"""
Analogical 策略的 code prompt 模块
通过类比学习：识别算法 → 写教程 → 提供例子 → 解决问题
"""

from typing import List, Dict


def get_messages(
    problem_description: str,
    language: str = "Python3",
    dataset_type: str = "HumanEval"
) -> List[Dict[str, str]]:
    """
    获取 Analogical 提示词消息列表
    
    Args:
        problem_description: 问题描述
        language: 编程语言
        dataset_type: 数据集类型（Analogical 不需要，保持接口一致）
        
    Returns:
        消息列表 [{"role": "user", "content": "..."}]
    """
    prompt = f"""Your goal is to write {language} code to solve competitive programming problems. Given a problem, explain the core concepts in it and provide other relevant problems. Then solve the original problem.

# Problem:
{problem_description}

# Instruction: (Your response must include the following points sequentially)

## Algorithms:
Identify the core concepts or algorithms used to solve the problem.

## Tutorial:
Write a useful tutorial about these algorithms.

## Example Problems: 
Provide three examples of relevant competitive programming problems that involve these algorithms. For each problem, describe the problem, explain the solution in detail, and then write the correct {language} code.

## {language} code to solve the original problem: 
Include the following points in your response: 
- Explanation of the solution: 
- {language} code to solve the problem (the inside ``` ``` block):"""
    
    return [{"role": "user", "content": prompt}]




