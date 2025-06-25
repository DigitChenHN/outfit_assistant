
import requests
import json
import time
import hashlib
import base64
import hmac
from urllib.parse import urlparse
from datetime import datetime
from flask import current_app
from app import db
from app.models import UserLLMConfig, UserLocation, Clothing
from app.services import weather_service, location_service

class LLMService:
    def __init__(self):
        self.user_id = None
        self.config = None

    def set_user_id(self, user_id, config_id=None):
        """设置用户ID并加载配置
        Args:
            user_id: 用户ID
            config_id: 可选，指定使用的配置ID。如果未提供，使用用户第一个有效配置
        """
        self.user_id = user_id
        if config_id:
            self.config = UserLLMConfig.query.filter_by(
                id=config_id,
                user_id=user_id,
                is_active=True
            ).first()
        else:
            self.config = UserLLMConfig.query.filter_by(
                user_id=user_id,
                is_active=True
            ).first()

    def _format_wardrobe_info(self, clothing_items):
        """格式化衣橱信息"""
        if not clothing_items:
            return "暂无衣物信息"
            
        wardrobe_by_category = {}
        for item in clothing_items:
            if item.category not in wardrobe_by_category:
                wardrobe_by_category[item.category] = []
            wardrobe_by_category[item.category].append(item)
        
        wardrobe_str = ""
        for category, items in wardrobe_by_category.items():
            wardrobe_str += f"\n【{category}】\n"
            for item in items:
                wardrobe_str += f"- {item.description}"
                if item.seasons_list:
                    wardrobe_str += f" (适用季节: {','.join(item.seasons_list)})"
                if item.occasions_list:
                    wardrobe_str += f" (适用场合: {','.join(item.occasions_list)})"
                wardrobe_str += "\n"
        
        return wardrobe_str

    def _get_baidu_access_token(self):
        """获取百度API的access_token"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            'grant_type': 'client_credentials',
            'client_id': self.config.api_key,
            'client_secret': self.config.api_secret
        }
        
        try:
            response = requests.post(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('access_token')
            current_app.logger.error(f"Baidu API token error: {response.text}")
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting Baidu access token: {str(e)}")
            return None

    def _call_baidu_api(self, prompt):
        """调用百度文心一言API"""
        if not self.config or not self.config.api_key or not self.config.api_secret:
            return "请先完成API配置（需要API Key和Secret Key）"
            
        access_token = self._get_baidu_access_token()
        if not access_token:
            return "无法连接到百度服务，请检查API配置"
            
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={access_token}"
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get('result', '未获取到有效回复')
            current_app.logger.error(f"Baidu API error: {response.text}")
            return "AI服务暂时不可用，请稍后再试"
        except Exception as e:
            current_app.logger.error(f"Error calling Baidu API: {str(e)}")
            return "调用AI服务时发生错误"

    def _call_xunfei_api(self, prompt):
        """调用讯飞星火API"""
        if not self.config or not self.config.api_key or not self.config.app_id:
            return "请先完成API配置（需要API Key和AppID）"
            
        api_url = "https://spark-api-open.xf-yun.com/v1/chat/completions"
        host = "spark-api.xf-yun.com"
        
        try:
                        
            headers = {
                "Authorization": f"Bearer {self.config.app_id}",
                "Content-Type": "application/json",
                # "host": host
            }
            
            data = {
                "model": "lite",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "# role\n"
                            "你是一个精通穿搭的时尚专家，熟悉各种风格的衣物搭配方法和技巧。对于配色、款式等搭配都有一套成熟的方法。\n"
                            "# situation\n"
                            "你面对的是不太了解穿搭的人群，他们只有最基本的审美，对于颜色应该如何搭配、款式应该如何选择，只有感觉上的判断，无法作出理论上的分析。而你懂得颜色和款式搭配的基本原理，知道哪些搭配是视觉上舒适的、符合大众审美的，哪些搭配是不应该采取的。\n"
                            "# task\n"
                            "你能够综合用户给出的天气、地理位置、衣橱中的衣物以及用户的自定义的要求，给出符合需求的建议，包括但不限于为用户提供穿搭建议，购买建议，以及其他任何相关的知识或者建议。"
                            "\n"
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False
            }
            
            response = requests.post(api_url, headers=headers, json=data)
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 0:
                    return data['choices'][0]['message']['content']
                else:
                    return f"AI服务请求失败，错误码：{data['code']}"
            current_app.logger.error(f"Xunfei API error: {response.text}")
            return f"http请求错误, {response.status_code}"
        except Exception as e:
            current_app.logger.error(f"Error calling Xunfei API: {str(e)}")
            return "调用AI服务时发生错误"

    def _call_silicon_api(self, prompt):
        """调用硅基流动API"""
        if not self.config or not self.config.api_key:
            return "请先完成API配置（需要API Key）"
            
        api_url = self.config.api_base if self.config.api_base else "https://api.siliconflow.cn/v1/chat/completions"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "Qwen/Qwen3-8B",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "# role\n"
                            "你是一个精通穿搭的时尚专家，熟悉各种风格的衣物搭配方法和技巧。对于配色、款式等搭配都有一套成熟的方法。\n"
                            "# situation\n"
                            "你面对的是不太了解穿搭的人群，他们只有最基本的审美，对于颜色应该如何搭配、款式应该如何选择，只有感觉上的判断，无法作出理论上的分析。而你懂得颜色和款式搭配的基本原理，知道哪些搭配是视觉上舒适的、符合大众审美的，哪些搭配是不应该采取的。\n"
                            "# task\n"
                            "你能够综合用户给出的天气、地理位置、衣橱中的衣物以及用户的自定义的要求，给出符合需求的建议，包括但不限于为用户提供穿搭建议，购买建议，以及其他任何相关的知识或者建议。"
                            "\n"
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(api_url, headers=headers, json=data)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            current_app.logger.error(f"Silicon API error: {response.text}")
            return f"AI服务请求失败，状态码：{response.status_code}"
        except Exception as e:
            current_app.logger.error(f"Error calling Silicon API: {str(e)}")
            return "调用AI服务时发生错误"

    def chat(self, prompt):
        """集成天气和位置信息的聊天接口"""
        if not self.config:
            return "请先配置AI服务"
            
        # 获取用户衣橱信息
        clothing_items = Clothing.query.filter_by(user_id=self.user_id).all()
        wardrobe_info = self._format_wardrobe_info(clothing_items)
        
        # 获取用户位置
        user_location = UserLocation.query.filter_by(user_id=self.user_id).first()
        
        # 获取天气信息
        weather_data = None
        if user_location:
            weather_data = weather_service.get_weather(
                user_location.latitude,
                user_location.longitude,
                user_location.city
            )
        
        # 格式化信息
        location_info = location_service.format_location_for_prompt(
            user_location if user_location else None
        )
        weather_info = weather_service.format_weather_for_prompt(weather_data) if weather_data else "天气信息暂不可用"
       
        
        # 构建完整prompt
        full_prompt = (
            f"当前地点：{location_info}\n"
            f"当前天气：{weather_info}\n\n"
            f"衣橱中的衣物：\n{wardrobe_info}\n\n"
            f"{prompt}\n\n"
        )
        
        # 根据配置的模型类型调用相应的API
        if self.config.model_type == 'baidu':
            return self._call_baidu_api(full_prompt)
        elif self.config.model_type == 'xunfei':
            return self._call_xunfei_api(full_prompt)
        elif self.config.model_type == 'silicon':
            return self._call_silicon_api(full_prompt)
        else:
            return "不支持的AI服务类型"