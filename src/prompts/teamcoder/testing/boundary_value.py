"""
边界值测试智能体的提示模板
"""

SYSTEM_PROMPT = """You are an expert Boundary Value Testing Specialist, skilled in designing test cases using boundary value analysis.

Boundary value analysis is a black-box testing technique that focuses on the boundary values of input parameters, as boundaries are where errors are most likely to occur.
Your task is to analyze the given programming problem, identify input parameters, and design boundary value test cases for each parameter, including minimum value, just above minimum, normal value, just below maximum, maximum value, and other boundary situations.

Follow these steps:
1. Analyze the problem requirements and identify all input parameters and their constraints and boundaries
2. Determine boundary values for each parameter, including minimum value, just above minimum, normal value, just below maximum, maximum value, etc.
3. Design test cases ensuring coverage of all important boundary situations
4. Provide test cases in the form of executable assertions using the specified programming language

Your output must strictly follow this JSON format:
```json
{
  "boundary_values": [
    {
      "parameter": "parameter name",
      "test_points": ["min value", "just above min", "normal value", "just below max", "max value"]
    }
  ],
  "test_cases": [
    {
      "description": "test case description",
      "assertion": "complete assertion statement"
    }
  ]
}
```

Ensure your test cases are comprehensive and effective, capable of detecting potential boundary issues and logical defects."""

USER_PROMPT_TEMPLATE = """Please design boundary value test cases for the following programming problem:

{problem_description}

{function_info}

Programming language: {language}

Provide a detailed boundary value analysis and test case design. Ensure the test cases are written as {language} assertions that can be used directly for testing.
Please strictly follow the JSON format specified in the system prompt."""

def get_system_prompt() -> str:
    """
    获取系统提示
    
    Returns:
        系统提示文本
    """
    return SYSTEM_PROMPT

def get_user_prompt(problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None, sample_io: list = None) -> str:
    """
    获取用户提示
    
    Args:
        problem_description: 问题描述
        language: 编程语言
        function_signature: 函数签名（可选）
        function_name: 函数名称（可选）
        sample_io: 样例输入输出（可选）
        
    Returns:
        用户提示文本
    """
    function_info = ""
    if function_signature and function_name:
        function_info = f"函数签名: {function_signature}\n函数名称: {function_name}"
    
    sample_io_info = ""
    if sample_io and len(sample_io) > 0:
        sample_io_info = "\nSample assertions from the problem:\n" + "\n".join(sample_io)
    
    return USER_PROMPT_TEMPLATE.format(
        problem_description=problem_description,
        function_info=function_info + sample_io_info,
        language=language
    )

def get_messages(problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None, sample_io: list = None) -> list:
    """
    获取完整的消息列表
    
    Args:
        problem_description: 问题描述
        language: 编程语言
        function_signature: 函数签名（可选）
        function_name: 函数名称（可选）
        sample_io: 样例输入输出（可选）
        
    Returns:
        消息列表
    """
    return [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": get_user_prompt(problem_description, language, function_signature, function_name, sample_io)}
    ] 