from typing import Dict, Any, List
import json
import re

from ..BaseAgent import BaseAgent
from models.Base import BaseModel
from constants.verboseType import *

class SolutionPlanningAgent(BaseAgent):
    """
    解决方案规划智能体，负责为编程问题设计多种可行的技术方案
    """
    def __init__(
        self,
        model: BaseModel,
        verbose: int = 1,
        enabled: bool = True,
    ):
        """
        初始化解决方案规划智能体
        
        Args:
            model: 模型实例
            verbose: 输出详细程度
            enabled: 是否启用该智能体
        """
        super().__init__(
            model=model,
            verbose=verbose,
            enabled=enabled,
            agent_name="SolutionPlanningAgent",
            prompt_module_path="planning.solution_planning"
        )
    
    def _generate_prompt(self, task_type: str, **kwargs) -> List[Dict[str, str]]:
        """
        根据任务类型生成提示
        
        Args:
            task_type: 任务类型，如'generate_solutions'等
            **kwargs: 任务相关参数
            
        Returns:
            消息列表
        """
        return self.prompt_module.get_messages(task_type, **kwargs)
    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        处理模型响应，提取解决方案
        
        Args:
            response: 模型响应文本
            
        Returns:
            处理后的解决方案
        """
        # 优先尝试从<SOLUTION_JSON>标签中提取JSON
        solution_json_match = re.search(r'<SOLUTION_JSON>\s*(.*?)\s*</SOLUTION_JSON>', response, re.DOTALL)
        
        if solution_json_match:
            try:
                json_str = solution_json_match.group(1).strip()
                # 移除可能的```json标记
                if json_str.startswith('```json'):
                    json_str = json_str[7:]
                if json_str.endswith('```'):
                    json_str = json_str[:-3]
                json_str = json_str.strip()
                
                result = json.loads(json_str)
                return {
                    "structured_data": result,
                    "raw_response": response
                }
            except json.JSONDecodeError as e:
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"<SOLUTION_JSON>标签内JSON解析失败: {e}")
        
        # 备用方案：尝试从响应中提取```json格式的JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        
        if json_match:
            try:
                json_str = json_match.group(1)
                result = json.loads(json_str)
                return {
                    "structured_data": result,
                    "raw_response": response
                }
            except json.JSONDecodeError as e:
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"```json代码块JSON解析失败: {e}")
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"未找到有效的JSON格式，使用传统方法提取解决方案")
        
        # 如果没有找到JSON或解析失败，返回原始响应
        return {
            "structured_data": None,
            "raw_response": response
        }
    
    def generate_solutions(self, problem_description: str, test_cases: Dict[str, Any],thought_content: str, problem_sample_io: Dict[str, Any], attention_analysis: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """
        为编程问题生成多种解决方案
        
        Args:
            problem_description: 问题描述
            test_cases: 测试用例
            
        Returns:
            生成的解决方案
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\nPhase 2: Solution Planning\n{'-'*50}")
            
        result = self.execute(
            task_type="generate_solutions",
            problem_description=problem_description,
            test_cases=test_cases,
            thought_content=thought_content,
            problem_sample_io=problem_sample_io,
            attention_analysis=attention_analysis,
            session_id=session_id
        )
        
        if self.verbose >= VERBOSE_MINIMAL:
            solutions_count = 0
            if result["result"].get("structured_data") and "solutions" in result["result"]["structured_data"]:
                solutions = result["result"]["structured_data"]["solutions"]
                solutions_count = len(solutions)
                print(f"Generated {solutions_count} solution approaches:")
                
                # 显示每个解决方案的名称和算法类型
                for i, solution in enumerate(solutions, 1):
                    name = solution.get("name", f"Solution {i}")
                    print(f"  {i}. {name}")
            else:
                print("No structured solutions were generated.")
            
        return result["result"] 