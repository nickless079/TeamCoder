from typing import List, Dict, Any, Union, Tuple
import json
import os
import re

from .Dataset import Dataset
from constants.paths import MBPP_PY_DATA_PATH
from evaluations.func_evaluate import evaluate_mbpp_functional_correctness, evaluate_mbpp_sample_io

class MBPPDataset(Dataset):
    """
    MBPP数据集实现
    """
    def __init__(
        self,
        path: str = MBPP_PY_DATA_PATH,
    ):
        """
        初始化MBPP数据集
        
        Args:
            path: 数据集文件路径
        """
        super().__init__(path)
        self.id_key = "task_id"
        
        # 将MBPP格式转换为HumanEval标准格式
        for item in self.data:
            self._convert_to_humaneval_format(item)
    
    def _convert_to_humaneval_format(self, item: Dict[str, Any]) -> None:
        """
        确保MBPP数据项包含所有必需字段
        
        Args:
            item: 数据项（会被就地修改）
        """
        # 1. 转换task_id字段

        if "name" in item and "task_id" not in item:
            item["task_id"] = f"MBPP/{item['name']}"
        
        # 2. 确保有test_list字段供MBPP评估函数使用
        if "test_list" not in item:
            # 从test代码中提取测试用例
            item["test_list"] = self._extract_test_list_from_test(item)
        
        # 3. 确保有sample_io字段供工作流使用
        if "sample_io" not in item:
            item["sample_io"] = self._extract_sample_io_from_test(item)
        elif not isinstance(item["sample_io"], list):
            item["sample_io"] = []
    
    def _extract_test_list_from_test(self, item: Dict[str, Any]) -> List[str]:
        """
        从测试代码中提取测试用例列表（供MBPP评估函数使用）
        
        Args:
            item: 数据项
            
        Returns:
            测试用例列表
        """
        test_code = item.get("test", "")
        if not test_code:
            return []
        
        # 提取check函数内的断言语句
        test_list = []
        in_check_function = False
        
        for line in test_code.split("\n"):
            line = line.strip()
            if line.startswith("def check("):
                in_check_function = True
                continue
            elif in_check_function and line.startswith("def "):
                # 遇到新函数定义，退出check函数
                break
            elif in_check_function and line.startswith("assert"):
                test_list.append(line)
        
        return test_list
    
    def _extract_sample_io_from_test(self, item: Dict[str, Any]) -> List[str]:
        """
        从测试代码中提取样例输入输出（供工作流使用）
        
        Args:
            item: 数据项
            
        Returns:
            样例输入输出列表
        """
        # 如果已经有sample_io字段，直接使用
        if "sample_io" in item and isinstance(item["sample_io"], list):
            return item["sample_io"]
        
        # 否则从test_list中获取前3个作为样例
        test_list = self._extract_test_list_from_test(item)
        return test_list[:3]
    
    def evaluate(
        self,
        item: Dict[str, Any],
        code: str,
        language: str,
    ) -> bool:
        """
        评估生成的代码
        
        Args:
            item: 数据项
            code: 生成的代码
            language: 编程语言
            
        Returns:
            评估结果，True表示通过
        """
        result = evaluate_mbpp_functional_correctness(
            test=item["test"],
            entry_point=item["entry_point"],
            completion=code,
        )
        return result == "passed"
    
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
        
        return evaluate_mbpp_sample_io(
            sample_io=item["sample_io"],
            completion=code,
            entry_point=item["entry_point"],            
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
        
        return evaluate_mbpp_sample_io(
            sample_io=additional_io,
            completion=code,
            entry_point="",  # 额外IO测试不需要entry_point           
        )
    
    def get_prompt(self, item: Dict[str, Any]) -> str:
        """
        从数据项中提取问题描述
        
        Args:
            item: 数据项
            
        Returns:
            问题描述文本
        """
        if "prompt" in item:
            return f"{item['prompt'].strip()}"
        elif "text" in item:
            return f"{item['text'].strip()}"
        else:
            raise Exception("数据项中没有prompt或text字段") 