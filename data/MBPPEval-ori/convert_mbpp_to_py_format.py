#!/usr/bin/env python3
"""
将 MBPP_EN.jsonl 转换为 mbpp-py.jsonl 格式

MBPP_EN 格式:
{
    "text": "问题描述",
    "code": "参考代码",
    "task_id": 2,
    "test_setup_code": "",
    "test_list": ["assert ...", ...],
    "challenge_test_list": []
}

mbpp-py 格式:
{
    "name": "mbpp_2_similar_elements",
    "language": "py",
    "prompt": "def similar_elements(...):\n    \"\"\"问题描述\"\"\"",
    "entry_point": "similar_elements",
    "test": "def check(candidate):\n    assert ...\n\ndef test_check():\n    check(entry_point)\n\ntest_check()\n",
    "sample_io": ["assert ..."]
}
"""

import json
import re
from pathlib import Path


def extract_function_name(code: str) -> str:
    """从代码中提取函数名"""
    # 匹配 def function_name(
    match = re.search(r'def\s+(\w+)\s*\(', code)
    if match:
        return match.group(1)
    return "unknown_function"


def extract_function_signature(code: str) -> str:
    """从代码中提取函数签名（包括参数和类型注解）"""
    # 匹配整个函数定义行
    match = re.search(r'def\s+\w+\s*\([^)]*\)(?:\s*->\s*[^:]+)?:', code)
    if match:
        return match.group(0).rstrip(':')
    
    # 如果没有找到，尝试简单匹配
    match = re.search(r'def\s+\w+\s*\([^)]*\)', code)
    if match:
        return match.group(0)
    
    return "def unknown_function()"


def create_test_code(entry_point: str, test_list: list) -> str:
    """创建测试代码"""
    test_assertions = []
    for test in test_list:
        # 将 assert function_name(...) 替换为 assert candidate(...)
        test_assertion = test.replace(f"assert {entry_point}(", "assert candidate(")
        test_assertions.append(f"    {test_assertion}")
    
    test_code = f"""def check(candidate):
{chr(10).join(test_assertions)}

def test_check():
    check({entry_point})

test_check()
"""
    return test_code


def create_prompt(text: str, function_signature: str) -> str:
    """创建 prompt（函数签名 + docstring）"""
    # 提取函数签名
    prompt = f"{function_signature}:\n"
    prompt += f'    """\n'
    prompt += f'    {text}\n'
    prompt += f'    """\n'
    return prompt


def convert_mbpp_to_py_format(input_file: str, output_file: str):
    """转换 MBPP_EN.jsonl 到 mbpp-py.jsonl 格式"""
    
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        print(f"❌ 输入文件不存在: {input_file}")
        return
    
    converted_count = 0
    skipped_count = 0
    
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        for line_num, line in enumerate(f_in, 1):
            try:
                item = json.loads(line.strip())
                
                # 提取必要字段
                task_id = item.get('task_id')
                text = item.get('text', '')
                code = item.get('code', '')
                test_list = item.get('test_list', [])
                
                if not code or not test_list:
                    print(f"⚠️  跳过第 {line_num} 行: 缺少 code 或 test_list")
                    skipped_count += 1
                    continue
                
                # 提取函数名和签名
                entry_point = extract_function_name(code)
                function_signature = extract_function_signature(code)
                
                # 创建 name
                name = f"mbpp_{task_id}_{entry_point}"
                
                # 创建 prompt
                prompt = create_prompt(text, function_signature)
                
                # 创建测试代码
                test_code = create_test_code(entry_point, test_list)
                
                # 创建 sample_io（取第一个测试用例）
                sample_io = [test_list[0]] if test_list else []
                
                # 构建新的数据项
                new_item = {
                    "task_id": task_id,
                    "name": name,
                    "language": "py",
                    "prompt": prompt,
                    "doctests": "transform",
                    "original": f"mbpp_{task_id}",
                    "prompt_terminology": "reworded",
                    "stop_tokens": [
                        "\ndef",
                        "\n#",
                        "\nif",
                        "\nclass"
                    ],
                    "entry_point": entry_point,
                    "test": test_code,
                    "sample_io": sample_io
                }
                
                # 写入输出文件
                f_out.write(json.dumps(new_item, ensure_ascii=False) + '\n')
                converted_count += 1
                
                if converted_count % 50 == 0:
                    print(f"✓ 已转换 {converted_count} 个问题...")
                
            except json.JSONDecodeError as e:
                print(f"❌ 第 {line_num} 行 JSON 解析错误: {e}")
                skipped_count += 1
            except Exception as e:
                print(f"❌ 第 {line_num} 行处理错误: {e}")
                skipped_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ 转换完成!")
    print(f"   成功转换: {converted_count} 个")
    print(f"   跳过: {skipped_count} 个")
    print(f"   输出文件: {output_file}")
    print(f"{'='*50}")


def main():
    """主函数"""
    import sys
    
    # 默认路径
    base_dir = Path(__file__).parent
    input_file = base_dir / "MBPP_EN.jsonl"
    output_file = base_dir / "mbpp-py-converted.jsonl"
    
    # 如果提供了命令行参数
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print(f"{'='*50}\n")
    
    convert_mbpp_to_py_format(str(input_file), str(output_file))


if __name__ == "__main__":
    main()

