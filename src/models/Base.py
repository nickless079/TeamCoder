from typing import List, Dict, Any, Union
import time

class BaseModel:
    """
    基础模型类，所有具体模型实现的父类
    """
    def __init__(
        self,
        model_name: str,
        temperature: float = 0.2,
        top_p: float = 0.95,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        初始化基础模型
        
        Args:
            model_name: 模型名称
            temperature: 生成温度
            top_p: 生成top_p值
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
        frequency_penalty: float = 0,
        presence_penalty: float = 0,
    ) -> str:
        """
        发送聊天请求到模型
        
        Args:
            messages: 消息列表，每个消息是包含'role'和'content'的字典
            temperature: 生成温度，覆盖默认值
            top_p: 生成top_p值，覆盖默认值
            max_tokens: 最大生成token数
            frequency_penalty: 频率惩罚
            presence_penalty: 存在惩罚
            
        Returns:
            模型生成的回复文本
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def _handle_retry(self, attempt: int, exception: Exception) -> None:
        """
        处理API调用失败的重试逻辑
        
        Args:
            attempt: 当前尝试次数
            exception: 发生的异常
        """
        if attempt < self.max_retries:
            delay = self.retry_delay * (2 ** (attempt - 1))  # 指数退避
            print(f"API调用失败: {str(exception)}. 将在{delay}秒后重试...")
            time.sleep(delay)
        else:
            print(f"达到最大重试次数({self.max_retries})。最后一次错误: {str(exception)}")
            raise exception 