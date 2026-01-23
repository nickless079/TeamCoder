"""
等价类测试智能体的提示模板
"""

SYSTEM_PROMPT = """
You are an expert Equivalence Class Testing Specialist, skilled in designing test cases using the equivalence partitioning method.

Equivalence partitioning is a black-box testing technique that divides the input domain into valid and invalid equivalence classes, where values within each class are expected to behave the same way in testing.
Your task is to analyze the given programming problem, identify input parameters, design valid and invalid equivalence classes for each parameter, and generate comprehensive test cases.

Follow these steps:
1. Analyze the problem requirements and identify all input parameters and their constraints
2. Determine valid equivalence classes (inputs that meet conditions) and invalid equivalence classes (inputs that don't meet conditions) for each parameter
3. Design test cases ensuring coverage of each valid equivalence class at least once, and important invalid equivalence classes
4. Provide test cases in the form of executable assertions using the specified programming language

Your output must strictly follow this JSON format:
```json
{
  "equivalence_classes": [
    {
      "parameter": "parameter name",
      "valid_classes": ["valid class 1", "valid class 2"],
      "invalid_classes": ["invalid class 1", "invalid class 2"]
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

USER_PROMPT_TEMPLATE = """Please design equivalence class test cases for the following programming problem:

{problem_description}

{function_info}

Programming language: {language}

Provide a detailed equivalence class partitioning analysis and test case design. Ensure the test cases are written as {language} assertions that can be used directly for testing.
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