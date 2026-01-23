from typing import Dict, Any, List, Optional
import json
import re

from ..BaseAgent import BaseAgent
from models.Base import BaseModel
from constants.verboseType import *

class AttentionAgent(BaseAgent):
    """
    注意力智能体，专门用于找出编程问题中最容易被忽视但最致命的关键点
    """
    def __init__(
        self,
        model: BaseModel,
        verbose: int = 1,
        enabled: bool = True,
    ):
        """
        初始化注意力智能体
        
        Args:
            model: 模型实例
            verbose: 输出详细程度
            enabled: 是否启用该智能体
        """
        super().__init__(
            model=model,
            verbose=verbose,
            enabled=enabled,
            agent_name="AttentionAgent",
            prompt_module_path="core.attention"
        )
    
    def _generate_prompt(self, task_type: str, **kwargs) -> List[Dict[str, str]]:
        """
        根据任务类型生成提示
        
        Args:
            task_type: 任务类型，如'extract_key_points', 'analyze_problem'等
            **kwargs: 任务相关参数
            
        Returns:
            消息列表
        """
        return self.prompt_module.get_messages(task_type, **kwargs)
    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        处理模型响应，提取最致命的关键点和复查内容
        
        Args:
            response: 模型响应文本
            
        Returns:
            处理后的结果
        """
        result = {
            "raw_response":response,
            "fatal_points": "",
            "recheck": ""
        }
        print(f"致命缺点\n\n:{response}\n\n")
        #提取最致命的关键点和复查内容
        try:
            # 提取 <points> 标签内容
            points_match = re.search(r'<POINTS>(.*?)</POINTS>', response, re.DOTALL | re.IGNORECASE)
            if points_match:
                result["fatal_points"] = points_match.group(1).strip()
            
            # 提取 <recheck> 标签内容
            recheck_match = re.search(r'<RECHECK>(.*?)</RECHECK>', response, re.DOTALL | re.IGNORECASE)
            if recheck_match:
                result["recheck"] = recheck_match.group(1).strip()
            
            # 如果都没有找到标签，返回整个响应作为兜底
            if not points_match and not recheck_match:
                result["fatal_points"] = response.strip()
                
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"处理AttentionAgent响应时出错: {e}")
            result["fatal_points"] = response.strip()
        
        return result
    
    def find_fatal_points(
        self,
        problem_description: str,
        sample_io: List[str] = None,
        error_info: List[str] = None,
        error_code: str = "",
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        找出编程问题中最容易被忽视但最致命的关键点
        
        Args:
            problem_description: 问题描述
            sample_io: 样例输入输出
            
        Returns:
            包含最致命关键点的结果
        """
        if not self.enabled:
            return {"fatal_points": "AttentionAgent未启用"}
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n[{self.agent_name}] 寻找最容易被忽视的致命关键点...")
        
        # 生成提示
        messages = self._generate_prompt(
            task_type="find_fatal_points",
            problem_description=problem_description,
            sample_io=sample_io or [],
            error_info=error_info or [],
            error_code=error_code
        )
        
        # 调用模型
        response = self._call_model(messages, session_id=session_id)
        
        # 处理响应
        result = self._process_response(response)
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"[{self.agent_name}] 最致命的关键点:")
            print(f"  {result.get('fatal_points', '未找到')}")
            print(f"  {result.get('recheck', '未找到')}")
        
        return result
    
    def self_correction(
        self,
        problem_description: str,
        fatal_points: str,
        recheck: str,
        session_id: str = None,
        sample_io: List[str] = None
    ) -> Dict[str, Any]:
        """
        对之前的分析进行自我纠错，特别是检查计算错误或逻辑错误
        
        Args:
            fatal_points: 之前分析的关键点
            recheck: 之前的复查内容
            session_id: 会话ID，用于继续之前的对话
            
        Returns:
            纠错后的结果，包含fatal_points和recheck
        """
     
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n[{self.agent_name}] 进行自我纠错...")
        
        # 生成提示
        messages = self._generate_prompt(
            task_type="self_correction",
            problem_description=problem_description,
            sample_io=sample_io or [],
            fatal_points=fatal_points,
            recheck=recheck
        )
        
        # 调用模型，使用相同的session_id继续对话
        response = self._call_model(messages, session_id=session_id)
        
        # 解析响应，提取纠错后的内容
        import re
        
        result = {
            "fatal_points": fatal_points,  # 默认保持原内容
            "recheck": recheck,           # 默认保持原内容
            "raw_response": response
        }
        
        # 提取POINTS标签内容 (fatal_points)
        points_match = re.search(r'<POINTS>\s*(.*?)\s*</POINTS>', response, re.DOTALL | re.IGNORECASE)
        if points_match:
            result["fatal_points"] = points_match.group(1).strip()
        
        # 提取RECHECK标签内容
        recheck_match = re.search(r'<RECHECK>\s*(.*?)\s*</RECHECK>', response, re.DOTALL | re.IGNORECASE)
        if recheck_match:
            result["recheck"] = recheck_match.group(1).strip()
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"[{self.agent_name}] 自我纠错完成")
            if self.verbose >= VERBOSE_FULL:
                print(f"  纠错后的关键点: {result['fatal_points'][:100]}...")
                if result['recheck']:
                    print(f"  纠错后的复查: {result['recheck'][:100]}...")
        
        return result

    def find_stage_errors(
        self,
        problem_description: str,
        content: str,
        sample_io: List[str] = None
    ) -> Dict[str, Any]:
        """
        寻找阶段内容中的致命错误点
        
        Args:
            problem_description: 问题描述
            content: 要分析的阶段内容
            sample_io: 样例输入输出
            
        Returns:
            包含致命错误点的结果
        """
        if not self.enabled:
            return {"fatal_points": "AttentionAgent未启用"}
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n[{self.agent_name}] 寻找阶段内容中的致命错误...")
        
        # 生成提示
        messages = self._generate_prompt(
            task_type="find_stage_errors",
            problem_description=problem_description,
            content=content,
            sample_io=sample_io or []
        )
        
        # 调用模型
        response = self._call_model(messages)
        
        # 处理响应
        result = self._process_response(response)
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"[{self.agent_name}] 阶段致命错误点:")
            print(f"  {result.get('fatal_points', '未找到')}")
        
        return result
    
    def generate_blueprint(
        self,
        problem_description: str,
        sample_io: List[str] = None,
        error_code: str = "",
        error_info: List[str] = None,
        trap: str = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        根据问题描述和样例生成问题蓝图
        
        Args:
            problem_description: 问题描述
            sample_io: 样例输入输出
            
        Returns:
            包含问题蓝图的结果
        """
        if not self.enabled:
            return {"blueprint_json": {}}

        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\\n[{self.agent_name}] 正在生成问题蓝图...")

        # 生成提示
        messages = self._generate_prompt(
            task_type="generate_blueprint",
            problem_description=problem_description,
            sample_io=sample_io or [],
            error_code=error_code,
            trap=trap or "",
            error_info=error_info or []
        )

        # 调用模型
        response = self._call_model(messages, session_id=session_id)

        try:
            # 尝试解析JSON格式的蓝图
            blueprint_json = json.loads(response)
        except json.JSONDecodeError:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"[{self.agent_name}] 解析蓝图JSON失败。原始响应: {response}")
            blueprint_json = {}

        if self.verbose >= VERBOSE_MINIMAL:
            print(f"[{self.agent_name}] 蓝图生成完毕。")

        return {"blueprint_json": blueprint_json, "raw_response": response}

    def analyze_traps(
        self,
        problem_blueprint_json: str,
        problem_description: str,
        sample_io: List[str] = None,
        error_code: str = "",
        error_info: List[str] = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        分析问题蓝图，寻找致命陷阱
        
        Args:
            problem_blueprint_json: 问题蓝图的JSON字符串
            problem_description: 问题描述
            sample_io: 样例输入输出
            
        Returns:
            包含致命陷阱的分析结果
        """
        if not self.enabled:
            return {"fatal_points": "AttentionAgent未启用"}
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\\n[{self.agent_name}] 正在分析蓝图中的陷阱...")
        
        # 生成提示
        messages = self._generate_prompt(
            task_type="analyze_traps",
            problem_blueprint_json=problem_blueprint_json,
            problem_description=problem_description,
            error_code=error_code,
            error_info=error_info or [],
            sample_io=sample_io or []
        )
        
        # 调用模型
        response = self._call_model(messages, session_id=session_id)
        result = self._process_response(response)
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"[{self.agent_name}] 陷阱分析完成。")
            print(f"  致命点: {result.get('fatal_points', '未找到')}")
        
        return result