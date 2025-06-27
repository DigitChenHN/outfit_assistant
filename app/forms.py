from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Optional
from app.models.llm_config import SUPPORTED_MODELS

class APIKeyForm(FlaskForm):
    """API密钥配置表单"""
    model_type = SelectField('AI服务提供商', 
                          choices=[(k, v) for k, v in SUPPORTED_MODELS.items()],
                          validators=[DataRequired(message='请选择AI服务提供商')])
                          
    api_key = StringField('API Key', 
                       validators=[DataRequired(message='请输入API Key'), 
                                 Length(min=5, message='API Key长度不足')])
                                 
    api_secret = StringField('Secret Key',
                          validators=[Optional()],
                          description='百度文心一言需要填写此项')
                          
    app_id = StringField('APIPassword',
                      validators=[Optional()],
                      description='讯飞星火需要填写此项')
                      
    api_base = StringField('API Base URL',
                       validators=[Optional()],
                       description='硅基流动专用(可选)')
                       
    is_active = BooleanField('启用此配置', default=True)
    
    is_default = BooleanField('设为默认', default=False,
                           description='设为默认后，在聊天界面将优先选择此服务商')

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    """注册表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])