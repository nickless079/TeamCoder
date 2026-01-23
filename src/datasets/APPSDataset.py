from typing import List, Dict, Any, Union, Tuple
import json
import os
import re

from .Dataset import Dataset
from constants.paths import APPS_DATA_PATH
from evaluations.evalute import contest_evaluate, contest_evaluate_public_tests

class APPSDataset(Dataset):
    """
    APPS数据集实现
    """
    def __init__(
        self,
        path: str = APPS_DATA_PATH,
    ):
        """
        初始化APPS数据集
        
        Args:
            path: 数据集文件路径
        """
        super().__init__(path)
        self.id_key = "id"  # APPS 数据集使用 "id" 作为主键
        
        # 确保APPS数据包含所有必需字段
        for item in self.data:
            self._convert_to_standard_format(item)
    
    def _convert_to_standard_format(self, item: Dict[str, Any]) -> None:
        """
        确保APPS数据项包含所有必需字段
        
        Args:
            item: 数据项（会被就地修改）
        """
        # 1. 添加 task_id 字段（用于兼容某些接口）
        if "id" in item and "task_id" not in item:
            item["task_id"] = f"APPS/{item['id']}"
        
        # 2. 确保有 sample_io 字段
        if "sample_io" not in item:
            item["sample_io"] = []
    
        # 3. 确保有 test_list 字段
        if "test_list" not in item:
            item["test_list"] = []
    
    def evaluate(
        self,
        item: Dict[str, Any],
        code: str,
        language: str,
    ) -> bool:
        """
        评估生成的代码（使用完整的隐藏测试用例，通过 ExecEval）
        
        Args:
            item: 数据项
            code: 生成的代码
            language: 编程语言
            
        Returns:
            评估结果，True表示通过
        """
        # 使用 ExecEval 评估完整的测试用例
       
            
        return contest_evaluate(
            generated_code=code,
            id=item["id"],
            tests=item["test_list"],
            lang=language
        )
    
    def evaluate_sample_io(
        self,
        item: Dict[str, Any],
        code: str,
        language: str,
    ) -> Tuple[bool, str]:
        """
        使用样例输入输出评估代码（通过 ExecEval）
        
        Args:
            item: 数据项
            code: 生成的代码
            language: 编程语言
            
        Returns:
            (是否通过, 测试日志)
        """
        if "sample_io" not in item or len(item["sample_io"]) == 0:
            return True, ""
        
        # 使用 ExecEval 评估样例 IO
        return contest_evaluate_public_tests(
            generated_code=code,
            id=item["id"],
            tests=item["sample_io"],
            lang=language
        )
    
    def evaluate_additional_io(
        self,
        id_value: str,
        additional_io: List[Dict],
        code: str,
        language: str,
    ) -> Tuple[bool, str]:
        """
        使用额外的输入输出评估代码（通过 ExecEval）
        
        Args:
            id_value: 数据项ID
            additional_io: 额外的测试用例（格式：[{"input": "...", "output": [...]}]）
            code: 生成的代码
            language: 编程语言
            
        Returns:
            (是否通过, 测试日志)
        """
        if not additional_io:
            return True, ""
        
        # 使用 ExecEval 评估额外的测试用例
        return contest_evaluate_public_tests(
            generated_code=code,
            id=id_value,
            tests=additional_io,
            lang=language
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
        
        # 添加样例输入输出格式
        sample_io_format = ""
        if "sample_io" in item and len(item["sample_io"]) > 0:
            first_sample = item["sample_io"][0]
            if isinstance(first_sample, dict):
                input_data = first_sample.get("input", "")
                output_data = first_sample.get("output", [""])
                if isinstance(output_data, list):
                    output_data = output_data[0] if output_data else ""
                
                sample_io_format = f"Sample Input Format:\n{input_data}\nSample Output Format:\n{output_data}\n\n-------\n"
        
        prompt = f"{description}\n-------\n"
        prompt += "Important Note: You must follow the input output format. Input should be taken from standard input and output should be given to standard output.\n"
        prompt += "Note: If you are writing a function then after the function definition take input from using `input()` function, call the function with specified parameters and finally print the output of the function."

        
        return prompt 