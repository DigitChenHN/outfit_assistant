
import requests
from datetime import datetime
from typing import Optional, Dict
from flask import current_app
from app import db
from app.models.weather import WeatherCache

class WeatherService:
    def __init__(self):
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.api_key = None  # 将从配置中获取

    def get_api_key(self) -> str:
        """从Flask配置中获取API密钥"""
        if not self.api_key:
            self.api_key = current_app.config.get('OPENWEATHER_API_KEY')
        return self.api_key

    def get_weather_from_cache(self, location: str) -> Optional[WeatherCache]:
        """从缓存中获取天气数据"""
        cache = WeatherCache.query.filter_by(location=location).order_by(
            WeatherCache.timestamp.desc()
        ).first()
        
        if cache and cache.is_valid:
            return cache
        return None

    def fetch_weather(self, latitude: float, longitude: float) -> Optional[Dict]:
        """从OpenWeatherMap API获取天气数据"""
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.get_api_key(),
                'units': 'metric'  # 使用摄氏度
            }
            
            response = requests.get(self.base_url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                current_app.logger.error(
                    f"Weather API error: {response.status_code} - {response.text}"
                )
                return None
        except Exception as e:
            current_app.logger.error(f"Error fetching weather: {str(e)}")
            return None

    def get_weather(self, latitude: float, longitude: float, city: str) -> Optional[Dict]:
        """获取天气信息，优先使用缓存"""
        # 先检查缓存
        cache = self.get_weather_from_cache(city)
        if cache and cache.location == city:
            return {
                'temperature': cache.temperature,
                'condition': cache.weather_condition,
                'humidity': cache.humidity,
                'wind_speed': cache.wind_speed,
                'timestamp': cache.timestamp
            }
        elif cache and cache.location != city:
            db.session.delete(cache)
            db.session.commit()

        # 如果缓存不存在或已过期，从API获取新数据
        weather_data = self.fetch_weather(latitude, longitude)
        if weather_data:
            # 保存到缓存
            cache = WeatherCache(
                location=city,
                temperature=weather_data['main']['temp'],
                weather_condition=weather_data['weather'][0]['main'],
                humidity=weather_data['main']['humidity'],
                wind_speed=weather_data['wind']['speed']
            )
            db.session.add(cache)
            try:
                db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Error saving weather cache: {str(e)}")
                db.session.rollback()

            return {
                'temperature': cache.temperature,
                'condition': cache.weather_condition,
                'humidity': cache.humidity,
                'wind_speed': cache.wind_speed,
                'timestamp': cache.timestamp
            }
        return None

    def format_weather_for_prompt(self, weather_data: Dict) -> str:
        """将天气信息格式化为适合prompt的字符串"""
        if not weather_data:
            return "天气信息暂不可用"

        condition_map = {
            'Clear': '晴天',
            'Clouds': '多云',
            'Rain': '雨天',
            'Snow': '雪天',
            'Thunderstorm': '雷暴',
            'Drizzle': '毛毛雨',
            'Mist': '薄雾',
            'Fog': '雾'
        }

        weather_condition = condition_map.get(
            weather_data['condition'], 
            weather_data['condition']
        )

        return (
            f"当前天气状况：{weather_condition}，"
            f"温度：{weather_data['temperature']:.1f}°C，"
            f"湿度：{weather_data['humidity']}%，"
            f"风速：{weather_data['wind_speed']}米/秒"
        )

# 创建全局服务实例
weather_service = WeatherService()