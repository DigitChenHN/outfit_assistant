from datetime import datetime
from app import db

class Conversation(db.Model):
    """对话模型，表示一个完整的对话"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), default="新对话")  # 对话标题
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 与ChatHistory的一对多关系
    messages = db.relationship('ChatHistory', backref='conversation', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Conversation {self.id}: {self.title}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'message_count': self.messages.count()
        }

class ChatHistory(db.Model):
    """聊天历史记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=True)  # 关联到对话
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
        return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_message': self.user_message,
            'ai_response': self.ai_response,
            'timestamp': self.timestamp.isoformat(),
            'type': self.message_type
        }