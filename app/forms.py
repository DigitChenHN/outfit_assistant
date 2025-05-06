
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField
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

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    """注册表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])