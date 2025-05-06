from abc import ABC, abstractmethod
from typing import Optional

class BaseLLM(ABC):
    """LLM服务基类"""
    
    def __init__(self, api_key: str, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        
    @abstractmethod
    def chat(self, prompt: str) -> str:
        """发送消息并获取响应"""
        pass
        
    @abstractmethod
    def get_usage(self) -> dict:
        """获取API使用情况"""
        pass