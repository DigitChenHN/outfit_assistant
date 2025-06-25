
from flask import Blueprint, render_template, jsonify, request, current_app 
from flask_login import login_required, current_user
from app.llm.service import LLMService
from app import db
from app.models.chat import ChatHistory

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
@login_required
def index():
    """聊天界面"""
    # 获取历史聊天记录
    chat_history = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(10)\
        .all()
    return render_template('chat/index.html', chat_history=chat_history)

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    current_app.logger.info(f"Received chat request from user {current_user.id}")  # 添加日志
    """处理聊天请求
    参数:
    - message: 必需，用户消息内容
    - config_id: 可选，指定使用的LLM配置ID
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': '无效的请求数据'}), 400
        
    user_message = data['message']
    config_id = data.get('config_id')
    
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
                user_message=user_message,
                ai_response=response,
                message_type='chat'
            )
            db.session.add(chat_history)
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
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    history = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp.desc())\
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