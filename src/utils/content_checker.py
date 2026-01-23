"""
内容检查器 - 用于检测AI响应是否重复
"""

from typing import Dict, Any


class ContentChecker:
    """
    内容检查器，用于检测AI是否重复生成相同内容
    """
    
    def __init__(self, verbose: int = 0):
        self.verbose = verbose
    
    def check_content_similarity(self, current_response: str, previous_content: str, model=None, turn_number: int = 1) -> Dict[str, Any]:
        """
        检查当前响应与前一次内容是否相同
        
        Args:
            current_response: 当前AI的响应
            previous_content: 前一次的内容
            model: 模型实例（用于初始化CTOAgent）
            
        Returns:
            Dict containing:
            - is_similar: bool, 是否相似/重复
            - feedback: str, 反馈信息
            - raw_response: str, CTO的原始响应
        """
        if self.verbose >= 1:
            print(f"\n[ContentChecker] 开始检查内容相似性...")
        
        # 每次都创建新的CTO agent实例用于判断
        if not model:
            if self.verbose >= 1:
                print(f"[ContentChecker] 警告: 未提供model实例，无法进行检查")
            return {
                "is_similar": False,
                "feedback": "未提供模型实例，跳过检查",
                "raw_response": "No model provided"
            }
        
        # 调用CTO来判断内容是否相同
        try:
            result = self._check_with_cto(current_response, previous_content, model, turn_number)
            
            if self.verbose >= 1:
                print(f"[ContentChecker] 检查结果: {'相似' if result['is_similar'] else '不相似'}")
                if result['is_similar']:
                    print(f"[ContentChecker] 反馈: {result['feedback']}")
            
            return result
            
        except Exception as e:
            if self.verbose >= 1:
                print(f"[ContentChecker] 检查时出错: {e}")
            
            # 出错时默认认为不相似，避免阻塞流程
            return {
                "is_similar": False,
                "feedback": "内容检查器出现错误，默认允许继续",
                "raw_response": str(e)
            }
    
    def _check_with_cto(self, current_response: str, previous_content: str, model, turn_number: int) -> Dict[str, Any]:
        """
        使用CTO Agent来检查内容相似性
        """
        # 创建新的CTO Agent实例 (延迟导入避免循环依赖)
        from agents.core.CTOAgent import CTOAgent
        cto_agent = CTOAgent(model=model, verbose=self.verbose)
        check_prompt = f"""
Please compare the following two pieces of content and determine if they are essentially the same or very similar in terms of the main ideas, solutions, or approaches.

Current Response:
{current_response}

Previous Content:
{previous_content}

Please analyze:
0. If you are checking the code, please ignore the comment sections and only verify whether the code is similar.
1. Are the main ideas/solutions essentially the same?
2. Are there only minor word changes but the same approach?
3. Is this likely a repetitive response that doesn't add new value?

Return your analysis in JSON format:
{{
  "is_similar": true/false,
  "similarity_score": 0-100,
  "feedback": "Detailed explanation of why they are similar/different and suggestions for improvement"
}}
"""
        
        # 构建消息
        messages = [
            {"role": "system", "content": "You are an expert content analyzer. Your task is to determine if two pieces of content are essentially the same or repetitive."},
            {"role": "user", "content": check_prompt}
        ]
        
        # 使用CTO Agent的_call_model方法
        response = cto_agent._call_model(messages,session_id=None)
        
        # 解析响应
        try:
            import re
            import json
            
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group(1))
            else:
                # 尝试直接解析整个响应
                result_data = json.loads(response)
            
            is_similar = result_data.get("is_similar", False)
            similarity_score = result_data.get("similarity_score", 0)
            feedback = result_data.get("feedback", "")
            
            # 根据轮数设置不同的相似度阈值
            # 奇数轮：100分（更严格），偶数轮：95分（现有标准）
            threshold = 100 if turn_number % 2 == 1 else 95
            
            # 主要基于相似度分数判断
            if similarity_score >= threshold:
                return {
                    "is_similar": True,
                    "feedback": f"内容重复！相似度: {similarity_score}% (>={threshold}%, 第{turn_number}轮). {feedback}",
                    "raw_response": response
                }
            else:
                return {
                    "is_similar": False,
                    "feedback": f"内容通过检查。相似度: {similarity_score}% (<{threshold}%, 第{turn_number}轮). {feedback}",
                    "raw_response": response
                }
                
        except (json.JSONDecodeError, KeyError) as e:
            # JSON解析失败，默认通过检查（保守策略，避免误拦截）
            if self.verbose >= 1:
                print(f"[ContentChecker] JSON解析失败，采用保守策略通过检查: {e}")
            return {
                "is_similar": False,
                "feedback": f"JSON解析失败，默认通过检查。原始响应长度: {len(response)}",
                "raw_response": response
            }
    
    def generate_retry_message(self, original_message: str, feedback: str) -> str:
        """
        生成重试消息，要求AI提供不同的内容
        
        Args:
            original_message: 原始消息
            feedback: 反馈信息
            
        Returns:
            重试消息
        """
        retry_message = f"""
Your previous response was identified as repetitive or too similar to earlier content.
!!!Your solution has been verified in a real-world environment and proven incorrect.!!!
!!! especially for the coder,you generated the toally wrong code every time ,if you(coder) write the same code again,I will punish you!!!
Feedback: {feedback}

YOU MUST THINK ABOUT WHY YOU ARE REPEATING THE SAME CONTENT.

Please generate a substantially different response now.
"""
        return retry_message 