from typing import Type
import os

from .Base import BaseModel
from .OpenAI import OpenAIModel
from .Ollama import OllamaModel
from .AlibabaModel import AlibabaModel


# 动态导入，避免未安装相关库时的错误
try:
    from .Anthropic import AnthropicModel
except ImportError:
    AnthropicModel = None

try:
    from .Gemini import GeminiModel
except ImportError:
    GeminiModel = None

try:
    from .GroqModel import GroqModel
except ImportError:
    GroqModel = None

class ModelFactory:
    """
    模型工厂类，用于创建不同类型的模型实例
    """
    
    @staticmethod
    def get_model_class(provider_name: str) -> Type[BaseModel]:
        """
        根据提供商名称获取对应的模型类
        
        Args:
            provider_name: 模型提供商名称
            
        Returns:
            模型类
        """
        provider_name = provider_name.lower()
        
        if provider_name == "openai":
            return OpenAIModel
        elif provider_name == "ollama":
            return OllamaModel
        elif provider_name in ["alibaba", "aliyun", "bailian"]:
            return AlibabaModel
        else:
            raise ValueError(f"未知的模型提供商: {provider_name}")
    
    @staticmethod
    def create_model(
        provider_name: str,
        model_name: str = None,
        **kwargs
    ) -> BaseModel:
        """
        创建模型实例
        
        Args:
            provider_name: 模型提供商名称
            model_name: 模型名称
            **kwargs: 其他参数
            
        Returns:
            模型实例
        """
        model_class = ModelFactory.get_model_class(provider_name)
        
        # 根据不同的提供商设置默认模型名称
        if not model_name:
            if provider_name.lower() == "openai":
                model_name = "gpt-3.5-turbo"
            elif provider_name.lower() == "ollama":
                model_name = "qwen3:4b"
            elif provider_name.lower() in ["alibaba", "aliyun", "bailian"]:
                model_name = "qwen3:4b"
        
        return model_class(model_name=model_name, **kwargs) 