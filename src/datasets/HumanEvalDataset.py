from typing import List, Dict, Any, Union, Tuple
import json
import os
import re

from .Dataset import Dataset
from constants.paths import HUMAN_DATA_PATH
from evaluations.func_evaluate import evaluate_functional_correctness, evaluate_io

class HumanEvalDataset(Dataset):
    """
    HumanEval数据集实现
    """
    def __init__(
        self,
        path: str = HUMAN_DATA_PATH,
    ):
        """
        初始化HumanEval数据集
        
        Args:
            path: 数据集文件路径
        """
        super().__init__(path)
        self.id_key = "task_id"
        
        # 为每个问题添加样例输入输出（如果没有）
        for item in self.data:
            if "sample_io" not in item:
                item["sample_io"] = self._extract_sample_io(item)
    
    def _extract_sample_io(self, item: Dict[str, Any]) -> List[str]:
        """
        从测试代码中提取样例输入输出
        
        Args:
            item: 数据项
            
        Returns:
            样例输入输出列表
        """
        test_code = item.get("test", "")
        entry_point = item.get("entry_point", "")
        
        # 提取断言语句
        assertions = []
        for line in test_code.split("\n"):
            line = line.strip()
            if line.startswith("assert"):
                assertions.append(line)
        
        # 如果没有找到断言，返回空列表
        if not assertions:
            return []
        
        # 只保留前3个断言作为样例
        return assertions[:3]
    
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
        result = evaluate_functional_correctness(
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
        return evaluate_io(
            sample_io=item["sample_io"],
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
        if "prompt" in item:
            return f"{item['prompt'].strip()}"
        elif "text" in item:
            return f"{item['text'].strip()}"
        else:
            raise Exception("数据项中没有prompt或text字段") 