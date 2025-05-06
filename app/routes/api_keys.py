
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
    # 获取用户现有配置
    config = UserLLMConfig.query.filter_by(user_id=current_user.id).first()
    form = APIKeyForm(obj=config)
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            if not config:
                config = UserLLMConfig(user_id=current_user.id)
                db.session.add(config)
            
            # 更新基本配置
            config.model_type = form.model_type.data
            config.api_key = form.api_key.data.strip()
            
            # 根据模型类型更新特定字段
            if config.model_type == 'baidu':
                if not form.api_secret.data:
                    flash('使用百度文心一言时必须提供Secret Key', 'error')
                    return render_template('api_keys/manage.html', form=form, config=config)
                config.api_secret = form.api_secret.data.strip()
                config.app_id = None  # 清除不需要的字段
                
            elif config.model_type == 'xunfei':
                if not form.app_id.data:
                    flash('使用讯飞星火时必须提供AppID', 'error')
                    return render_template('api_keys/manage.html', form=form, config=config)
                config.app_id = form.app_id.data.strip()
                config.api_secret = None  # 清除不需要的字段
            
            db.session.commit()
            flash('API配置已保存', 'success')
            return redirect(url_for('api_keys.manage'))
            
        except Exception as e:
            db.session.rollback()
            flash('保存失败，请重试', 'error')
    
    return render_template('api_keys/manage.html', 
                         form=form,
                         config=config,
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

def init_app(app):
    app.register_blueprint(bp)