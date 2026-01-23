import os
import json
from typing import Dict, Any, List
from collections import Counter

from .jsonl import read_jsonl

def gen_summary(results_path: str, summary_path: str) -> None:
    """
    生成结果摘要
    
    Args:
        results_path: 结果文件路径
        summary_path: 摘要文件路径
    """
    if not os.path.exists(results_path):
        print(f"结果文件不存在: {results_path}")
        return
    
    # 读取结果
    results = read_jsonl(results_path)
    
    if not results:
        print(f"结果文件为空: {results_path}")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("结果文件为空，无法生成摘要。")
        return
    
    # 计算统计信息
    total = len(results)
    passed = sum(1 for result in results if result.get("passed", False))
    pass_rate = passed / total if total > 0 else 0
    
    # 计算时间统计（如果结果中包含时间信息）
    times = [result.get("total_time", 0) for result in results if "total_time" in result]
    total_time = sum(times) if times else 0
    avg_time = total_time / len(times) if times else 0
    
    # 生成摘要
    summary = [
        "# 结果摘要",
        "",
        f"总问题数: {total}",
        f"通过问题数: {passed}",
        f"通过率: {pass_rate:.2%}",
        f"总时间: {total_time:.2f}秒" if times else "总时间: N/A",
        f"平均时间: {avg_time:.2f}秒" if times else "平均时间: N/A",
        "",
        "## 详细统计",
        ""
    ]
    
    # 按问题ID分组
    problems_by_id = {}
    for result in results:
        problem_id = result.get("problem_id", "unknown")
        if problem_id not in problems_by_id:
            problems_by_id[problem_id] = []
        problems_by_id[problem_id].append(result)
    
    # 添加每个问题的详细信息
    for problem_id, problem_results in sorted(problems_by_id.items()):
        passed_count = sum(1 for r in problem_results if r.get("passed", False))
        summary.append(f"### 问题 {problem_id}")
        summary.append(f"- 尝试次数: {len(problem_results)}")
        summary.append(f"- 通过次数: {passed_count}")
        summary.append(f"- 通过率: {passed_count/len(problem_results):.2%}")
        
        if any("time" in r for r in problem_results):
            times = [r.get("time", 0) for r in problem_results if "time" in r]
            avg_time = sum(times) / len(times)
            summary.append(f"- 平均时间: {avg_time:.2f}秒")
        
        summary.append("")
    
    # 写入摘要文件
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary))
    
    print(f"摘要已生成: {summary_path}")

def analyze_failures(results_path: str) -> Dict[str, Any]:
    """
    分析失败案例
    
    Args:
        results_path: 结果文件路径
        
    Returns:
        失败分析结果
    """
    if not os.path.exists(results_path):
        return {"error": f"结果文件不存在: {results_path}"}
    
    # 读取结果
    results = read_jsonl(results_path)
    
    if not results:
        return {"error": f"结果文件为空: {results_path}"}
    
    # 筛选失败案例
    failures = [result for result in results if not result.get("passed", False)]
    
    if not failures:
        return {"message": "没有失败案例"}
    
    # 分析失败原因（如果有）
    failure_reasons = Counter()
    for failure in failures:
        reason = failure.get("failure_reason", "unknown")
        failure_reasons[reason] += 1
    
    # 分析测试阶段失败（如果有）
    test_failures = Counter()
    for failure in failures:
        test_log = failure.get("test_log", "")
        if "AssertionError" in test_log:
            test_failures["assertion_error"] += 1
        elif "SyntaxError" in test_log:
            test_failures["syntax_error"] += 1
        elif "TypeError" in test_log:
            test_failures["type_error"] += 1
        elif "IndexError" in test_log:
            test_failures["index_error"] += 1
        elif "KeyError" in test_log:
            test_failures["key_error"] += 1
        elif "ValueError" in test_log:
            test_failures["value_error"] += 1
        elif "NameError" in test_log:
            test_failures["name_error"] += 1
        else:
            test_failures["other_error"] += 1
    
    return {
        "total_failures": len(failures),
        "failure_reasons": {reason: count for reason, count in failure_reasons.most_common()},
        "test_failures": {error: count for error, count in test_failures.most_common()}
    } 