from typing import Dict, Any, List, Optional
import time
import json
import os
from datetime import datetime

from models.Base import BaseModel
from datasets.Dataset import Dataset
from utils.results import Results

class BaseWorkflow:
    """
    基础工作流类，所有具体工作流实现的父类
    """
    def __init__(
        self,
        model: BaseModel,
        dataset: Dataset,
        language: str,
        pass_at_k: int = 1,
        results: Optional[Results] = None,
        verbose: int = 1,
        web_search: bool = True,
        docker_execution: bool = True,
        start_index: int = 0,  # 添加start_index参数，默认从0开始
    ):
        """
        初始化基础工作流
        
        Args:
            model: 模型实例
            dataset: 数据集实例
            language: 编程语言
            pass_at_k: 评估时的pass@k值
            results: 结果记录器实例
            verbose: 输出详细程度
            web_search: 是否启用网络搜索
            docker_execution: 是否使用Docker执行验证
            start_index: 开始处理的数据集索引，默认为0
        """
        self.model = model
        self.dataset = dataset
        self.language = language
        self.pass_at_k = pass_at_k
        self.results = results
        self.verbose = verbose
        self.web_search = web_search
        self.docker_execution = docker_execution
        self.start_index = start_index  # 保存开始索引
        
        # 运行统计信息
        self.stats = {
            "total_problems": 0,
            "solved_problems": 0,
            "total_time": 0,
            "start_time": None,
            "end_time": None,
        }
        
    def run(self):
        """
        运行工作流
        """
        self.stats["start_time"] = datetime.now()
        
        total_problems = len(self.dataset)
        self.stats["total_problems"] = total_problems - self.start_index  # 调整总问题数
        
        for idx in range(self.start_index, total_problems):  # 从start_index开始
    

            item = self.dataset.get_item(idx)
            
            start_time = time.time()
            result = self.process_item(item)
            end_time = time.time()
            
            elapsed_time = end_time - start_time
            self.stats["total_time"] += elapsed_time
            
            if result["passed"]:
                self.stats["solved_problems"] += 1
                
            if self.results:
             
                self.results.add_result(result)
                
            print(f"问题 {idx+1}/{total_problems} - {'通过' if result['passed'] else '失败'} - 耗时: {elapsed_time:.2f}秒")
        
        # ✨ 新增：ET 扩展测试和 Plus 测试（仅针对 HumanEval 和 MBPP）
        if self.results:
            dataset_name = self.dataset.__class__.__name__.lower()
            if "humaneval" in dataset_name:
                self._run_et_evaluation_humaneval()
                self._run_plus_evaluation_humaneval()
            elif "mbpp" in dataset_name:
                self._run_et_evaluation_mbpp()
                
        
        self.stats["end_time"] = datetime.now()
        self.print_summary()
        
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个数据项
        
        Args:
            item: 数据项
            
        Returns:
            处理结果
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def _run_et_evaluation_humaneval(self):
        """运行 HumanEval ET 扩展测试"""
        from evaluations.evaluate_et import run_et_evaluation_humaneval
        
        results_path = self.results.results_path
        run_et_evaluation_humaneval(results_path, verbose=True)
    
    def _run_et_evaluation_mbpp(self):
        """运行 MBPP ET 扩展测试"""
        from evaluations.evaluate_et import run_et_evaluation_mbpp
        
        results_path = self.results.results_path
        run_et_evaluation_mbpp(results_path, verbose=True)
    
    def _run_plus_evaluation_humaneval(self):
        """运行 HumanEval+ 评估（使用 EvalPlus）"""
        from evaluations.evaluate_plus import run_plus_evaluation_humaneval
        
        results_path = self.results.results_path
        run_plus_evaluation_humaneval(results_path, verbose=True)
    
    def _run_plus_evaluation_mbpp(self):
        """运行 MBPP+ 评估（使用 EvalPlus）"""
        from evaluations.evaluate_plus import run_plus_evaluation_mbpp
        
        results_path = self.results.results_path
        run_plus_evaluation_mbpp(results_path, verbose=True)
    
    def print_summary(self):
        """
        打印运行摘要
        """
        total_time = self.stats["end_time"] - self.stats["start_time"]
        success_rate = self.stats["solved_problems"] / self.stats["total_problems"] * 100 if self.stats["total_problems"] > 0 else 0
        
        print("\n" + "=" * 50)
        print("运行摘要:")
        print(f"总问题数: {self.stats['total_problems']}")
        print(f"解决问题数: {self.stats['solved_problems']}")
        print(f"成功率: {success_rate:.2f}%")
        print(f"总运行时间: {total_time}")
        print(f"平均每题时间: {self.stats['total_time'] / self.stats['total_problems']:.2f}秒" if self.stats["total_problems"] > 0 else "N/A")
        print("=" * 50) 