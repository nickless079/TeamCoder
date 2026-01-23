#!/usr/bin/env python3
"""
筛选 MBPP 和 MBPP_ET 数据集，只保留 MBPPPLUS 中存在的 task_id
生成 MBPP_EN.jsonl 和 MBPPET_EN.jsonl
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
    mbppplus_file = base_dir / "mbpp-py.jsonl"
    mbpp_file = base_dir / "MBPP.jsonl"
    mbpp_et_file = base_dir / "MBPP_ET.jsonl"
    
    mbpp_en_file = base_dir / "MBPP_EN.jsonl"
    mbppet_en_file = base_dir / "MBPPET_EN.jsonl"
    
    print("=" * 60)
    print("MBPP 数据集筛选工具")
    print("=" * 60)
    
    # 1. 加载 MBPPPLUS 的 task_id 作为基准
    print(f"\n📖 读取 MBPPPLUS 的 task_id...")
    plus_task_ids = load_task_ids(mbppplus_file)
    print(f"   ✓ MBPPPLUS 包含 {len(plus_task_ids)} 个题目")
    print(f"   ✓ task_id 范围: {min(plus_task_ids)} - {max(plus_task_ids)}")
    
    # 2. 筛选 MBPP.jsonl
    print(f"\n🔍 筛选 MBPP.jsonl...")
    filtered_mbpp, total_mbpp = filter_by_task_ids(
        mbpp_file, 
        mbpp_en_file, 
        plus_task_ids
    )
    print(f"   ✓ 原始题目数: {total_mbpp}")
    print(f"   ✓ 筛选后题目数: {filtered_mbpp}")
    print(f"   ✓ 输出文件: {mbpp_en_file.name}")
    
    # 3. 筛选 MBPP_ET.jsonl
    print(f"\n🔍 筛选 MBPP_ET.jsonl...")
    filtered_et, total_et = filter_by_task_ids(
        mbpp_et_file, 
        mbppet_en_file, 
        plus_task_ids
    )
    print(f"   ✓ 原始题目数: {total_et}")
    print(f"   ✓ 筛选后题目数: {filtered_et}")
    print(f"   ✓ 输出文件: {mbppet_en_file.name}")
    
    # 4. 验证结果
    print(f"\n✅ 筛选完成！")
    print(f"\n📊 统计信息:")
    print(f"   - MBPPPLUS:   {len(plus_task_ids)} 题")
    print(f"   - MBPP_EN:    {filtered_mbpp} 题")
    print(f"   - MBPPET_EN:  {filtered_et} 题")
    
    if filtered_mbpp == len(plus_task_ids) and filtered_et == len(plus_task_ids):
        print(f"\n✓ 验证通过：所有文件题目数量一致！")
    else:
        print(f"\n⚠️  警告：题目数量不一致，可能存在缺失的 task_id")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

