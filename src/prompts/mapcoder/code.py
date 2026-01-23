"""
MapCoder 策略的 prompt 模块
复杂的多步骤策略：KB + Exemplars + Planning + Verification + Code + Testing
"""

from typing import List, Dict, Tuple


def get_kb_exemplars_messages(
    problem_description: str,
    k: int = 3,
    language: str = "Python3"
) -> List[Dict[str, str]]:
    """
    Step 1: 获取知识库和例子生成的提示词
    
    Args:
        problem_description: 问题描述
        k: 需要回忆的相关问题数量
        language: 编程语言
        
    Returns:
        消息列表
    """
    mapping = {
        1: "one (01)",
        2: "two (02)",
        3: "three (03)",
        4: "four (04)",
        5: "five (05)",
        6: "six (06)",
    }
    
    k_str = mapping.get(k, f"{k}")
    
    prompt = f"""Given a problem, provide relevant problems then identify the algorithm behind it and also explain the tutorial of the algorithm.
# Problem:
{problem_description}

# Exemplars:
Recall {k_str} relevant and distinct problems (different from problem mentioned above). For each problem,
1. describe it
2. generate {language} code step by step to solve that problem
3. finally generate a planning to solve that problem

# Algorithm:

----------------
Important:
Your response must strictly follow the following xml format

<root>

<problem>
# Recall {k_str} relevant and distinct problems (different from problem mentioned above). Write each problem in the following format.
<description>
# Describe the problem.
</description>
<code>
# Let's think step by step to solve this problem in {language} programming language.
</code>
<planning>
# Planning to solve this problem.
</planning>
</problem>

# similarly add more problems here...

<algorithm>
# Identify the algorithm (Brute-force, Dynamic Programming, Divide-and-conquer, Greedy, Backtracking, Recursive, Binary search, and so on) that needs to be used to solve the original problem.
# Write a useful tutorial about the above mentioned algorithms. Provide a high level generic tutorial for solving this types of problem. Do not generate code.
</algorithm>

</root>
"""
    
    return [{"role": "user", "content": prompt}]


def get_problem_planning_messages(
    problem_description: str,
    example_problem: str,
    example_planning: str,
    algorithm: str,
    sample_io: str,
    language: str = "Python3"
) -> List[Dict[str, str]]:
    """
    Step 2: 获取问题规划的提示词
    
    Args:
        problem_description: 原问题描述
        example_problem: 例子问题
        example_planning: 例子的 planning
        algorithm: 识别的算法
        sample_io: 样例输入输出
        language: 编程语言
        
    Returns:
        消息列表
    """
    algorithm_prompt = f"## Relevant Algorithm to solve the next problem:\n{algorithm}"
    sample_io_prompt = f"## Sample Test cases: \n{sample_io}\n" if sample_io else ""
    
    # 原始提示词格式（单行）
    prompt = f"Given a competitive programming problem generate a concrete planning to solve the problem.\n# Problem:\n{example_problem}\n# Planning:\n{example_planning}\n{algorithm_prompt}\n## Problem to be solved:\n{problem_description}\n{sample_io_prompt}\n## Planning:\n\n----------------\nImportant: You should give only the planning to solve the problem. Do not add extra explanation or words."
    
    return [{"role": "user", "content": prompt}]


def get_planning_verification_messages(
    problem_description: str,
    planning: str,
    language: str = "Python3"
) -> List[Dict[str, str]]:
    """
    Step 3: 获取规划验证的提示词
    
    Args:
        problem_description: 问题描述
        planning: 要验证的 planning
        language: 编程语言
        
    Returns:
        消息列表
    """
    prompt = f"""Given a competitive programming problem and a plan to solve the problem in {language}, tell whether the plan is correct to solve this problem.

# Problem:
{problem_description}
# Planning:
{planning}

----------------
Important: Your response must follow the following xml format-```
<root>
<explanation> Discuss whether the given competitive programming problem is solvable by using the above mentioned planning.</explanation>
<confidence> Confidence score regarding the solvability of the problem. Must be an integer between 0 and 100. </confidence>
</root>
```"""
    
    return [{"role": "user", "content": prompt}]


def get_code_generation_messages(
    problem_description: str,
    planning: str,
    algorithm: str,
    sample_io: str,
    language: str = "Python3",
    dataset_type: str = "HumanEval"
) -> List[Dict[str, str]]:
    """
    Step 4: 获取代码生成的提示词
    
    Args:
        problem_description: 问题描述
        planning: 选定的 planning
        algorithm: 算法
        sample_io: 样例输入输出
        language: 编程语言
        dataset_type: 数据集类型
        
    Returns:
        消息列表
    """
    algorithm_prompt = f"## Relevant Algorithm to solve the next problem:\n{algorithm}"
    sample_io_prompt = f"## Sample Test cases: \n{sample_io}\n" if sample_io else ""
    
    # 根据数据集类型决定是否需要标准输入输出
    if dataset_type in ["APPS", "CodeContest", "XCodeEval"]:
        std_input_prompt = "## Note: Strictly follow the input and output format. The input should be taken from Standard input and output should be given to standard output. If you are writing a function then after the function definition take input using `input()` function then call the function with specified parameters and finally print the output of the function. Do not add extra print statement otherwise it will failed the test cases."
    else:
        std_input_prompt = ""
    
    # 原始提示词格式（单行）
    prompt = f"Given a competitive programming problem generate {language} code to solve the problem.\n{algorithm_prompt}\n## Problem to be solved:\n{problem_description}\n## Planning:\n{planning}\n{sample_io_prompt}\n## Let's think step by step.\n\n----------------\nImportant:\n{std_input_prompt}\n## Your response must contain only the {language} code to solve this problem. Do not add extra explanation or words."
    
    return [{"role": "user", "content": prompt}]


def get_code_improvement_messages(
    problem_description: str,
    current_planning: str,
    current_code: str,
    test_log: str,
    algorithm: str,
    language: str = "Python3",
    dataset_type: str = "HumanEval"
) -> List[Dict[str, str]]:
    """
    Step 5: 获取代码改进的提示词
    
    Args:
        problem_description: 问题描述
        current_planning: 当前的 planning
        current_code: 当前的代码
        test_log: 测试日志
        algorithm: 算法
        language: 编程语言
        dataset_type: 数据集类型
        
    Returns:
        消息列表
    """
    algorithm_prompt = f"## Relevant Algorithm to solve the next problem:\n{algorithm}"
    
    # 根据数据集类型决定是否需要标准输入输出
    if dataset_type in ["APPS", "CodeContest", "XCodeEval"]:
        std_input_prompt = "## Note: Strictly follow the input and output format. The input should be taken from Standard input and output should be given to standard output. If you are writing a function then after the function definition take input using `input()` function then call the function with specified parameters and finally print the output of the function. Do not add extra print statement otherwise it will failed the test cases."
    else:
        std_input_prompt = ""
    
    response_with_code = f"## Planning: {current_planning}\n## Code:\n```\n{current_code}\n```"
    
    # 原始提示词格式（单行）
    prompt = f"Given a competitive programming problem you have generated {language} code to solve the problem. But the generated code can not pass sample test cases. Improve your code to solve the problem correctly.\n{algorithm_prompt}\n## Problem to be solved:\n{problem_description}\n{response_with_code}\n## Test Report:\n{test_log}\n## Modified Planning:\n## Let's think step by step to modify {language} Code for solving this problem.\n\n----------------\nImportant:\n{std_input_prompt}\n## Your response must contain the modified planning and then the {language} code inside ``` block to solve this problem."
    
    return [{"role": "user", "content": prompt}]

