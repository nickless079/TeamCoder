"""
ET (Extended Tests) 扩展测试评估模块

用于对 HumanEval 和 MBPP 数据集进行扩展测试用例的评估
"""

from typing import List, Dict, Any
import json
import os

from .func_evaluate import function_with_timeout, _create_safe_namespace


def evaluate_io_et(
    test_case_list: List[str],
    code: str,
    prompt: str = "",
    timeout: int = 5
) -> bool:
    """
    执行 ET 扩展测试
    
    Args:
        test_case_list: ET 测试用例列表
        code: 生成的代码
        prompt: 问题的 prompt（HumanEval 需要，MBPP 不需要）
        timeout: 超时时间（秒）
        
    Returns:
        是否通过所有测试
    """
    # 为每次测试创建独立的命名空间（包含内置函数）
    namespace = _create_safe_namespace()
    
    try:
        # 将所有测试用例拼接成一个字符串
        test_code = "\n".join(test_case_list)
        
        # 构建完整的测试代码
        full_code = ""
        if "from typing import *" not in code:
            full_code += "from typing import *\n"
        full_code += prompt + code + "\n" + test_code + "\n"
        
        # 执行测试（使用独立的命名空间）
        function_with_timeout(exec, args=(full_code, namespace), timeout=timeout)
        
        return True
    except Exception as e:
        # 其他错误：返回 False
        print('其他错误')
        return False


def run_et_evaluation_humaneval(
    results_path: str,
    et_dataset_path: str = "data/HumanEval/HumanEvalET.jsonl",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    运行 HumanEval ET 扩展测试
    
    Args:
        results_path: Results.jsonl 文件路径
        et_dataset_path: HumanEvalET.jsonl 数据集路径
        verbose: 是否显示详细信息
        
    Returns:
        测试统计信息字典
    """
    if verbose:
        print("\n" + "="*50)
        print("🔍 开始 HumanEval ET 扩展测试")
        print("="*50)
    
    # 1. 检查 ET 数据集是否存在
    if not os.path.exists(et_dataset_path):
        print(f"⚠️  ET 数据集不存在: {et_dataset_path}")
        return {"error": "ET dataset not found"}
    
    # 2. 读取 ET 数据集
    et_data = {}
    with open(et_dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            et_data[item['task_id']] = item
    
    if verbose:
        print(f"✓ 加载了 {len(et_data)} 个 ET 测试用例")
    
    # 3. 检查结果文件是否存在
    if not os.path.exists(results_path):
        print(f"⚠️  结果文件不存在: {results_path}")
        return {"error": "Results file not found"}
    
    # 4. 对每个结果进行 ET 测试
    correct_count = 0
    total_count = 0
    et_results = []
    
    with open(results_path, 'r', encoding='utf-8') as f:
        for line in f:
            result = json.loads(line.strip())
            task_id = result.get('problem_id', '')
            code = result.get('code', '')
            
            # 获取 ET 测试用例
            if task_id in et_data:
                et_item = et_data[task_id]
                test_case_list = et_item.get('test_case_list', [])
                prompt = et_item.get('prompt', '')
                
                if not test_case_list:
                    if verbose:
                        print(f"⚠️  {task_id} 没有 ET 测试用例")
                    continue
                
                # 使用 evaluate_io_et 测试
                passed = evaluate_io_et(test_case_list, code, prompt)
                
                # 更新结果
                result['et_passed'] = passed
                result['et_test_count'] = len(test_case_list)
                et_results.append(result)
                
                if passed:
                    correct_count += 1
                total_count += 1
                
                if verbose:
                    status = "✓ 通过" if passed else "✗ 失败"
                    print(f"  {task_id}: {status} ({len(test_case_list)} 个测试)")
    
    # 5. 保存 ET 结果
    et_results_path = results_path.replace('.jsonl', '_ET.jsonl')
    
    # 按 task_id 排序
    et_results_sorted = sorted(
        et_results,
        key=lambda x: int(x['problem_id'].split('/')[-1])
    )
    
    with open(et_results_path, 'w', encoding='utf-8') as f:
        for result in et_results_sorted:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
    
    # 6. 计算统计信息
    success_rate = (correct_count / total_count * 100) if total_count > 0 else 0
    
    if verbose:
        print(f"\n{'='*50}")
        print(f"✅ ET 测试完成!")
        print(f"   通过: {correct_count}/{total_count} ({success_rate:.2f}%)")
        print(f"   结果已保存到: {et_results_path}")
        print(f"{'='*50}\n")
    
    return {
        "correct_count": correct_count,
        "total_count": total_count,
        "success_rate": success_rate,
        "et_results_path": et_results_path
    }


def run_et_evaluation_mbpp(
    results_path: str,
    et_dataset_path: str = "data/MBPPEval/MBPP_ET.jsonl",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    运行 MBPP ET 扩展测试
    
    Args:
        results_path: Results.jsonl 文件路径
        et_dataset_path: MBPP_ET.jsonl 数据集路径
        verbose: 是否显示详细信息
        
    Returns:
        测试统计信息字典
    """
    if verbose:
        print("\n" + "="*50)
        print("🔍 开始 MBPP ET 扩展测试")
        print("="*50)
    
    # 1. 检查 ET 数据集是否存在
    if not os.path.exists(et_dataset_path):
        print(f"⚠️  ET 数据集不存在: {et_dataset_path}")
        return {"error": "ET dataset not found"}
    
    # 2. 读取 ET 数据集
    et_data = {}
    with open(et_dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            et_data[item['task_id']] = item
    
    if verbose:
        print(f"✓ 加载了 {len(et_data)} 个 ET 测试用例")
    
    # 3. 检查结果文件是否存在
    if not os.path.exists(results_path):
        print(f"⚠️  结果文件不存在: {results_path}")
        return {"error": "Results file not found"}
    
    # 4. 对每个结果进行 ET 测试
    correct_count = 0
    total_count = 0
    et_results = []
    
    with open(results_path, 'r', encoding='utf-8') as f:
        for line in f:
            result = json.loads(line.strip())
            # MBPP 的 problem_id 可能是数字格式
            problem_id = result.get('problem_id', '')
            
            # 尝试将 problem_id 转换为整数（MBPP 使用整数 task_id）
            try:
                if isinstance(problem_id, str) and '/' in problem_id:
                    task_id = int(problem_id.split('/')[-1])
                else:
                    task_id = int(problem_id)
            except (ValueError, TypeError):
                task_id = problem_id
            
            code = result.get('code', '')
            
            # 获取 ET 测试用例
            if task_id in et_data:
                et_item = et_data[task_id]
                test_list = et_item.get('test_list', [])
                
                if not test_list:
                    if verbose:
                        print(f"⚠️  task_id {task_id} 没有 ET 测试用例")
                    continue
                
                # MBPP 不需要 prompt，直接测试
                passed = evaluate_io_et(test_list, code, prompt="")
                
                # 更新结果
                result['et_passed'] = passed
                result['et_test_count'] = len(test_list)
                et_results.append(result)
                
                if passed:
                    correct_count += 1
                total_count += 1
                
                if verbose:
                    status = "✓ 通过" if passed else "✗ 失败"
                    print(f"  task_id {task_id}: {status} ({len(test_list)} 个测试)")
    
    # 5. 保存 ET 结果
    et_results_path = results_path.replace('.jsonl', '_ET.jsonl')
    
    # 按 task_id 排序
    et_results_sorted = sorted(
        et_results,
        key=lambda x: int(str(x['problem_id']).split('/')[-1]) if '/' in str(x['problem_id']) else int(x['problem_id'])
    )
    
    with open(et_results_path, 'w', encoding='utf-8') as f:
        for result in et_results_sorted:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
    
    # 6. 计算统计信息
    success_rate = (correct_count / total_count * 100) if total_count > 0 else 0
    
    if verbose:
        print(f"\n{'='*50}")
        print(f"✅ ET 测试完成!")
        print(f"   通过: {correct_count}/{total_count} ({success_rate:.2f}%)")
        print(f"   结果已保存到: {et_results_path}")
        print(f"{'='*50}\n")
    
    return {
        "correct_count": correct_count,
        "total_count": total_count,
        "success_rate": success_rate,
        "et_results_path": et_results_path
    }

