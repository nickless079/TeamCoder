from typing import List, Dict, Any, Union, Tuple
import json
import os
from utils.jsonl import read_jsonl

class Dataset:
    """
    基础数据集类，所有具体数据集实现的父类
    """
    def __init__(
        self,
        path: str,
    ):
        """
        初始化数据集
        
        Args:
            path: 数据集文件路径
        """
        self.path = path
        self.data = self._load_data()
        self.id_key = "id"  # 默认ID字段名，子类可覆盖
        
    def _load_data(self) -> List[Dict[str, Any]]:
        """
        加载数据集文件
        
        Returns:
            数据列表
        """
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"数据集文件不存在: {self.path}")
        
        return read_jsonl(self.path)
    
    def get_item(self, idx: int) -> Dict[str, Any]:
        """
        获取指定索引的数据项
        
        Args:
            idx: 数据索引
            
        Returns:
            数据项
        """
        if idx < 0 or idx >= len(self.data):
            raise IndexError(f"索引{idx}超出范围[0, {len(self.data) - 1}]")
        
        return self.data[idx]
    
    def get_item_by_id(self, id_value: str) -> Dict[str, Any]:
        """
        通过ID获取数据项
        
        Args:
            id_value: ID值
            
        Returns:
            数据项
            
        Raises:
            ValueError: 如果未找到匹配的数据项
        """
        for item in self.data:
            if item[self.id_key] == id_value:
                return item
        
        raise ValueError(f"未找到ID为{id_value}的数据项")
    
    def __len__(self) -> int:
        """
        获取数据集长度
        
        Returns:
            数据集中的项目数
        """
        return len(self.data)
    
    def get_prompt(self, item: Dict[str, Any]) -> str:
        """
        从数据项中提取问题描述
        
        Args:
            item: 数据项
            
        Returns:
            问题描述文本
        """
        raise NotImplementedError("子类必须实现此方法")
    
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
        raise NotImplementedError("子类必须实现此方法")
    
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
        raise NotImplementedError("子类必须实现此方法")
    
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
        raise NotImplementedError("子类必须实现此方法") 