
import requests
from flask import current_app
import json
from typing import Optional, Tuple, Dict
from app.models.weather import UserLocation

class LocationService:
    def __init__(self):
        self.ip_api_url = "http://ip-api.com/json/"  # 免费的IP定位服务
        
    def get_location_by_ip(self, ip: str = None) -> Optional[Dict]:
        """通过IP地址获取位置信息"""
        try:
            url = self.ip_api_url + (ip if ip else '')
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'city': data.get('city'),
                        'latitude': data.get('lat'),
                        'longitude': data.get('lon'),
                        'country': data.get('country'),
                        'region': data.get('regionName')
                    }
            current_app.logger.warning(f"IP定位失败: {response.text}")  # 记录失败信息，便于调
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting location by IP: {str(e)}")
            return None

    def validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """验证坐标是否有效"""
        try:
            return -90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180
        except (ValueError, TypeError):
            return False

    def get_location_by_coordinates(self, latitude: float, longitude: float) -> Optional[Dict]:
        """通过坐标获取位置信息（优先使用IP定位，失败时使用坐标查询）"""
        # 首先尝试通过IP获取位置
        ip = self.get_client_ip()
        if not ip:
            current_app.logger.warning("无法获取IP地址，使用坐标查询")
        ip_location = self.get_location_by_ip(ip)
        if ip_location:
            return ip_location
        else:
            current_app.logger.warning("IP定位失败，使用坐标查询")
            
        # IP定位失败时再使用坐标查询
        if not self.validate_coordinates(latitude, longitude):
            return None

        try:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
            headers = {'User-Agent': 'OutfitAssistant/1.0'}
            response = requests.get(url, headers=headers, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                return {
                    'city': address.get('city') or address.get('town') or address.get('village'),
                    'latitude': latitude,
                    'longitude': longitude,
                    'country': address.get('country'),
                    'region': address.get('state')
                }
            return None
        except Exception as e:
            current_app.logger.error(f"坐标定位失败: {str(e)}")
            return None

    def format_location_for_prompt(self, location_data: UserLocation) -> str:
        """将位置信息格式化为适合prompt的字符串"""
        if not location_data:
            return "未知位置"
        
        data = {
            'city': getattr(location_data, 'city', None),
            'region': None,  # 可根据模型添加
            'country': None  # 可根据模型添加
        }

        location_parts = []
        if data.get('city'):
            location_parts.append(data['city'])
        if data.get('region'):
            location_parts.append(data['region'])
        if data.get('country'):
            location_parts.append(data['country'])
            
        return ", ".join(location_parts) if location_parts else "未知位置"

    def get_client_ip(self) -> Optional[str]:
        """获取客户端IP地址"""
        try:
            from flask import request
            if current_app.config.get('TESTING'):  # 测试环境下使用固定IP
                return '114.114.114.114'
            if request:
                # 考虑代理情况，获取最真实的IP
                if request.headers.get('X-Forwarded-For'):
                    ip = request.headers['X-Forwarded-For'].split(',')[0]
                else:
                    ip = request.remote_addr
                return ip
            return None
        except Exception as e:
            current_app.logger.error(f"获取IP地址失败: {str(e)}")
            return None

    def get_current_coordinates(self) -> Tuple[float, float]:
        """获取设备当前位置坐标"""
        try:
            # 获取客户端IP
            ip = self.get_client_ip()
            # 通过IP获取位置，增加超时设置
            location = self.get_location_by_ip(ip)
            if location:
                return (location['latitude'], location['longitude'])
            
        except requests.exceptions.ConnectionError:
            current_app.logger.warning("IP定位服务连接失败，使用默认位置")
        except Exception as e:
            current_app.logger.error(f"获取当前位置失败: {str(e)}")
        
        # 返回默认位置
        default = current_app.config['DEFAULT_LOCATION']
        return (default['latitude'], default['longitude'])

# 创建全局服务实例
location_service = LocationService()