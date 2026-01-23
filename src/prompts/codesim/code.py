from typing import List, Dict, Any

def get_planning_messages(problem: str, language: str) -> List[Dict[str, str]]:
    """
    生成规划阶段的提示词消息
    
    Args:
        problem: 问题描述
        language: 编程语言
    
    Returns:
        消息列表
    """
    return [
        {
            "role": "user",
            "content": f"""You are a programmer tasked with generating appropriate plan to solve a given problem using the **{language}** programming language.

## Problem

{problem}

**Expected Output:**

Your response must be structured as follows:

### Problem Understanding

- Think about the original problem. Develop an initial understanding about the problem.

### Recall Example Problem

Recall a relevant and distinct problems (different from problem mentioned above) and
- Describe it
- Generate {language} code step by step to solve that problem
- Discuss the algorithm to solve this problem
- Finally generate a planning to solve that problem

### Algorithm to solve the original problem

- Write down the algorithm that is well suited for the original problem
- Give some tutorials to about the algorithm for example:
    - How to approach this type of algorithm
    - Important things to consider

### Plan

- Write down a detailed, step-by-step plan to solve the **original problem**.

--------
**Important Instruction:**
- Strictly follow the instructions.
- Do not generate code.""",
        },
    ]


def get_simulation_messages(problem_with_planning: str, language: str) -> List[Dict[str, str]]:
    """
    生成模拟阶段的提示词消息（验证计划是否正确）
    
    Args:
        problem_with_planning: 问题描述 + 计划
        language: 编程语言
    
    Returns:
        消息列表
    """
    return [
        {
            "role": "user",
            "content": f"""You are a programmer tasked with verifying a plan to solve a given problem using the **{language}** programming language.

{problem_with_planning}

**Expected Output:**

Your response must be structured as follows:

### Simulation

- Take a sample input and apply plan step by step to get the output. Do not generate code do it manually by applying reasoning.
- Compare the generated output with the sample output to verify if your plan works as expected.

### Plan Evaluation

- If the simulation is successful write **No Need to Modify Plan**.
- Otherwise write **Plan Modification Needed**.
""",
        },
    ]


def get_plan_refinement_messages(problem_with_planning: str, critique: str, language: str) -> List[Dict[str, str]]:
    """
    生成计划优化阶段的提示词消息
    
    Args:
        problem_with_planning: 问题描述 + 原计划
        critique: 模拟阶段的批评/反馈
        language: 编程语言
    
    Returns:
        消息列表
    """
    return [
        {
            "role": "user",
            "content": f"""You are a programmer tasked with generating appropriate plan to solve a given problem using the **{language}** programming language. You already have a wrong plan. Correct it so that it can generate correct plan.

{problem_with_planning}

## Plan Critique

{critique}

**Expected Output:**

Your response must be structured as follows:

## New Plan

- Write down a detailed, step-by-step modified plan to solve the **original problem**.
- Ensure each step logically follows from the previous one.

--------
**Important Instruction:**
- Your response must contain only the plan.
- Do not add any explanation.
- Do not generate code.""",
        },
    ]


def get_code_generation_messages(problem_with_planning: str, language: str, std_input_prompt: str) -> List[Dict[str, str]]:
    """
    生成代码生成阶段的提示词消息
    
    Args:
        problem_with_planning: 问题描述 + 计划
        language: 编程语言
        std_input_prompt: 标准输入提示（针对竞赛类问题）
    
    Returns:
        消息列表
    """
    return [
        {
            "role": "user",
            "content": f"""You are a programmer tasked with solving a given problem using the **{language}** programming language. See the plan to solve the plan and implement code to solve it.

{problem_with_planning}

--------
**Important Instructions:**
- Do not add any explanation.
- The generated **{language}** code must be inside a triple backtick (```) code block.
{std_input_prompt}""",
        },
    ]


def get_debugging_messages(problem_with_planning: str, code: str, test_log: str, language: str, std_input_prompt: str) -> List[Dict[str, str]]:
    """
    生成调试阶段的提示词消息
    
    Args:
        problem_with_planning: 问题描述 + 计划
        code: 有bug的代码
        test_log: 测试日志
        language: 编程语言
        std_input_prompt: 标准输入提示（针对竞赛类问题）
    
    Returns:
        消息列表
    """
    return [
        {
            "role": "user",
            "content": f"""You are a programmer who has received a solution of a problem written in **{language}** that fails to pass certain test cases. Your task is to modify the code in such a way so that it can pass all the test cases. Do not generate same code.

{problem_with_planning}

### Buggy Code
```{language}
{code}
```

{test_log}

**Expected Output:**

Your response must be structured as follows:

### Simulation with failed test case
To detect where is the bug follow following steps:
    - Take a sample test case where it fails.
    - Take the input go through each step according to the plan
    - You will get a output that must be different from the expected output.

### Debugging Notes
- Based on this simulation detect any of the following cases:
    - Plan is wrong
    - Plan is correct but plan to code generation is wrong.
- Finally, discuss how to correct this code.

### Modified Code

```{language}
# Your corrected code, with comments explaining each correction.
```

--------
**Important Instructions:**
- Strictly follow the instructions.
- Do not add testing code for example assert statement in your code.
- Do not be overconfident that the generated code is correct. It is wrong.
- The modified **{language}** code must be enclosed within triple backticks (```).
- Your response must contain **Simulation with failed test case**, **Debugging Notes**,
and **Modified Code** section.
{std_input_prompt}""",
        },
    ]
