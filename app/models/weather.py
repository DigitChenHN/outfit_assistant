
from datetime import datetime
from app import db

class WeatherCache(db.Model):
    """天气数据缓存模型"""
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    weather_condition = db.Column(db.String(50), nullable=False)
    humidity = db.Column(db.Integer)
    wind_speed = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WeatherCache {self.location} {self.temperature}°C {self.weather_condition}>'
    
    @property
    def is_valid(self):
        """检查缓存是否有效（1小时内）"""
        age = datetime.utcnow() - self.timestamp
        return age.total_seconds() < 3600  # 1小时有效期

class UserLocation(db.Model):
    """用户位置模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(100))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserLocation {self.city} ({self.latitude}, {self.longitude})>'