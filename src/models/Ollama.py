from typing import List, Dict, Any, Union, Optional
import os
import time
import requests
import json
import copy

from .Base import BaseModel

class OllamaModel(BaseModel):
    """
    Ollama模型实现，支持本地大语言模型如Qwen3
    """
    def __init__(
        self,
        model_name: str = "qwen3:14b",
        temperature: float = 0,
        top_p: float = 0.95,
        max_retries: int = 3,
        retry_delay: int = 5,
        api_base: str = "http://localhost:11434",
        disable_thinking: bool = True,
    ):
        """
        初始化Ollama模型
        
        Args:
            model_name: 模型名称，如"qwen3:14b"
            temperature: 生成温度
            top_p: 生成top_p值
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
            api_base: Ollama API基础URL
            disable_thinking: 是否关闭思考模式，添加/no_think标记
        """
        super().__init__(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self.api_base = api_base
        self.disable_thinking = disable_thinking
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

    def _estimate_tokens(self, text: str) -> int:
        """
        简单估算文本 token 数
        """
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            # 简单兜底估算：平均每 4 个字符算一个 token
            return max(1, len(text) // 4)
         
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
        发送聊天请求到Ollama模型
        
        Args:
            messages: 消息列表，每个消息是包含'role'和'content'的字典
            temperature: 生成温度，覆盖默认值
            top_p: 生成top_p值，覆盖默认值
            max_tokens: 最大生成token数
            frequency_penalty: 频率惩罚（Ollama可能不支持）
            presence_penalty: 存在惩罚（Ollama可能不支持）
            
        Returns:
            模型生成的回复文本
        """
        temp = temperature if temperature is not None else self.temperature
        top_p_val = top_p if top_p is not None else self.top_p
        
        # 创建消息的深拷贝，避免修改原始消息
        messages_copy = copy.deepcopy(messages)
        
        # 转换消息格式以适应Ollama API
        # Ollama期望的格式是[{"role": "user", "content": "..."}]
        # 确保消息格式正确
        for msg in messages_copy:
            if msg["role"] not in ["user", "assistant", "system"]:
                msg["role"] = "user"
        
        # 新版本 Ollama 不再需要在消息内容中添加 /no_think
        # 而是通过 API 参数 "think": false 来控制思考模式
       
        for attempt in range(1, self.max_retries + 1):
            try:
                # Ollama API调用，添加合理的超时时间
                response = requests.post(
                    f"{self.api_base}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages_copy,
                        "options": {
                            "temperature": temp,
                            "top_p": top_p_val,
                            #"top_k": 15,
                            "num_predict": max_tokens if max_tokens else 4096
                        },
                        "think": not self.disable_thinking,  # 新版本 Ollama 使用 think 参数控制思考模式
                        "stream": False
                    },
                    timeout=300  # 5分钟超时
                )
                
                response.raise_for_status()  # 如果响应状态码不是200，抛出异常
                print(f"Ollama API响应状态码: {response.status_code}")
                # 解析响应
                result = response.json()

                # ---- token 统计逻辑 ----
                input_tokens = 0
                output_tokens = 0
                # 尝试从 Ollama 响应中读取 token 信息
                if "eval_count" in result:
                    output_tokens = result.get("eval_count", 0)
                    input_tokens = result.get("prompt_eval_count", 0)
                elif "message" in result and "content" in result["message"]:
                    output_text = result["message"]["content"]
                    input_text = "\n".join([m["content"] for m in messages_copy])
                    input_tokens = self._estimate_tokens(input_text)
                    output_tokens = self._estimate_tokens(output_text)
                else:
                    raise Exception(f"Ollama API返回了意外的响应格式: {result}")

                self._token_count_total += (input_tokens + output_tokens)

                if "message" in result and "content" in result["message"]:
                    return result["message"]["content"]
                else:
                    raise Exception(f"Ollama API返回了意外的响应格式: {result}")
                    
            except requests.exceptions.Timeout as e:
                print(f"第{attempt}次尝试超时: {e}")
                self._handle_retry(attempt, e)
            except requests.exceptions.RequestException as e:
                print(f"第{attempt}次尝试网络错误: {e}")
                self._handle_retry(attempt, e)
            except Exception as e:
                print(f"第{attempt}次尝试其他错误: {e}")
                self._handle_retry(attempt, e)
        
        # 如果所有重试都失败，将抛出最后一个异常
        raise Exception("所有Ollama API调用尝试均失败")
    
    def generate(
        self,
        prompt: str,
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
    ) -> str:
        """
        使用Ollama的生成API（而非聊天API）
        
        Args:
            prompt: 提示文本
            temperature: 生成温度，覆盖默认值
            top_p: 生成top_p值，覆盖默认值
            max_tokens: 最大生成token数
            
        Returns:
            模型生成的文本
        """
        # 由于某些Ollama模型可能不支持直接生成API，
        # 我们可以使用聊天API作为后备方案
        messages = [{"role": "user", "content": prompt}]
        
        # 首先尝试使用生成API
        temp = temperature if temperature is not None else self.temperature
        top_p_val = top_p if top_p is not None else self.top_p
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # 尝试使用Ollama生成API
                response = requests.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "options": {
                            "temperature": temp,
                            "top_p": top_p_val,
                            "num_predict": max_tokens if max_tokens else 8192,
                        },
                        "think": not self.disable_thinking,  # 新版本 Ollama 使用 think 参数控制思考模式
                        "stream": False
                    },
                    timeout=300  # 5分钟超时
                )
                
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                if "response" in result:
                    return result["response"]
                else:
                    # 如果响应格式不正确，尝试聊天API
                    print("生成API响应格式不正确，尝试使用聊天API...")
                    break
                    
            except requests.exceptions.RequestException as e:
                # 如果是最后一次尝试，则尝试聊天API
                if attempt == self.max_retries:
                    print(f"生成API调用失败: {e}，尝试使用聊天API...")
                    break
                self._handle_retry(attempt, e)
            except Exception as e:
                # 如果是最后一次尝试，则尝试聊天API
                if attempt == self.max_retries:
                    print(f"生成API调用失败: {e}，尝试使用聊天API...")
                    break
                self._handle_retry(attempt, e)
        
        # 如果生成API失败，尝试使用聊天API
        try:
            return self.chat(messages, temperature, top_p, max_tokens)
        except Exception as e:
            raise Exception(f"生成失败，聊天API也失败: {e}")
    
    def get_available_models(self) -> List[str]:
        """
        获取Ollama可用的模型列表
        
        Returns:
            可用模型名称列表
        """
        try:
            response = requests.get(f"{self.api_base}/api/tags")
            response.raise_for_status()
            
            result = response.json()
            if "models" in result:
                return [model["name"] for model in result["models"]]
            else:
                return []
                
        except Exception as e:
            print(f"获取可用模型列表失败: {e}")
            return [] 