
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.services import weather_service, location_service
from app.models.weather import UserLocation
from app import db
from datetime import datetime

weather_bp = Blueprint('weather', __name__)

def _update_user_location(latitude=None, longitude=None):
    """内部使用的更新位置逻辑"""
    if latitude is None or longitude is None:
        # 尝试从浏览器获取位置
        latitude, longitude = location_service.get_current_coordinates()
    
    location_info = location_service.get_location_by_coordinates(latitude, longitude)
    if not location_info:
        return None
        
    # 更新或创建用户位置记录
    user_location = UserLocation.query.filter_by(user_id=current_user.id).first() or \
                   UserLocation(user_id=current_user.id)
    user_location.latitude = latitude
    user_location.longitude = longitude
    user_location.city = location_info.get('city')
    
    try:
        db.session.add(user_location)
        db.session.commit()
        return location_info
    except Exception as e:
        current_app.logger.error(f"保存位置失败: {str(e)}")
        db.session.rollback()
        return None

@weather_bp.route('/api/location', methods=['GET'])
@login_required
def get_location():
    """获取用户当前位置信息"""
    user_location = UserLocation.query.filter_by(user_id=current_user.id).first()
    
    if user_location:
        location_age = datetime.utcnow() - user_location.last_updated
        if location_age < current_app.config['LOCATION_CACHE_DURATION']:
            return jsonify({
                'latitude': user_location.latitude,
                'longitude': user_location.longitude,
                'city': user_location.city
            })
    
    # 尝试自动获取位置
    location_info = _update_user_location()
    if location_info:
        return jsonify(location_info)
    
    # 返回默认位置
    return jsonify(current_app.config['DEFAULT_LOCATION'])

@weather_bp.route('/api/location', methods=['POST'])  
@login_required
def update_location():
    """更新用户位置信息(API端点)"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效请求'}), 400
        
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if not location_service.validate_coordinates(latitude, longitude):
        return jsonify({'error': '无效坐标'}), 400
        
    location_info = _update_user_location(latitude, longitude)
    if not location_info:
        return jsonify({'error': '更新位置失败'}), 500
        
    return jsonify(location_info)

@weather_bp.route('/api/weather', methods=['GET'])
@login_required
def get_weather():
    """获取当前天气信息"""
    # 获取用户位置
    user_location = UserLocation.query.filter_by(user_id=current_user.id).first()
    
    if not user_location:
        # 使用默认位置
        default_location = current_app.config['DEFAULT_LOCATION']
        latitude = default_location['latitude']
        longitude = default_location['longitude']
        city = default_location['city']
    else:
        latitude = user_location.latitude
        longitude = user_location.longitude
        city = user_location.city
        
    # 获取天气信息
    weather_data = weather_service.get_weather(latitude, longitude, city)
    
    if not weather_data:
        return jsonify({'error': '无法获取天气信息'}), 500
        
    # 格式化天气信息用于显示
    formatted_weather = weather_service.format_weather_for_prompt(weather_data)
    
    return jsonify({
        'weather': weather_data,
        'formatted': formatted_weather,
        'location': {
            'latitude': latitude,
            'longitude': longitude,
            'city': city
        }
    })