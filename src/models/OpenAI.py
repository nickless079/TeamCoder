from typing import List, Dict, Any, Union, Optional
import os
import time
import openai
from openai import OpenAI

from .Base import BaseModel

class OpenAIModel(BaseModel):
    """
    OpenAI模型实现
    """
    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0,
        top_p: float = 0.95,
        max_retries: int = 3,
        retry_delay: int = 5,
        api_key: Optional[str] = None,
    ):
        """
        初始化OpenAI模型
        
        Args:
            model_name: 模型名称
            temperature: 生成温度
            top_p: 生成top_p值
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
            api_key: OpenAI API密钥，如果为None则从环境变量获取
        """
        super().__init__(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        
        # 使用提供的API密钥或从环境变量获取
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("必须提供OpenAI API密钥或设置OPENAI_API_KEY环境变量")
        self.api_base = os.environ.get("OPENAI_API_BASE")
        self.client = OpenAI(base_url=self.api_base,api_key=self.api_key)
        self._token_count_start = None
        self._token_count_total = 0
    def start_token_count(self):
        """
        启动 token 统计计数
        """
        self._token_count_start = time.time()
        self._token_count_total = 0

    def end_token_count(self) -> int:
        """
        结束 token 统计并返回总 token 数
        """
        elapsed = time.time() - (self._token_count_start or time.time())
        print(f"统计时长: {elapsed:.2f}s, 总 token 使用: {self._token_count_total}")
        return self._token_count_total
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0,
        top_p: float = 0.95,
        max_tokens: int = 1024 * 4,
        frequency_penalty: float = 0,
        presence_penalty: float = 1.5,
    ) -> str:
        
        temp = temperature if temperature is not None else self.temperature
        top_p_val = top_p if top_p is not None else self.top_p
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # 1. 发起请求
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temp,
                    top_p=top_p_val,
                    max_tokens=max_tokens,
                    #frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    extra_body={
                        "chat_template_kwargs": {
                            "top_k": 20,
                            "min_p": 0,
                            "enable_thinking": False  # 这里就是你想要的开关
                        }
                    }
                )

                # 2. 修正后的 Token 统计逻辑 (适配 OpenAI 对象格式)
                input_tokens = 0
                output_tokens = 0
                
                # 检查是否存在 usage 信息 (标准 OpenAI 格式都有)
                if hasattr(response, 'usage') and response.usage:
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens
                else:
                    # 如果没有 usage (极少见)，可以做一个简单估算或忽略
                    pass

                self._token_count_total += (input_tokens + output_tokens)

                # 3. 返回纯文本内容
                return response.choices[0].message.content
                
            except Exception as e:
                # 打印一下具体的错误，方便调试
                print(f"Attempt {attempt} failed: {e}")
                self._handle_retry(attempt, e)
        
        raise Exception("所有API调用尝试均失败")