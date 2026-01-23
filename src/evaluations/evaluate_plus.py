"""
EvalPlus 评估模块

使用 EvalPlus 官方评估器对 HumanEval+ 和 MBPP+ 进行评估
EvalPlus GitHub: https://github.com/evalplus/evalplus
"""

import os
import json
import subprocess
from typing import Dict, Any, Optional


def prepare_evalplus_format(
    results_path: str,
    output_path: str,
    dataset_type: str = "humaneval"
) -> bool:
    """
    将 TeamCoder 的 Results.jsonl 转换为 EvalPlus 格式
    
    EvalPlus 格式:
    {
        "task_id": "HumanEval/0",
        "solution": "def has_close_elements(...):\n    ..."
    }
    
    Args:
        results_path: TeamCoder Results.jsonl 文件路径
        output_path: 输出的 EvalPlus 格式文件路径
        dataset_type: 数据集类型 ("humaneval" 或 "mbpp")
        
    Returns:
        是否成功转换
    """
    if not os.path.exists(results_path):
        print(f"❌ 文件不存在: {results_path}")
        return False
    
    try:
        evalplus_results = []
        
        with open(results_path, 'r', encoding='utf-8') as f:
            for line in f:
                result = json.loads(line.strip())
                
                # 提取必要字段
                if dataset_type.lower() == "humaneval":
                    task_id = result.get('problem_id', '')
                elif dataset_type.lower() == "mbpp":
                    # MBPP 的 task_id 格式可能需要转换
                    problem_id = result.get('problem_id', '')
                    if isinstance(problem_id, int):
                        task_id = f"Mbpp/{problem_id}"
                    else:
                        task_id = problem_id
                else:
                    task_id = result.get('problem_id', '')
                
                code = result.get('code', '')
                
                # 构建 EvalPlus 格式
                evalplus_item = {
                    "task_id": task_id,
                    "solution": code
                }
                
                evalplus_results.append(evalplus_item)
        
        # 写入 EvalPlus 格式文件
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in evalplus_results:
                f.write(json.dumps(item) + '\n')
        
        print(f"✓ 已转换 {len(evalplus_results)} 个结果到 EvalPlus 格式")
        print(f"  输出文件: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False


def run_evalplus_evaluation(
    evalplus_samples_path: str,
    dataset: str = "humaneval",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    使用 EvalPlus 官方评估器进行评估
    
    Args:
        evalplus_samples_path: EvalPlus 格式的样本文件路径
        dataset: 数据集名称 ("humaneval" 或 "mbpp")
        dataset_path: 本地数据集路径（可选，如果不提供则自动下载）
        verbose: 是否显示详细信息
        
    Returns:
        评估结果字典
    """
    if verbose:
        print("\n" + "="*50)
        print(f"🔍 开始 {dataset.upper()}+ 评估 (使用 EvalPlus)")
        print("="*50)
    
    if not os.path.exists(evalplus_samples_path):
        print(f"❌ 样本文件不存在: {evalplus_samples_path}")
        return {"error": "Sample file not found"}
    
    try:
        # 构建 evalplus 命令
        # evalplus.evaluate --dataset humaneval --samples samples.jsonl
        cmd = [
            "evalplus.evaluate",
            "--dataset", dataset.lower(),
            "--samples", evalplus_samples_path
        ]
        
        if verbose:
            print(f"📝 执行命令: {' '.join(cmd)}")
        
        # 执行评估
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1小时超时
        )
        
        if result.returncode == 0:
            if verbose:
                print("\n" + "="*50)
                print("✅ EvalPlus 评估完成")
                print("="*50)
                print("\n评估结果:")
                print(result.stdout)
            
            # 解析输出结果
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        else:
            print(f"❌ EvalPlus 评估失败")
            print(f"错误信息: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        print("❌ 评估超时（超过1小时）")
        return {"error": "Timeout"}
    except FileNotFoundError:
        print("❌ 未找到 evalplus 命令")
        print("   请先安装 EvalPlus: pip install evalplus")
        return {"error": "EvalPlus not installed"}
    except Exception as e:
        print(f"❌ 评估过程出错: {e}")
        return {"error": str(e)}


def run_plus_evaluation_humaneval(
    results_path: str,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    运行 HumanEval+ 评估的完整流程
    
    Args:
        results_path: TeamCoder Results.jsonl 文件路径
        verbose: 是否显示详细信息
        
    Returns:
        评估统计信息
    """
    if verbose:
        print("\n" + "="*60)
        print("🚀 HumanEval+ 评估流程")
        print("="*60)
    
    # 1. 准备 EvalPlus 格式文件
    evalplus_path = results_path.replace('.jsonl', '_evalplus.jsonl')
    
    if verbose:
        print("\n步骤 1: 转换为 EvalPlus 格式")
    
    if not prepare_evalplus_format(results_path, evalplus_path, "humaneval"):
        return {"error": "Format conversion failed"}
    
    # 2. 运行 EvalPlus 评估
    if verbose:
        print("\n步骤 2: 运行 EvalPlus 评估器")
    
    # 使用本地数据集路径
    dataset_path = "data/HumanEval/HumanEvalPlus.jsonl"
    
    eval_result = run_evalplus_evaluation(evalplus_path, "humaneval", verbose)
    
    # 3. 保存结果
    if eval_result.get("success"):
        summary_path = results_path.replace('.jsonl', '_Plus_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(eval_result.get("stdout", ""))
        
        if verbose:
            print(f"\n✓ 评估结果已保存到: {summary_path}")
        
        eval_result["summary_path"] = summary_path
    
    return eval_result


def run_plus_evaluation_mbpp(
    results_path: str,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    运行 MBPP+ 评估的完整流程
    
    Args:
        results_path: TeamCoder Results.jsonl 文件路径
        verbose: 是否显示详细信息
        
    Returns:
        评估统计信息
    """
    if verbose:
        print("\n" + "="*60)
        print("🚀 MBPP+ 评估流程")
        print("="*60)
    
    # 1. 准备 EvalPlus 格式文件
    evalplus_path = results_path.replace('.jsonl', '_evalplus.jsonl')
    
    if verbose:
        print("\n步骤 1: 转换为 EvalPlus 格式")
    
    if not prepare_evalplus_format(results_path, evalplus_path, "mbpp"):
        return {"error": "Format conversion failed"}
    
    # 2. 运行 EvalPlus 评估
    if verbose:
        print("\n步骤 2: 运行 EvalPlus 评估器")
    

    
    eval_result = run_evalplus_evaluation(evalplus_path, "mbpp", verbose)
    
    # 3. 保存结果
    if eval_result.get("success"):
        summary_path = results_path.replace('.jsonl', '_Plus_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(eval_result.get("stdout", ""))
        
        if verbose:
            print(f"\n✓ 评估结果已保存到: {summary_path}")
        
        eval_result["summary_path"] = summary_path
    
    return eval_result


def check_evalplus_installed() -> bool:
    """
    检查 EvalPlus 是否已安装
    
    Returns:
        是否已安装
    """
    try:
        # 尝试导入 evalplus 模块
        import importlib.util
        spec = importlib.util.find_spec("evalplus")
        return spec is not None
    except (ImportError, ValueError, AttributeError):
        return False


if __name__ == "__main__":
    # 测试 EvalPlus 是否安装
    print("检查 EvalPlus 安装状态...")
    if check_evalplus_installed():
        print("✅ EvalPlus 已安装")
    else:
        print("❌ EvalPlus 未安装")
        print("   安装命令: pip install evalplus")

