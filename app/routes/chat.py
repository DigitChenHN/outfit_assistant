
from flask import Blueprint, render_template, jsonify, request, current_app 
from flask_login import login_required, current_user
from app.llm.service import LLMService
from app import db
from app.models.chat import ChatHistory, Conversation
from app.utils.chat_migration import migrate_chat_history
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
@login_required
def index():
    """聊天界面"""
    # 获取对话ID参数
    conversation_id = request.args.get('conversation_id', type=int)
    
    # 如果没有指定对话ID，则获取最近的对话
    if not conversation_id:
        conversation = Conversation.query.filter_by(user_id=current_user.id)\
            .order_by(Conversation.updated_at.desc())\
            .first()
    else:
        conversation = Conversation.query.filter_by(
            id=conversation_id, 
            user_id=current_user.id
        ).first_or_404()
    
    # 如果没有对话，创建一个新对话
    if not conversation:
        conversation = Conversation(
            user_id=current_user.id,
            title=f"新对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        db.session.add(conversation)
        db.session.commit()
    
    # 获取当前对话的聊天记录
    chat_history = ChatHistory.query.filter_by(
        user_id=current_user.id,
        conversation_id=conversation.id
    ).order_by(ChatHistory.timestamp.desc()).all()
    
    # 获取所有对话列表
    conversations = Conversation.query.filter_by(user_id=current_user.id)\
        .order_by(Conversation.updated_at.desc())\
        .all()
    
    return render_template(
        'chat/index.html', 
        chat_history=chat_history,
        current_conversation=conversation,
        conversations=conversations
    )

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """处理聊天请求
    参数:
    - message: 必需，用户消息内容
    - conversation_id: 必需，对话ID
    - config_id: 可选，指定使用的LLM配置ID
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': '无效的请求数据'}), 400
        
    user_message = data['message']
    conversation_id = data.get('conversation_id')
    config_id = data.get('config_id')
    
    # 验证对话ID
    if not conversation_id:
        return jsonify({'error': '缺少对话ID'}), 400
        
    # 检查对话是否存在且属于当前用户
    conversation = Conversation.query.filter_by(
        id=conversation_id, 
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': '对话不存在或无权限访问'}), 404
    
    # 创建LLM服务实例
    llm_service = LLMService()
    llm_service.set_user_id(current_user.id, config_id)
    
    try:
        # 验证LLM服务配置
        if not llm_service.config:
            current_app.logger.error(f"No LLM config for user {current_user.id}")
            return jsonify({'error': '请先配置AI服务'}), 400
            
        # 获取AI响应
        response = llm_service.chat(user_message)
        
        if not response or len(response.strip()) == 0:
            current_app.logger.error(f"Empty response from LLM for user {current_user.id}")
            return jsonify({'error': 'AI服务返回空响应'}), 500
        
        # 保存聊天记录
        try:
            chat_history = ChatHistory(
                user_id=current_user.id,
                conversation_id=conversation_id,
                user_message=user_message,
                ai_response=response,
                message_type='chat'
            )
            db.session.add(chat_history)
            
            # 更新对话的最后更新时间
            conversation.updated_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as db_error:
            current_app.logger.error(f"Error saving chat history: {str(db_error)}")
            db.session.rollback()
            # 即使保存失败也返回响应，但不带history_id
            return jsonify({
                'response': response,
                'warning': '聊天记录保存失败'
            })
        
        return jsonify({
            'success': True,
            'response': response,
            'history_id': chat_history.id
        })
        
    except Exception as e:
        current_app.logger.error(f"Chat error for user {current_user.id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': '处理请求时发生错误',
            'details': str(e)
        }), 500

@chat_bp.route('/api/chat/history')
@login_required
def get_chat_history():
    """获取聊天历史"""
    conversation_id = request.args.get('conversation_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    if not conversation_id:
        return jsonify({'error': '缺少对话ID'}), 400
        
    # 检查对话是否存在且属于当前用户
    conversation = Conversation.query.filter_by(
        id=conversation_id, 
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': '对话不存在或无权限访问'}), 404
    
    history = ChatHistory.query.filter_by(
        user_id=current_user.id,
        conversation_id=conversation_id
    ).order_by(ChatHistory.timestamp.desc())\
     .paginate(page=page, per_page=per_page, error_out=False)
        
    return jsonify({
        'items': [{
            'id': h.id,
            'user_message': h.user_message,
            'ai_response': h.ai_response,
            'timestamp': h.timestamp.isoformat(),
            'type': h.message_type
        } for h in history.items],
        'total': history.total,
        'pages': history.pages,
        'current_page': history.page
    })

@chat_bp.route('/api/conversations')
@login_required
def get_conversations():
    """获取用户的所有对话"""
    conversations = Conversation.query.filter_by(user_id=current_user.id)\
        .order_by(Conversation.updated_at.desc())\
        .all()
        
    return jsonify({
        'success': True,
        'conversations': [conv.to_dict() for conv in conversations]
    })

@chat_bp.route('/api/conversations/create', methods=['POST'])
@login_required
def create_conversation():
    """创建新对话"""
    data = request.get_json()
    title = data.get('title', f"新对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    try:
        conversation = Conversation(
            user_id=current_user.id,
            title=title
        )
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'conversation': conversation.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'创建对话失败: {str(e)}'
        }), 500

@chat_bp.route('/api/conversations/<int:id>/rename', methods=['POST'])
@login_required
def rename_conversation(id):
    """重命名对话"""
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': '缺少标题'}), 400
        
    conversation = Conversation.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        conversation.title = data['title']
        db.session.commit()
        
        return jsonify({
            'success': True,
            'conversation': conversation.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'重命名对话失败: {str(e)}'
        }), 500

@chat_bp.route('/api/conversations/<int:id>/delete', methods=['POST'])
@login_required
def delete_conversation(id):
    """删除对话"""
    conversation = Conversation.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(conversation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '对话已删除'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'删除对话失败: {str(e)}'
        }), 500

@chat_bp.route('/run-migration')
@login_required
def run_migration():
    """运行聊天记录迁移"""
    try:
        migrate_chat_history()
        return jsonify({
            'success': True,
            'message': '迁移完成'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'迁移失败: {str(e)}'
        }), 500