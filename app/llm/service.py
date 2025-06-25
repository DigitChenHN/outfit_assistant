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
            
    def _call_openrouter_api(self, prompt):
        """调用OpenRouter API"""
        if not self.config or not self.config.api_key:
            return "请先完成API配置（需要API Key）"
            
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                # "HTTP-Referer": "https://outfit-assistant.example.com",  # 根据OpenRouter要求添加
                # "X-Title": "Outfit Assistant"  # 可选的应用名称
            }
            
            data = {
                "model": "deepseek/deepseek-chat-v3-0324:free",  # 可以根据需要选择模型
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
            current_app.logger.error(f"OpenRouter API error: {response.text}")
            return f"AI服务请求失败，状态码：{response.status_code}"
        except Exception as e:
            current_app.logger.error(f"Error calling OpenRouter API: {str(e)}")
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
        elif self.config.model_type == 'openrouter':
            return self._call_openrouter_api(full_prompt)
        else:
            return "不支持的AI服务类型"
    
    def analyze_clothing_image(self, image_data):
        """分析衣物图片并返回识别结果
        
        Args:
            image_data: 二进制图片数据
            
        Returns:
            dict: 包含解析后的衣物信息，如description, seasons, occasions
        """
        if not self.config:
            return {"error": "请先配置AI服务"}
            
        # 将图片转换为base64编码
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # 准备提示词
        system_prompt = """
## role 
你是一个服装从业者，熟悉服装的款式、颜色、材料等。

## task
当用户提供给你一张包含衣物服饰的图片时，你需要识别其中的服装的种类、颜色、款式、适合季节、适用场合。然后将这些信息以json的格式输出，例如：
{
"description": "珍珠白褶皱雪纺衬衫",
"season":  ["春", "夏"],
"occasion": ["日常"]
}
其中，occasion仅从['日常', '工作', '运动', '正式', '休闲', '派对']中选择，season仅从["春", "夏", "秋", "冬"]中选择。
"""
        user_prompt = "请分析这张衣物图片，并以JSON格式返回描述、适用季节和场合信息。"
        
        # 根据配置的模型类型调用相应的API
        try:
            if self.config.model_type == 'baidu':
                result = '目前仅openrouter支持图像识别'
                # result = self._call_baidu_image_api(system_prompt, user_prompt, image_base64)
            elif self.config.model_type == 'xunfei':
                result = '目前仅openrouter支持图像识别'
                # result = self._call_xunfei_image_api(system_prompt, user_prompt, image_base64)
            elif self.config.model_type == 'silicon':
                result = '目前仅openrouter支持图像识别'
                # result = self._call_silicon_image_api(system_prompt, user_prompt, image_base64)
            elif self.config.model_type == 'openrouter':
                result = self._call_openrouter_image_api(system_prompt, user_prompt, image_base64)
            else:
                return {"error": "不支持的AI服务类型"}
                
            # 解析返回的JSON结果
            try:
                # 查找JSON部分，可能被包含在其他文本中
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    
                    # 标准化结果格式
                    return {
                        "description": data.get("description", "未识别的衣物"),
                        "seasons": data.get("season", []),
                        "occasions": data.get("occasion", [])
                    }
                else:
                    return {"error": "无法从AI响应中解析出JSON数据"}
            except Exception as e:
                current_app.logger.error(f"解析AI响应时出错: {str(e)}, 原始响应: {result}")
                return {"error": f"解析AI响应时出错: {str(e)}"}
        except Exception as e:
            current_app.logger.error(f"调用AI图像分析服务时出错: {str(e)}")
            return {"error": f"调用AI服务时出错: {str(e)}"}
    
    def _call_openrouter_image_api(self, system_prompt, user_prompt, image_base64):
        """调用OpenRouter多模态API分析图片"""
        if not self.config or not self.config.api_key:
            return "请先完成API配置（需要API Key）"
            
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                # "HTTP-Referer": "https://outfit-assistant.example.com",
                # "X-Title": "Outfit Assistant"
            }
            
            # 构建多模态消息
            data = {
                "model": "qwen/qwen2.5-vl-72b-instruct:free", # 使用支持视觉的模型
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(api_url, headers=headers, json=data)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            current_app.logger.error(f"OpenRouter API error: {response.text}")
            return f"AI服务请求失败，状态码：{response.status_code}"
        except Exception as e:
            current_app.logger.error(f"Error calling OpenRouter API: {str(e)}")
            return f"调用AI服务时发生错误: {str(e)}"
    
    def _call_baidu_image_api(self, system_prompt, user_prompt, image_base64):
        """调用百度文心一言多模态API分析图片"""
        if not self.config or not self.config.api_key or not self.config.api_secret:
            return "请先完成API配置（需要API Key和Secret Key）"
            
        access_token = self._get_baidu_access_token()
        if not access_token:
            return "无法连接到百度服务，请检查API配置"
            
        api_url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={access_token}"
        
        try:
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.7,
                "max_output_tokens": 1000
            }
            
            response = requests.post(api_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get('result', '未获取到有效回复')
            current_app.logger.error(f"Baidu Image API error: {response.text}")
            return "AI服务暂时不可用，请稍后再试"
        except Exception as e:
            current_app.logger.error(f"Error calling Baidu Image API: {str(e)}")
            return f"调用AI服务时发生错误: {str(e)}"
            
    def _call_xunfei_image_api(self, system_prompt, user_prompt, image_base64):
        """调用讯飞星火多模态API分析图片"""
        # 注意：讯飞目前的API可能不支持直接处理图像，此处提供一个模拟实现
        # 实际使用时应查阅讯飞最新的API文档
        if not self.config or not self.config.api_key or not self.config.app_id:
            return "请先完成API配置（需要API Key和AppID）"
            
        return "讯飞星火API暂不支持图像分析功能，请选择其他服务提供商"
            
    def _call_silicon_image_api(self, system_prompt, user_prompt, image_base64):
        """调用硅基流动多模态API分析图片"""
        if not self.config or not self.config.api_key:
            return "请先完成API配置（需要API Key）"
            
        api_url = self.config.api_base if self.config.api_base else "https://api.siliconflow.cn/v1/chat/completions"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "Qwen/Qwen-VL-Plus",  # 使用支持视觉的模型
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(api_url, headers=headers, json=data)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            current_app.logger.error(f"Silicon Image API error: {response.text}")
            return f"AI服务请求失败，状态码：{response.status_code}"
        except Exception as e:
            current_app.logger.error(f"Error calling Silicon Image API: {str(e)}")
            return f"调用AI服务时发生错误: {str(e)}"