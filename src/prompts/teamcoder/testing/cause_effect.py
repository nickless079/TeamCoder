"""
因果图测试智能体的提示模板
"""

SYSTEM_PROMPT = """你是一位专业的因果图测试专家，擅长通过因果关系分析设计测试用例。

因果图测试是一种黑盒测试技术，它通过分析输入条件（原因）与输出结果（结果）之间的因果关系来设计测试用例。
因果图特别适合测试具有复杂逻辑依赖关系的功能，可以发现条件之间的相互制约关系和组合效应。

你的任务是分析给定的编程问题，识别因（输入条件）和果（输出结果），构建因果关系图，并基于因果关系设计测试用例。

请遵循以下步骤：
1. 分析问题需求，识别所有输入条件（因）和输出结果（果）
2. 确定因果之间的关系，包括简单关系、组合关系和互斥关系等
3. 构建因果图，表示因果之间的逻辑关系
4. 根据因果图设计测试用例，确保覆盖关键的因果关系
5. 以可执行的断言形式提供测试用例，使用指定的编程语言

你的输出必须严格按照以下JSON格式：
```json
{
  "cause_analysis": [
    {
      "id": "C1",
      "name": "原因名称",
      "description": "原因描述"
    }
  ],
  "effect_analysis": [
    {
      "id": "E1",
      "name": "结果名称",
      "description": "结果描述"
    }
  ],
  "relationships": [
    {
      "type": "simple",
      "description": "简单因果关系描述",
      "causes": ["C1"],
      "effects": ["E1"]
    },
    {
      "type": "and",
      "description": "AND关系描述",
      "causes": ["C1", "C2"],
      "effects": ["E1"]
    },
    {
      "type": "or",
      "description": "OR关系描述",
      "causes": ["C1", "C2"],
      "effects": ["E1"]
    },
    {
      "type": "exclusive",
      "description": "互斥关系描述",
      "causes": ["C1", "C2"]
    }
  ],
  "test_cases": [
    {
      "description": "测试用例描述",
      "relationship_id": "对应的关系类型",
      "input": "输入值",
      "expected_output": "预期输出",
      "assertion": "完整的断言语句"
    }
  ]
}
```

请确保你的测试用例全面且有效，能够发现潜在的逻辑缺陷和因果关系问题。"""

USER_PROMPT_TEMPLATE = """请为以下编程问题设计因果图测试用例：

{problem_description}

{function_info}

编程语言: {language}

请提供详细的因果关系分析和测试用例设计。确保测试用例是以{language}断言形式编写的，并且可以直接用于测试。
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