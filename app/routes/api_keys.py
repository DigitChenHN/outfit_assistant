
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import UserLLMConfig
from app.forms import APIKeyForm
from app.llm.service import LLMService

bp = Blueprint('api_keys', __name__, url_prefix='/api_keys')

@bp.route('/', methods=['GET', 'POST'])
@login_required
def manage():
    """管理API密钥"""
    # 获取用户所有配置
    configs = UserLLMConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    # 将配置按model_type组织为字典
    config_dict = {c.model_type: c for c in configs}
    
    # 获取当前选择的model_type (优先用表单提交的，其次用第一个配置的，最后用默认)
    current_model = request.form.get('model_type') or (
        configs[0].model_type if configs else 'baidu'
    )
    
    # 获取当前配置或创建新实例
    current_config = config_dict.get(current_model)
    form = APIKeyForm(obj=current_config)
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            model_type = form.model_type.data
            config = config_dict.get(model_type)
            
            if not config:
                config = UserLLMConfig(
                    user_id=current_user.id,
                    model_type=model_type
                )
                db.session.add(config)
            
            # 更新基本配置
            config.api_key = form.api_key.data.strip()
            # 根据模型类型更新特定字段
            if model_type == 'baidu':
                if not form.api_secret.data:
                    flash('使用百度文心一言时必须提供Secret Key', 'error')
                    return render_template('api_keys/manage.html', 
                                        form=form, 
                                        configs=configs,
                                        current_model=model_type)
                config.api_secret = form.api_secret.data.strip()
                config.app_id = None
                
            elif model_type == 'xunfei':
                if not form.app_id.data:
                    flash('使用讯飞星火时必须提供AppID', 'error')
                    return render_template('api_keys/manage.html',
                                        form=form,
                                        configs=configs,
                                        current_model=model_type)
                config.app_id = form.app_id.data.strip()
                config.api_secret = None
                config.api_base = None
                
            elif model_type == 'silicon':
                config.api_base = form.api_base.data.strip() if form.api_base.data else None
                config.api_secret = None
                config.app_id = None
                
            elif model_type == 'openrouter':
                config.api_secret = None
                config.app_id = None
                config.api_base = None
            
            db.session.commit()
            flash(f'{model_type} API配置已保存', 'success')
            return redirect(url_for('api_keys.manage'))
            
        except Exception as e:
            db.session.rollback()
            flash('保存失败，请重试', 'error')
    
    return render_template('api_keys/manage.html', 
                         form=form,
                         configs=configs,
                         current_model=current_model,
                         model_info=UserLLMConfig.get_model_info())

@bp.route('/test', methods=['POST'])
@login_required
def test_api():
    """测试API配置"""
    config = UserLLMConfig.query.filter_by(user_id=current_user.id).first()
    if not config:
        return jsonify({
            'success': False,
            'message': '请先配置API密钥'
        }), 400
        
    if not config.is_valid:
        return jsonify({
            'success': False,
            'message': '配置信息不完整，请检查必填字段'
        }), 400
        
    try:
        # 创建LLM服务实例
        service = LLMService()
        service.set_user_id(current_user.id)
        
        # 发送测试请求
        test_prompt = "你好，这是一个测试消息，请回复'测试成功'。"
        response = service.chat(test_prompt)
        
        if response and '测试成功' in response:
            return jsonify({
                'success': True,
                'message': 'API配置测试成功！'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'API响应异常：{response}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败：{str(e)}'
        }), 400

@bp.route('/llm-configs', methods=['GET'])
@login_required
def get_llm_configs():
    """获取用户所有的LLM配置"""
    configs = UserLLMConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    return jsonify({
        'success': True,
        'data': [config.to_dict() for config in configs]
    })

# def init_app(app):
#     app.register_blueprint(bp)