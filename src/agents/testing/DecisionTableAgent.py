from typing import Dict, Any, List
import json
import re

from ..BaseAgent import BaseAgent
from models.Base import BaseModel
from constants.verboseType import *

class DecisionTableAgent(BaseAgent):
    """
    判定表测试智能体，专精条件组合测试用例生成
    """
    def __init__(
        self,
        model: BaseModel,
        verbose: int = 1,
        enabled: bool = True,
    ):
        """
        初始化判定表测试智能体
        
        Args:
            model: 模型实例
            verbose: 输出详细程度
            enabled: 是否启用该智能体
        """
        super().__init__(
            model=model,
            verbose=verbose,
            enabled=enabled,
            agent_name="判定表测试智能体",
            prompt_module_path="testing.decision_table"
        )
    
    def _generate_prompt(self, problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None) -> List[Dict[str, str]]:
        """
        生成判定表测试用例的提示
        
        Args:
            problem_description: 问题描述
            language: 编程语言
            function_signature: 函数签名（可选）
            function_name: 函数名称（可选）
            
        Returns:
            消息列表
        """
        return self.prompt_module.get_messages(problem_description, language, function_signature, function_name)
    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        处理模型响应，提取判定表测试用例
        
        Args:
            response: 模型响应文本
            
        Returns:
            处理后的判定表测试用例
        """
        # 尝试从响应中提取JSON格式的结果
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        
        if json_match:
            try:
                json_str = json_match.group(1)
                result = json.loads(json_str)
                
                # 验证并修复测试用例中可能的错误
                if "test_cases" in result:
                    for i, test_case in enumerate(result["test_cases"]):
                        if "assertion" in test_case:
                            # 修复常见的断言语法错误
                            assertion = test_case["assertion"]
                            # 修复双点错误，如 [1..0] -> [1.0]
                            assertion = re.sub(r'(\d)\.\.(\d)', r'\1.\2', assertion)
                            # 修复缺少空格的比较操作符
                            assertion = re.sub(r'([^=])=([^=])', r'\1 = \2', assertion)
                            assertion = re.sub(r'([^!<>])=\s*=([^=])', r'\1 == \2', assertion)
                            # 更新修复后的断言
                            result["test_cases"][i]["assertion"] = assertion
                
                return {
                    "type": "decision_table",
                    "analysis": response,
                    "structured_data": result,
                    "condition_analysis": result.get("condition_analysis", []),
                    "action_analysis": result.get("action_analysis", []),
                    "decision_table": result.get("decision_table", []),
                    "test_cases": result.get("test_cases", [])
                }
            except json.JSONDecodeError as e:
                # JSON解析失败，记录错误并回退到传统提取方法
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"JSON解析失败: {e}")
                    print(f"尝试使用传统方法提取测试用例")
        
        # 如果没有找到JSON或解析失败，尝试传统方法提取
        # 提取测试用例（断言形式）
        test_cases = []
        
        # 尝试提取代码块中的断言
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', response, re.DOTALL)
        for block in code_blocks:
            assertions = [line.strip() for line in block.split('\n') if line.strip().startswith('assert') or 'assert' in line.strip()]
            test_cases.extend(assertions)
        
        # 如果代码块中没有找到断言，尝试从文本中直接提取
        if not test_cases:
            lines = response.split('\n')
            for line in lines:
                if line.strip().startswith('assert') or 'assert' in line.strip():
                    test_cases.append(line.strip())
        
        # 提取条件分析
        condition_analysis_match = re.search(r'(?:条件分析|输入条件分析)(?:[：:])?\s*(.*?)(?:动作分析|输出动作分析|$)', response, re.DOTALL)
        condition_analysis = condition_analysis_match.group(1).strip() if condition_analysis_match else ""
        
        # 提取动作分析
        action_analysis_match = re.search(r'(?:动作分析|输出动作分析)(?:[：:])?\s*(.*?)(?:判定表|决策表|$)', response, re.DOTALL)
        action_analysis = action_analysis_match.group(1).strip() if action_analysis_match else ""
        
        # 提取判定表
        decision_table_match = re.search(r'(?:判定表|决策表)(?:[：:])?\s*(.*?)(?:测试用例设计|$)', response, re.DOTALL)
        decision_table = decision_table_match.group(1).strip() if decision_table_match else ""
        
        # 提取测试用例设计
        test_design_match = re.search(r'(?:测试用例设计)(?:[：:])?\s*(.*?)(?:测试代码|$)', response, re.DOTALL)
        test_design = test_design_match.group(1).strip() if test_design_match else ""
        
        return {
            "type": "decision_table",
            "analysis": response,
            "condition_analysis": condition_analysis,
            "action_analysis": action_analysis,
            "decision_table": decision_table,
            "test_design": test_design,
            "test_cases": test_cases,
            "structured_data": None  # 标记为未能提取结构化数据
        }
    
    def generate_test_cases(self, problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None) -> Dict[str, Any]:
        """
        生成判定表测试用例
        
        Args:
            problem_description: 问题描述
            language: 编程语言
            function_signature: 函数签名（可选）
            function_name: 函数名称（可选）
            
        Returns:
            判定表测试用例
        """
        result = self.execute(
            problem_description=problem_description, 
            language=language,
            function_signature=function_signature, 
            function_name=function_name
        )
        return result["result"] 