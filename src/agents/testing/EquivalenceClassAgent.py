from typing import Dict, Any, List
import json
import re

from ..BaseAgent import BaseAgent
from models.Base import BaseModel
from constants.verboseType import *

class EquivalenceClassAgent(BaseAgent):
    """
    等价类测试智能体，专精输入域划分和等价类测试用例生成
    """
    def __init__(
        self,
        model: BaseModel,
        verbose: int = 1,
        enabled: bool = True,
    ):
        """
        初始化等价类测试智能体
        
        Args:
            model: 模型实例
            verbose: 输出详细程度
            enabled: 是否启用该智能体
        """
        super().__init__(
            model=model,
            verbose=verbose,
            enabled=enabled,
            agent_name="等价类测试智能体",
            prompt_module_path="testing.equivalence_class"
        )
    
    def _generate_prompt(self, problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None, sample_io: List[str] = None) -> List[Dict[str, str]]:
        """
        生成等价类测试用例的提示
        
        Args:
            problem_description: 问题描述
            language: 编程语言
            function_signature: 函数签名（可选）
            function_name: 函数名称（可选）
            sample_io: 样例输入输出（可选）
            
        Returns:
            消息列表
        """
        return self.prompt_module.get_messages(problem_description, language, function_signature, function_name, sample_io)
    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        处理模型响应，提取等价类测试用例
        
        Args:
            response: 模型响应文本
            
        Returns:
            处理后的等价类测试用例
        """
        # 尝试从响应中提取JSON格式的结果
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        
        if json_match:
            try:
                json_str = json_match.group(1)
                result = json.loads(json_str)
                return {
                    "type": "equivalence_class",
                    "analysis": response,
                    "structured_data": result,
                    "parameter_analysis": result.get("parameter_analysis", []),
                    "equivalence_classes": result.get("equivalence_classes", []),
                    "test_cases": result.get("test_cases", [])
                }
            except json.JSONDecodeError:
                # JSON解析失败，回退到传统提取方法
                pass
        
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
        
        # 提取参数分析
        param_analysis_match = re.search(r'(?:输入参数分析|参数分析)(?:[：:])?\s*(.*?)(?:等价类划分|$)', response, re.DOTALL)
        param_analysis = param_analysis_match.group(1).strip() if param_analysis_match else ""
        
        # 提取等价类划分
        eq_class_match = re.search(r'(?:等价类划分)(?:[：:])?\s*(.*?)(?:测试用例设计|$)', response, re.DOTALL)
        eq_class = eq_class_match.group(1).strip() if eq_class_match else ""
        
        # 提取测试用例设计
        test_design_match = re.search(r'(?:测试用例设计)(?:[：:])?\s*(.*?)(?:测试代码|$)', response, re.DOTALL)
        test_design = test_design_match.group(1).strip() if test_design_match else ""
        
        return {
            "type": "equivalence_class",
            "analysis": response,
            "param_analysis": param_analysis,
            "equivalence_classes": eq_class,
            "test_design": test_design,
            "test_cases": test_cases,
            "structured_data": None  # 标记为未能提取结构化数据
        }
    
    def generate_test_cases(self, problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None, sample_io: List[str] = None) -> Dict[str, Any]:
        """
        生成等价类测试用例
        
        Args:
            problem_description: 问题描述
            language: 编程语言
            function_signature: 函数签名（可选）
            function_name: 函数名称（可选）
            sample_io: 样例输入输出（可选）
            
        Returns:
            等价类测试用例
        """
        result = self.execute(
            problem_description=problem_description, 
            language=language,
            function_signature=function_signature, 
            function_name=function_name,
            sample_io=sample_io
        )
        return result["result"]
    
    def extract_function_info(self, problem_description: str, language: str = "Python") -> Dict[str, str]:
        """
        从问题描述中提取函数信息
        
        Args:
            problem_description: 问题描述
            language: 编程语言
            
        Returns:
            函数信息，包含函数名称和函数签名
        """
        # 根据不同语言匹配函数定义
        if language.lower() == "python":
            function_match = re.search(r'def\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', problem_description)
        elif language.lower() in ["javascript", "typescript"]:
            function_match = re.search(r'function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', problem_description)
        elif language.lower() == "java":
            # Java方法定义可能更复杂，这里简化处理
            function_match = re.search(r'(?:public|private|protected)?\s+\w+\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', problem_description)
        else:
            # 默认尝试匹配常见的函数定义模式
            function_match = re.search(r'(?:function|def|func)\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', problem_description)
        
        if function_match:
            function_name = function_match.group(1)
            function_params = function_match.group(2)
            
            # 根据语言生成适当的函数签名
            if language.lower() == "python":
                function_signature = f"def {function_name}({function_params})"
            elif language.lower() in ["javascript", "typescript"]:
                function_signature = f"function {function_name}({function_params})"
            elif language.lower() == "java":
                # 简化处理，实际应包含返回类型
                function_signature = f"public returnType {function_name}({function_params})"
            else:
                function_signature = f"{function_name}({function_params})"
            
            return {
                "function_name": function_name,
                "function_signature": function_signature
            }
        
        return {
            "function_name": None,
            "function_signature": None
        } 