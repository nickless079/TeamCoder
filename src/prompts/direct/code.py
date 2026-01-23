"""
Direct 策略的 code prompt 模块
直接让模型生成代码，不使用 few-shot examples
"""

from typing import List, Dict


def get_messages(
    problem_description: str,
    language: str = "Python3",
    dataset_type: str = "HumanEval"
) -> List[Dict[str, str]]:
    """
    获取 Direct 提示词消息列表
    
    Args:
        problem_description: 问题描述
        language: 编程语言
        dataset_type: 数据集类型（Direct 策略不需要，保持接口一致）
        
    Returns:
        消息列表 [{"role": "user", "content": "..."}]
    """
    # Direct 策略：直接要求生成代码，不提供示例
    prompt = f"""{problem_description}

Generate {language} code to solve the above mentioned problem.

Important: Your response must contain only the {language} code inside ``` block."""
    
    return [{"role": "user", "content": prompt}]

