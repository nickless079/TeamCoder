from typing import List, Dict, Any, Union, Optional
import os
import time
import copy
import dashscope

from .Base import BaseModel
from constants.verboseType import *

class AlibabaModel(BaseModel):
    """
    阿里云百炼平台模型实现，支持通义千问等大语言模型
    使用官方dashscope SDK
    """
    def __init__(
        self,
        model_name: str = "qwen3-4b",
        temperature: float = 0.2,
        top_p: float = 0.95,
        max_retries: int = 3,
        retry_delay: int = 5,
        api_key: str = None,
        api_base: str = None,
        verbose: int = VERBOSE_MINIMAL,
    ):
        """
        初始化阿里云百炼平台模型
        
        Args:
            model_name: 模型名称，如"qwen3:4b"
            temperature: 生成温度
            top_p: 生成top_p值
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
            api_key: 阿里云API密钥，如果为None则从环境变量DASHSCOPE_API_KEY获取
            api_base: 阿里云API基础URL（使用dashscope时通常不需要）
            verbose: 输出详细程度
        """
        super().__init__(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self.verbose = verbose
        self.api_key = api_key or os.environ.get("ALIBABA_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
        self._token_count_start = None
        self._token_count_total = 0
        if not self.api_key:
            raise ValueError("阿里云API密钥未提供，请通过参数或环境变量ALIBABA_API_KEY/DASHSCOPE_API_KEY设置")
        
        # 设置dashscope API密钥
        dashscope.api_key = self.api_key
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"API密钥: {self.api_key[:8]}...{self.api_key[-4:]}")
            print(f"使用阿里云百炼平台模型: {self.model_name}")
    
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
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
        frequency_penalty: float = 0,
        presence_penalty: float = 0,
    ) -> str:
        """
        发送聊天请求到阿里云百炼平台
        
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
        temp = temperature if temperature is not None else self.temperature
        top_p_val = top_p if top_p is not None else self.top_p
        
        # 创建消息的深拷贝，避免修改原始消息
        messages_copy = copy.deepcopy(messages)
        

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"尝试 {attempt}/{self.max_retries}: 调用阿里云百炼平台模型 {self.model_name}")
                start = time.time()
                # 使用dashscope SDK发送请求
                response = dashscope.Generation.call(
                    model=self.model_name,
                    messages=messages_copy,
                    temperature=temp,
                    top_p=top_p_val,
                    max_tokens=max_tokens or 1024*8,
                    result_format='message',
                    repetition_penalty=1.0 + frequency_penalty,  # 将frequency_penalty转换为repetition_penalty
                    enable_thinking=False  # 禁用思考过程，解决非流式调用的错误
                )
                
                # 检查响应状态
                if response.status_code == 200:
                    # 提取生成的文本
                    if response.output and response.output.choices and len(response.output.choices) > 0:
                        response_text = response.output.choices[0].message.content
                        
                        # ==========================================
                        # Token 统计逻辑 (新增部分)
                        # ==========================================
                        input_tokens = 0
                        output_tokens = 0
                        
                        # DashScope 返回的 response 中通常包含 usage 字段
                        if hasattr(response, 'usage') and response.usage:
                            # DashScope 的字段通常是 input_tokens 和 output_tokens
                            input_tokens = getattr(response.usage, 'input_tokens', 0)
                            output_tokens = getattr(response.usage, 'output_tokens', 0)
                        
                        self._token_count_total += (input_tokens + output_tokens)
                        # ==========================================

                        # 计算并输出耗时
                        end = time.time()
                        elapsed_time = end - start
                        if self.verbose >= VERBOSE_MINIMAL:
                            print(f"==========⏱️ API调用耗时: {elapsed_time:.2f}秒 (Tokens: {input_tokens}+{output_tokens})==========")

                        return response_text
                    else:
                        raise Exception(f"阿里云百炼平台响应格式异常: {response}")
                else:
                    raise Exception(f"阿里云百炼平台API调用失败，状态码: {response.status_code}, 错误: {response.message}")
                
            except Exception as e:
                # 计算失败请求的耗时
                end = time.time()
                elapsed_time = end - start
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"调用阿里云百炼平台API失败 (尝试 {attempt}/{self.max_retries}): {str(e)}")
                    print(f"=========⏱️ 失败请求耗时: {elapsed_time:.2f}秒=========")
                self._handle_retry(attempt, e)
        
        # 如果所有重试都失败，将抛出最后一个异常
        raise Exception("所有阿里云API调用尝试均失败")
    
    def generate(
        self,
        prompt: str,
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
    ) -> str:
        """
        使用阿里云百炼平台生成文本
        
        Args:
            prompt: 提示文本
            temperature: 生成温度，覆盖默认值
            top_p: 生成top_p值，覆盖默认值
            max_tokens: 最大生成token数
            
        Returns:
            模型生成的文本
        """
        # 将提示转换为消息格式
        messages = [{"role": "user", "content": prompt}]
        
        # 调用聊天API
        return self.chat(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )