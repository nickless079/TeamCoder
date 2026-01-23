"""
解决方案规划智能体的提示模板
"""


def get_system_prompt() -> str:
    """
    获取系统提示
    
    Returns:
        系统提示文本
    """
    return """You are a Test-Driven Development (TDD) Solution Architect. Your mission is to take a set of test scenarios (an 'exam paper'), deduce the correct answers for them, and then design a single, robust algorithm that can pass the entire exam.
"""


def get_generate_solutions_prompt(problem_description: str, test_cases: dict,thought_content: str ,problem_sample_io: dict, attention_analysis: dict) -> str:
    """
    获取生成解决方案的提示
    
    Args:
        problem_description: 问题描述
        test_cases: 测试用例
        
    Returns:
        提示文本
    """
    import json
    rules = attention_analysis['fatal_points']['Rules'] 
    traps_data = attention_analysis['fatal_points'].get('Traps', '{}')
    
    prompt = f"""# ### ROLE & MISSION
You are a Principal Software Engineer. Your mission is to write production-ready Plan. **Your primary directive is to implement `<THE_RULES>` with absolute fidelity. The `<THE_PRIMARY_TRAP>` serves as a critical warning of specific logic patterns and interpretations to AVOID.**

### ENGINEERING BLUEPRINT
This section contains the definitive, multi-part specification. Your implementation MUST be a direct and faithful execution of this blueprint. This is your **sole source of truth**.

<THE_RULES>
{rules}
</THE_RULES>

<THE_TRAP>
{traps_data}
</THE_TRAP>

### CONTEXT: Original Problem Description
This is provided for context and vocabulary only. **The `<ENGINEERING_BLUEPRINT>` above is your sole source of truth.**
<PROBLEM_DESCRIPTION>
{problem_description}
</PROBLEM_DESCRIPTION>

---

### EXECUTION PROTOCOL
First, complete the `<SYNTHESIS_AND_STRATEGY>` block by detailing how you will derive a robust plan from the blueprint. Then, write the final, complete plan inside the `<FINAL_PLAN>` block.

---
### REQUIRED OUTPUT STRUCTURE

<SYNTHESIS_AND_STRATEGY>
1.  **Rule Implementation:** How will your code's logic perfectly implement every detail from `<THE_RULES>` in detail? **Critically analyze **every word** in its definition to ensure your low-level logic is precise (e.g., how to handle a custom ordering system;).**
2.  **Trap Countermeasure:** **Re-affirming your commitment to implementing `<THE_RULES>` precisely**, how will your code's structure and logic **actively prevent** the flawed behavior described in `<THE_TRAP>`?
</SYNTHESIS_AND_STRATEGY>

<FINAL_PLAN>
... Your final completed and detailed plan, not the code! ...
</FINAL_PLAN>

---
START OF YOUR RESPONSE
"""
    return prompt


def get_messages(task_type: str, **kwargs) -> list:
    """
    获取完整的消息列表
    
    Args:
        task_type: 任务类型，如'generate_solutions'等
        **kwargs: 任务相关参数
        
    Returns:
        消息列表
    """
    messages = [{"role": "system", "content": get_system_prompt()}]
    
    if task_type == "generate_solutions":
        messages.append({
            "role": "user", 
            "content": get_generate_solutions_prompt(
                kwargs.get("problem_description", ""),
                kwargs.get("test_cases", {}),
                kwargs.get("thought_content", ""),
                kwargs.get("problem_sample_io", {}),
                kwargs.get("attention_analysis", {})
            )
        })
    else:
        raise ValueError(f"未知的任务类型: {task_type}")
    
    return messages 