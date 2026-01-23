#!/usr/bin/env python3
"""
筛选 HumanEval 和 HumanEvalET 数据集，只保留 humanevalplus 中存在的 task_id
生成 HumanEval_EN.jsonl 和 HumanEvalET_EN.jsonl
"""

import json
from pathlib import Path


def load_task_ids(file_path: str) -> set:
    """加载文件中的所有 task_id"""
    task_ids = set()
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                task_ids.add(data['task_id'])
    return task_ids


def filter_by_task_ids(input_file: str, output_file: str, target_task_ids: set):
    """根据 task_id 集合筛选数据"""
    filtered_count = 0
    total_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        for line in fin:
            total_count += 1
            if line.strip():
                data = json.loads(line)
                if data['task_id'] in target_task_ids:
                    fout.write(line)
                    filtered_count += 1
    
    return filtered_count, total_count


def main():
    # 获取当前脚本所在目录
    base_dir = Path(__file__).parent
    
    # 文件路径
    plus_file = base_dir / "humanevalplus.jsonl"
    humaneval_file = base_dir / "HumanEval.jsonl"
    humaneval_et_file = base_dir / "HumanEvalET.jsonl"
    
    humaneval_en_file = base_dir / "HumanEval_EN.jsonl"
    humanevalet_en_file = base_dir / "HumanEvalET_EN.jsonl"
    
    print("=" * 60)
    print("HumanEval 数据集筛选工具")
    print("=" * 60)
    
    # 1. 加载 humanevalplus 的 task_id 作为基准
    print(f"\n📖 读取 humanevalplus 的 task_id...")
    plus_task_ids = load_task_ids(plus_file)
    print(f"   ✓ humanevalplus 包含 {len(plus_task_ids)} 个题目")
    
    # 2. 筛选 HumanEval.jsonl
    print(f"\n🔍 筛选 HumanEval.jsonl...")
    filtered_humaneval, total_humaneval = filter_by_task_ids(
        humaneval_file, 
        humaneval_en_file, 
        plus_task_ids
    )
    print(f"   ✓ 原始题目数: {total_humaneval}")
    print(f"   ✓ 筛选后题目数: {filtered_humaneval}")
    print(f"   ✓ 输出文件: {humaneval_en_file.name}")
    
    # 3. 筛选 HumanEvalET.jsonl
    print(f"\n🔍 筛选 HumanEvalET.jsonl...")
    filtered_et, total_et = filter_by_task_ids(
        humaneval_et_file, 
        humanevalet_en_file, 
        plus_task_ids
    )
    print(f"   ✓ 原始题目数: {total_et}")
    print(f"   ✓ 筛选后题目数: {filtered_et}")
    print(f"   ✓ 输出文件: {humanevalet_en_file.name}")
    
    # 4. 验证结果
    print(f"\n✅ 筛选完成！")
    print(f"\n📊 统计信息:")
    print(f"   - humanevalplus:   {len(plus_task_ids)} 题")
    print(f"   - HumanEval_EN:    {filtered_humaneval} 题")
    print(f"   - HumanEvalET_EN:  {filtered_et} 题")
    
    if filtered_humaneval == len(plus_task_ids) and filtered_et == len(plus_task_ids):
        print(f"\n✓ 验证通过：所有文件题目数量一致！")
    else:
        print(f"\n⚠️  警告：题目数量不一致，可能存在缺失的 task_id")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

