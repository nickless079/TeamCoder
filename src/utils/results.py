import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from .jsonl import append_jsonl, read_jsonl

class Results:
    """
    结果记录类，用于记录和管理代码生成结果
    """
    def __init__(
        self,
        results_path: str,
        auto_save: bool = True,
    ):
        """
        初始化结果记录器
        
        Args:
            results_path: 结果文件路径
            auto_save: 是否自动保存结果
        """
        self.results_path = results_path
        self.auto_save = auto_save
        self.results: List[Dict[str, Any]] = []
        
        # 确保结果目录存在
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        
        # 如果结果文件已存在，加载现有结果
        if os.path.exists(results_path):
            self.results = read_jsonl(results_path)
    
    def add_result(self, result: Dict[str, Any]) -> None:
        """
        添加单个结果
        
        Args:
            result: 结果数据
        """
        # 添加时间戳
        result["timestamp"] = datetime.now().isoformat()
        
        # 添加到结果列表
        self.results.append(result)
        
        # 如果启用自动保存，则保存到文件
        if self.auto_save:
            append_jsonl(self.results_path, result)
    
    def get_results(self) -> List[Dict[str, Any]]:
        """
        获取所有结果
        
        Returns:
            结果列表
        """
        return self.results
    
    def get_result_by_id(self, problem_id: str) -> Optional[Dict[str, Any]]:
        """
        通过问题ID获取结果
        
        Args:
            problem_id: 问题ID
            
        Returns:
            对应的结果，如果未找到则返回None
        """
        for result in self.results:
            if result.get("problem_id") == problem_id:
                return result
        return None
    
    def get_success_rate(self) -> float:
        """
        计算成功率
        
        Returns:
            成功率(0.0-1.0)
        """
        if not self.results:
            return 0.0
        
        success_count = sum(1 for result in self.results if result.get("passed", False))
        return success_count / len(self.results)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取结果摘要
        
        Returns:
            结果摘要
        """
        if not self.results:
            return {
                "total": 0,
                "success": 0,
                "success_rate": 0.0,
                "average_time": 0.0,
            }
        
        success_count = sum(1 for result in self.results if result.get("passed", False))
        
        # 计算平均时间（如果结果中包含时间信息）
        times = [result.get("time", 0) for result in self.results if "time" in result]
        avg_time = sum(times) / len(times) if times else 0.0
        
        return {
            "total": len(self.results),
            "success": success_count,
            "success_rate": success_count / len(self.results),
            "average_time": avg_time,
        }
    
    def save(self) -> None:
        """
        手动保存结果到文件
        """
        with open(self.results_path, 'w', encoding='utf-8') as f:
            for result in self.results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n') 