from datetime import datetime
from app import db

class UserLLMConfig(db.Model):
    """用户LLM配置模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    model_type = db.Column(db.String(20), nullable=False)  # baidu/xunfei/silicon/openrouter
    api_key = db.Column(db.String(200), nullable=False)
    api_secret = db.Column(db.String(200))  # 百度需要
    app_id = db.Column(db.String(200))      # 讯飞需要
    api_base = db.Column(db.String(200))    # 硅基流动可选
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserLLMConfig {self.model_type}>'

    @property
    def is_valid(self):
        """检查配置是否有效"""
        if not self.api_key:
            return False
            
        if self.model_type == 'baidu':
            return bool(self.api_secret)
        elif self.model_type == 'xunfei':
            return bool(self.app_id)
        elif self.model_type == 'silicon':
            return True  # 只需要api_key
        elif self.model_type == 'openrouter':
            return True  # 只需要api_key
        return False

    @staticmethod
    def get_model_info():
        """获取支持的模型信息"""
        return {
            'baidu': {
                'name': '百度文心一言',
                'requires': ['api_key', 'api_secret'],
                'optional': [],
                'help_url': 'https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Dlibv6vs1'
            },
            'xunfei': {
                'name': '讯飞星火',
                'requires': ['api_key', 'app_id'],
                'optional': [],
                'help_url': 'https://www.xfyun.cn/doc/spark/Web.html'
            },
            'silicon': {
                'name': '硅基流动',
                'requires': ['api_key'],
                'optional': ['api_base'],
                'help_url': 'https://www.siliconflow.cn/docs'
            },
            'openrouter': {
                'name': 'OpenRouter',
                'requires': ['api_key'],
                'optional': [],
                'help_url': 'https://openrouter.ai/docs'
            }
        }

    def to_dict(self):
        """转换为字典格式"""
        model_name = SUPPORTED_MODELS.get(self.model_type, self.model_type)
        # 如果是默认配置，在名称后标注
        model_type_display = f"{model_name}{' (默认)' if self.is_default else ''}"
        
        return {
            'id': self.id,
            'model_type': self.model_type,
            'model_type_display': model_type_display,
            'api_key': self.api_key,
            'api_secret': self.api_secret if self.model_type == 'baidu' else None,
            'app_id': self.app_id if self.model_type == 'xunfei' else None,
            'api_base': self.api_base if self.model_type == 'silicon' else None,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat()
        }

# 支持的模型类型
SUPPORTED_MODELS = {
    'baidu': '百度文心一言',
    'xunfei': '讯飞星火',
    'silicon': '硅基流动',
    'openrouter': 'OpenRouter'
}