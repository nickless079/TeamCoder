from typing import List, Dict, Any, Union, Tuple
import json
import os
import re

from .Dataset import Dataset
from constants.paths import XCODE_PROG_SYN_PATH
from evaluations.func_evaluate import evaluate_io

class XCodeDataset(Dataset):
    """
    XCodeEval数据集实现
    """
    def __init__(
        self,
        path: str = XCODE_PROG_SYN_PATH,
    ):
        """
        初始化XCodeEval数据集
        
        Args:
            path: 数据集文件路径
        """
        super().__init__(path)
        self.id_key = "task_id"
        
        # 确保XCode数据包含所有必需字段
        for item in self.data:
            self._convert_to_standard_format(item)
    
    def _convert_to_standard_format(self, item: Dict[str, Any]) -> None:
        """
        确保XCode数据项包含所有必需字段
        
        Args:
            item: 数据项（会被就地修改）
        """
        # 1. 转换task_id字段
        if "src_uid" in item:
            item["task_id"] = f"XCode/{item['src_uid']}"
        
        # 2. 确保有test_cases字段供评估函数使用
        if "test_cases" not in item:
            item["test_cases"] = self._extract_test_cases(item)
        
        # 3. 确保有sample_io字段供工作流使用
        if "sample_io" not in item:
            item["sample_io"] = self._create_sample_io(item)
    
    def _create_sample_io(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从样例输入输出创建测试用例
        
        Args:
            item: 数据项
            
        Returns:
            样例输入输出列表
        """
        sample_io = []
        
        sample_inputs = item.get("sample_inputs", [])
        sample_outputs = item.get("sample_outputs", [])
        
        # 确保输入输出数量匹配
        min_len = min(len(sample_inputs), len(sample_outputs))
        
        for i in range(min_len):
            sample_io.append({
                "input": sample_inputs[i],
                "output": [sample_outputs[i]]
            })
        
        return sample_io
    
    def _extract_test_cases(self, item: Dict[str, Any]) -> List[str]:
        """
        从XCode数据项中提取测试用例
        
        Args:
            item: 数据项
            
        Returns:
            测试用例列表
        """
        sample_io_data = self._create_sample_io(item)
        test_cases = []
        
        for test_case in sample_io_data:
            if isinstance(test_case, dict):
                input_data = test_case.get("input", "")
                output_data = test_case.get("output", [""])
                if isinstance(output_data, list):
                    output_data = output_data[0] if output_data else ""
                
                # 构造测试字符串
                test_str = f"# Test case\ninput_data = '''{input_data}'''\nexpected_output = '''{output_data}'''"
                test_cases.append(test_str)
        
        return test_cases
    
    def evaluate(
        self,
        item: Dict[str, Any],
        code: str,
        language: str,
    ) -> bool:
        """
        评估生成的代码（使用样例输入输出）
        
        Args:
            item: 数据项
            code: 生成的代码
            language: 编程语言
            
        Returns:
            评估结果，True表示通过
        """
        # XCodeEval主要使用样例IO评估
        if "sample_io" in item and len(item["sample_io"]) > 0:
            result, _ = self.evaluate_sample_io(item, code, language)
            return result
        
        # 如果没有样例IO，返回True（表示无法验证）
        return True
    
    def evaluate_sample_io(
        self,
        item: Dict[str, Any],
        code: str,
        language: str,
    ) -> Tuple[bool, str]:
        """
        使用样例输入输出评估代码
        
        Args:
            item: 数据项
            code: 生成的代码
            language: 编程语言
            
        Returns:
            (是否通过, 测试日志)
        """
        if "sample_io" not in item or len(item["sample_io"]) == 0:
            return True, ""
        
        # 将XCode格式的测试用例转换为evaluate_io支持的格式
        sample_tests = []
        for test_case in item["sample_io"]:
            if isinstance(test_case, dict):
                input_data = test_case.get("input", "")
                output_data = test_case.get("output", [""])
                if isinstance(output_data, list):
                    output_data = output_data[0] if output_data else ""
                
                # 构造测试字符串
                test_str = f"# Test case\ninput_data = '''{input_data}'''\nexpected_output = '''{output_data}'''"
                sample_tests.append(test_str)
        
        if not sample_tests:
            return True, ""
        
        return evaluate_io(
            sample_io=sample_tests,
            completion=code,            
        )
    
    def evaluate_additional_io(
        self,
        id_value: str,
        additional_io: List[str],
        code: str,
        language: str,
    ) -> Tuple[bool, str]:
        """
        使用额外的输入输出评估代码
        
        Args:
            id_value: 数据项ID
            additional_io: 额外的测试用例
            code: 生成的代码
            language: 编程语言
            
        Returns:
            (是否通过, 测试日志)
        """
        if not additional_io:
            return True, ""
        
        return evaluate_io(
            sample_io=additional_io,
            completion=code,            
        )
    
    def get_prompt(self, item: Dict[str, Any]) -> str:
        """
        从数据项中提取问题描述
        
        Args:
            item: 数据项
            
        Returns:
            问题描述文本
        """
        description = item.get("description", "")
        input_spec = item.get("input_spec", "")
        output_spec = item.get("output_spec", "")
        notes = item.get("notes", "")
        input_from = item.get("input_from", "")
        output_to = item.get("output_to", "")
        
        sample_inputs = item.get("sample_inputs", [])
        sample_outputs = item.get("sample_outputs", [])
        
        prompt = f"Problem Description:\n{description}\n"
        
        if input_spec:
            prompt += f"Input Specification:\n{input_spec}\n"
        
        if output_spec:
            prompt += f"Output Specification:\n{output_spec}\n"
        
        if sample_inputs:
            prompt += f"Sample Inputs: {sample_inputs}\n"
        
        if sample_outputs:
            prompt += f"Sample Outputs: {sample_outputs}\n"
        
        prompt += "\n-------\n"
        prompt += "Important Note: If you are writing a function then after the function definition take input from using `input()` function, call the function with specified parameters and finally print the output of the function.\n"
        
        if notes:
            prompt += f"Note: {notes}\n"
        
        if input_from:
            prompt += f"Take input from: {input_from}\n"
        
        if output_to:
            prompt += f"Give output to: {output_to}"
        
        return prompt 