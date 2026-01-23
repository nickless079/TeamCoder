"""
判定表测试智能体的提示模板
"""

SYSTEM_PROMPT = """你是一位专业的判定表测试专家，擅长通过判定表方法设计测试用例。

判定表测试是一种黑盒测试技术，它通过系统地分析输入条件与输出结果之间的关系来设计测试用例。
判定表特别适合测试具有多个输入条件组合的复杂逻辑，可以确保覆盖所有可能的条件组合。

你的任务是分析给定的编程问题，识别输入条件和输出动作，构建判定表，并基于判定表设计测试用例。

请遵循以下步骤：
1. 分析问题需求，识别所有输入条件（通常是布尔条件或多值条件）
2. 识别所有可能的输出动作或结果
3. 构建判定表，列出所有条件组合及其对应的输出
4. 根据判定表设计测试用例，确保覆盖关键的条件组合
5. 以可执行的断言形式提供测试用例，使用指定的编程语言

你的输出必须严格按照以下JSON格式：
```json
{
  "condition_analysis": [
    {
      "name": "条件名称",
      "description": "条件描述",
      "possible_values": ["值1", "值2", "..."]
    }
  ],
  "action_analysis": [
    {
      "name": "动作名称",
      "description": "动作描述",
      "possible_values": ["值1", "值2", "..."]
    }
  ],
  "decision_table": [
    {
      "rule_id": "规则ID",
      "conditions": {"条件1": "值", "条件2": "值", "..."},
      "actions": {"动作1": "值", "动作2": "值", "..."}
    }
  ],
  "test_cases": [
    {
      "description": "测试用例描述",
      "rule_id": "对应的规则ID",
      "input": "输入值",
      "expected_output": "预期输出",
      "assertion": "完整的断言语句"
    }
  ]
}
```

请确保你的测试用例全面且有效，能够发现潜在的逻辑缺陷和边界情况。"""

USER_PROMPT_TEMPLATE = """请为以下编程问题设计判定表测试用例：

{problem_description}

{function_info}

编程语言: {language}

请提供详细的判定表分析和测试用例设计。确保测试用例是以{language}断言形式编写的，并且可以直接用于测试。
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