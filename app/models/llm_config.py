
from datetime import datetime
from app import db

class UserLLMConfig(db.Model):
    """用户LLM配置模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    model_type = db.Column(db.String(20), nullable=False)  # baidu/xunfei
    api_key = db.Column(db.String(200), nullable=False)
    api_secret = db.Column(db.String(200))  # 百度需要
    app_id = db.Column(db.String(200))      # 讯飞需要
    is_active = db.Column(db.Boolean, default=True)
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
            }
        }

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'model_type': self.model_type,
            'api_key': self.api_key,
            'api_secret': self.api_secret if self.model_type == 'baidu' else None,
            'app_id': self.app_id if self.model_type == 'xunfei' else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

# 支持的模型类型
SUPPORTED_MODELS = {
    'baidu': '百度文心一言',
    'xunfei': '讯飞星火'
}