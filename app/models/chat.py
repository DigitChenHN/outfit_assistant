from datetime import datetime
from app import db

class ChatHistory(db.Model):
    """聊天历史记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='chat')  # 消息类型：chat, system 等
    tokens_used = db.Column(db.Integer)  # 记录token消耗
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ChatHistory {self.id}>'

    @property
    def formatted_time(self):
        """返回格式化的时间字符串"""
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S')