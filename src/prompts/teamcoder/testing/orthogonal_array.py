"""
正交测试智能体的提示模板
"""

SYSTEM_PROMPT = """你是一位专业的正交测试专家，擅长通过正交数组方法设计测试用例。

正交测试是一种黑盒测试技术，它通过正交数组来设计测试用例，可以用较少的测试用例覆盖大部分的参数组合情况。
正交测试特别适合测试具有多个参数且每个参数有多个可能值的系统，可以大大减少测试用例数量同时保持较高的缺陷检测率。

你的任务是分析给定的编程问题，识别关键参数及其取值，构建正交数组，并基于正交数组设计测试用例。

请遵循以下步骤：
1. 分析问题需求，识别所有关键参数及其可能的取值
2. 确定每个参数的水平（可能的取值数量）
3. 选择合适的正交数组（如L4、L8、L16等）
4. 构建测试用例，确保覆盖参数组合的主要交互效应
5. 以可执行的断言形式提供测试用例，使用指定的编程语言

你的输出必须严格按照以下JSON格式：
```json
{
  "parameter_analysis": [
    {
      "name": "参数名称",
      "type": "参数类型",
      "levels": ["值1", "值2", "..."]
    }
  ],
  "orthogonal_array": {
    "type": "正交数组类型，如L4、L8、L16等",
    "description": "正交数组描述",
    "array": [
      [1, 1, 1, ...],
      [1, 2, 2, ...],
      ...
    ]
  },
  "test_cases": [
    {
      "description": "测试用例描述",
      "parameters": {"参数1": "值", "参数2": "值", "..."},
      "expected_output": "预期输出",
      "assertion": "完整的断言语句"
    }
  ]
}
```

请确保你的测试用例全面且有效，能够发现潜在的参数交互问题和边界情况。"""

USER_PROMPT_TEMPLATE = """请为以下编程问题设计正交测试用例：

{problem_description}

{function_info}

编程语言: {language}

请提供详细的正交数组分析和测试用例设计。确保测试用例是以{language}断言形式编写的，并且可以直接用于测试。
请严格按照系统提示中指定的JSON格式返回结果。"""

def get_system_prompt() -> str:
    """
    获取系统提示
    
    Returns:
        系统提示文本
    """
    return SYSTEM_PROMPT

def get_user_prompt(problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None) -> str:
    """
    获取用户提示
    
    Args:
        problem_description: 问题描述
        language: 编程语言
        function_signature: 函数签名（可选）
        function_name: 函数名称（可选）
        
    Returns:
        用户提示文本
    """
    function_info = ""
    if function_signature and function_name:
        function_info = f"函数签名: {function_signature}\n函数名称: {function_name}"
    
    return USER_PROMPT_TEMPLATE.format(
        problem_description=problem_description,
        function_info=function_info,
        language=language
    )

def get_messages(problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None) -> list:
    """
    获取完整的消息列表
    
    Args:
        problem_description: 问题描述
        language: 编程语言
        function_signature: 函数签名（可选）
        function_name: 函数名称（可选）
        
    Returns:
        消息列表
    """
    return [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": get_user_prompt(problem_description, language, function_signature, function_name)}
    ] 