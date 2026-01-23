from typing import List, Dict, Any, Callable, Union, Tuple
import numpy as np
import math
import json
import os
import time
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

from .func_evaluate import evaluate_functional_correctness, evaluate_io, evaluate_mbpp_functional_correctness, evaluate_mbpp_sample_io


def estimate_pass_at_k(
    n_samples: int,
    n_correct: int,
    k: int
) -> float:
    """
    估计pass@k指标
    
    Args:
        n_samples: 样本数量
        n_correct: 正确样本数量
        k: k值
        
    Returns:
        pass@k估计值
    """
    if n_samples == 0:
        return 0.0
    if n_correct == 0:
        return 0.0
    if n_correct > n_samples:
        return 1.0

    # 计算pass@k
    # 公式: 1 - 组合数(n_samples - n_correct, k) / 组合数(n_samples, k)
    # 参考: https://arxiv.org/pdf/2107.03374.pdf
    
    # 使用对数计算组合数，避免溢出
    def log_combinations(n, k):
        return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    
    log_numerator = log_combinations(n_samples - n_correct, k)
    log_denominator = log_combinations(n_samples, k)
    
    return 1.0 - math.exp(log_numerator - log_denominator)


def evaluate_humaneval_problem(
    problem: Dict[str, Any],
    solutions: List[str],
    timeout: int = 5,
) -> Dict[str, Any]:
    """
    评估HumanEval问题的多个解决方案
    
    Args:
        problem: HumanEval问题
        solutions: 解决方案列表
        timeout: 超时时间(秒)
        
    Returns:
        评估结果
    """
    task_id = problem.get("task_id", "")
    entry_point = problem.get("entry_point", "")
    test = problem.get("test", "")
    
    if not test or not entry_point:
        return {
            "task_id": task_id,
            "correct": [],
            "total": len(solutions),
            "pass_rate": 0.0,
            "error": "缺少测试代码或入口点"
        }
    
    # 评估每个解决方案
    correct_indices = []
    errors = []
    
    for i, solution in enumerate(solutions):
        try:
            result = evaluate_functional_correctness(
                test=test,
                entry_point=entry_point,
                completion=solution,
                timeout=timeout
            )
            
            if result == "passed":
                correct_indices.append(i)
            else:
                errors.append((i, result))
        except Exception as e:
            errors.append((i, str(e)))
    
    return {
        "task_id": task_id,
        "correct": correct_indices,
        "total": len(solutions),
        "pass_rate": len(correct_indices) / len(solutions) if solutions else 0.0,
        "errors": errors
    }


def evaluate_mbpp_problem(
    problem: Dict[str, Any],
    solutions: List[str],
    timeout: int = 5,
) -> Dict[str, Any]:
    """
    评估MBPP问题的多个解决方案
    
    Args:
        problem: MBPP问题
        solutions: 解决方案列表
        timeout: 超时时间(秒)
        
    Returns:
        评估结果
    """
    task_id = problem.get("task_id", "")
    test = problem.get("test", "")
    entry_point = problem.get("entry_point", "")
    
    if not test or not entry_point:
        return {
            "task_id": task_id,
            "correct": [],
            "total": len(solutions),
            "pass_rate": 0.0,
            "error": "缺少测试代码或入口点"
        }
    
    # 评估每个解决方案
    correct_indices = []
    errors = []
    
    for i, solution in enumerate(solutions):
        try:
            result = evaluate_mbpp_functional_correctness(
                test=test,
                entry_point=entry_point,
                completion=solution,
                timeout=timeout
            )
            
            if result == "passed":
                correct_indices.append(i)
            else:
                errors.append((i, result))
        except Exception as e:
            errors.append((i, str(e)))
    
    return {
        "task_id": task_id,
        "correct": correct_indices,
        "total": len(solutions),
        "pass_rate": len(correct_indices) / len(solutions) if solutions else 0.0,
        "errors": errors
    }


def evaluate_apps_problem(
    problem: Dict[str, Any],
    solutions: List[str],
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    评估APPS问题的多个解决方案
    
    Args:
        problem: APPS问题
        solutions: 解决方案列表
        timeout: 超时时间(秒)
        
    Returns:
        评估结果
    """
    task_id = problem.get("task_id", "")
    test_cases = problem.get("test_cases", [])
    
    if not test_cases:
        return {
            "task_id": task_id,
            "correct": [],
            "total": len(solutions),
            "pass_rate": 0.0,
            "error": "缺少测试用例"
        }
    
    # 评估每个解决方案
    correct_indices = []
    errors = []
    
    for i, solution in enumerate(solutions):
        try:
            passed, log = evaluate_io(
                sample_io=test_cases,
                completion=solution,
                timeout=timeout,
                stop_early=True
            )
            
            if passed:
                correct_indices.append(i)
            else:
                errors.append((i, log))
        except Exception as e:
            errors.append((i, str(e)))
    
    return {
        "task_id": task_id,
        "correct": correct_indices,
        "total": len(solutions),
        "pass_rate": len(correct_indices) / len(solutions) if solutions else 0.0,
        "errors": errors
    }


def evaluate_xcode_problem(
    problem: Dict[str, Any],
    solutions: List[str],
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    评估XCode问题的多个解决方案
    
    Args:
        problem: XCode问题
        solutions: 解决方案列表
        timeout: 超时时间(秒)
        
    Returns:
        评估结果
    """
    task_id = problem.get("task_id", "")
    test_cases = problem.get("test_cases", [])
    
    if not test_cases:
        return {
            "task_id": task_id,
            "correct": [],
            "total": len(solutions),
            "pass_rate": 0.0,
            "error": "缺少测试用例"
        }
    
    # 评估每个解决方案
    correct_indices = []
    errors = []
    
    for i, solution in enumerate(solutions):
        try:
            passed, log = evaluate_io(
                sample_io=test_cases,
                completion=solution,
                timeout=timeout,
                stop_early=True
            )
            
            if passed:
                correct_indices.append(i)
            else:
                errors.append((i, log))
        except Exception as e:
            errors.append((i, str(e)))
    
    return {
        "task_id": task_id,
        "correct": correct_indices,
        "total": len(solutions),
        "pass_rate": len(correct_indices) / len(solutions) if solutions else 0.0,
        "errors": errors
    }


def calculate_pass_at_k(
    results: List[Dict[str, Any]],
    k_values: List[int] = [1, 10, 100]
) -> Dict[int, float]:
    """
    计算pass@k指标
    
    Args:
        results: 评估结果列表
        k_values: k值列表
        
    Returns:
        不同k值对应的pass@k指标
    """
    # 过滤掉没有解决方案的问题
    valid_results = [r for r in results if r["total"] > 0]
    
    if not valid_results:
        return {k: 0.0 for k in k_values}
    
    # 计算每个k值的pass@k
    pass_at_k = {}
    for k in k_values:
        # 对于每个问题，计算pass@k
        problem_pass_at_k = []
        for result in valid_results:
            n_samples = min(result["total"], k)
            n_correct = len(result["correct"])
            problem_pass_at_k.append(estimate_pass_at_k(n_samples, n_correct, k))
        
        # 计算平均pass@k
        pass_at_k[k] = sum(problem_pass_at_k) / len(problem_pass_at_k)
    
    return pass_at_k


def evaluate_solutions(
    problems: List[Dict[str, Any]],
    solutions: List[List[str]],
    dataset_type: str = "humaneval",
    timeout: int = 5,
    k_values: List[int] = [1, 10, 100],
    max_workers: int = 4,
    output_file: str = None
) -> Dict[str, Any]:
    """
    评估多个问题的多个解决方案
    
    Args:
        problems: 问题列表
        solutions: 每个问题的解决方案列表
        dataset_type: 数据集类型，可选值: humaneval, mbpp, apps
        timeout: 超时时间(秒)
        k_values: k值列表
        max_workers: 最大并行工作进程数
        output_file: 输出文件路径
        
    Returns:
        评估结果
    """
    if len(problems) != len(solutions):
        raise ValueError("问题数量和解决方案列表数量不匹配")
    
    # 选择评估函数
    if dataset_type.lower() == "humaneval":
        evaluate_fn = evaluate_humaneval_problem
    elif dataset_type.lower() == "mbpp":
        evaluate_fn = evaluate_mbpp_problem
    elif dataset_type.lower() == "apps":
        evaluate_fn = evaluate_apps_problem
    else:
        raise ValueError(f"不支持的数据集类型: {dataset_type}")
    
    # 并行评估所有问题
    results = []
    start_time = time.time()
    
    with tqdm(total=len(problems), desc=f"评估{dataset_type}") as pbar:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for problem, problem_solutions in zip(problems, solutions):
                future = executor.submit(
                    evaluate_fn,
                    problem,
                    problem_solutions,
                    timeout
                )
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                pbar.update(1)
    
    # 计算pass@k
    pass_at_k_results = calculate_pass_at_k(results, k_values)
    
    # 计算总体通过率
    total_correct = sum(len(r["correct"]) for r in results)
    total_solutions = sum(r["total"] for r in results)
    overall_pass_rate = total_correct / total_solutions if total_solutions > 0 else 0.0
    
    # 构建最终结果
    final_results = {
        "dataset": dataset_type,
        "num_problems": len(problems),
        "num_solutions": total_solutions,
        "num_correct": total_correct,
        "overall_pass_rate": overall_pass_rate,
        "pass_at_k": pass_at_k_results,
        "evaluation_time": time.time() - start_time,
        "problem_results": results
    }
    
    # 保存结果到文件
    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
    
    return final_results 