"""
CTO智能体的提示模板
"""

from typing import Any, Dict


def get_system_prompt() -> str:
    """
    获取CTO智能体的系统提示
    
    Returns:
        系统提示文本
    """
    return """You are The Arbiter, the ultimate authority on logical correctness. You are being brought in because the project is in a critical state: the preliminary test suite is believed to be riddled with errors. Your mission is to establish the absolute 'Rule of Truth' and forge a new, correct test suite from scratch. Failure to correct the flawed tests will lead to project failure.\n """

def get_summarize_test_cases_prompt(problem_description: str, test_results: list, sample_io:list,attention_analysis: Dict[str, Any]) -> str:
    """
    获取总结测试用例的提示
    
    Args:
        problem_description: 问题描述
        test_results: 各测试智能体的测试结果列表
        
    Returns:
        提示文本
    """
    import json
    
    # 构建测试结果部分
    test_results_section = ""
    for i, result in enumerate(test_results):
        agent_type = result.get("type", f"Testing Agent {i+1}")
        test_results_section += f"### {agent_type}\n"
        
        # 添加结构化数据（如果有）
        if result.get("structured_data"):
            test_results_section += "```json\n"
            test_results_section += json.dumps(result["structured_data"], ensure_ascii=False, indent=2)
            test_results_section += "\n```\n\n"
        else:
            # 添加非结构化数据
            for key, value in result.items():
                if key not in ["type", "analysis", "structured_data"] and value:
                    test_results_section += f"#### {key}\n{value}\n\n"
    
    prompt = f"""# Final Arbitration of Test Cases

## 1. The Supreme Law (Level 1 Truth - Your ONLY Source of Truth)
This is the absolute, non-negotiable source of truth.
<PROBLEM_DESCRIPTION>
{problem_description}
</PROBLEM_DESCRIPTION>
<SAMPLE_IO>(always true)
{sample_io}
</SAMPLE_IO>

## 2. Evidence to be Audited (Assume it is flawed until proven correct)
This is the candidate test suite from the TestAgent.
{test_results_section}

## 3. Analyst's Notes (For Context and Inspiration ONLY)
This is the thought process from the TestAgent. Use it to understand which scenarios the agent *intended* to test, but **DO NOT trust its conclusions or calculations**.
{attention_analysis} 

## Your Mission: Forge the Golden Test Suite from First Principles.

You must follow a rigorous, non-negotiable protocol.

## Output (exactly TWO parts in order)

### Part 1: <thought> Block
Your arbitration process MUST follow these explicit steps:
1.  **Rule Extraction**: Your first task is to meticulously scan the `PROBLEM_DESCRIPTION` and list **EVERY SINGLE ATOMIC RULE** exactly as written. You must pay extreme attention to the comparison operators (`==`, `>`).
    *(This is a purely abstract example of the required thinking:
    "I have extracted the following atomic rules from the source:
    - Rule 1: input == 'specific_value_A' -> output 'Category X'
    - Rule 2: input > threshold_B -> output 'Category Y'
    - Rule 3: input > threshold_C -> output 'Category Z'
    - Rule 4: input == 'specific_value_D' -> output 'Category W'
    This step ensures no rule is missed or misinterpreted.")*

2.  **'Oracle' Function Construction**: Now, and only now, you will translate the **complete and exact list of extracted rules** from Step 1 into a self-contained Python 'Oracle' function. **The `if/elif/else` structure of your Oracle MUST directly and perfectly correspond to the extracted rules.**

3.  **Oracle Validation**: You MUST immediately confirm that your Oracle correctly reproduces all `SAMPLE_IO`. This validates that your Oracle is the 'Rule of Truth'.

4.  **Audit ALL Candidate Tests using the 'Oracle'**: Now, for EACH assertion, use your validated 'Oracle' to calculate the **True Expected Output**. State your verdict for each test case: **CORRECT** or **FLAWED**.

5.  **Synthesize the Final 'Golden Set'**: Based on your audit, assemble the final, minimal, and correct set of test cases.

### Part 2: JSON Block(remember to include the assert )
Output the final, audited, and corrected test suite in the specified JSON format.
```json
{{
  "test_strategy": "A concise strategy sentence reflecting the 'Golden Set' categories.",
  "test_cases": [
    {{ "assertion": "assert function_name(args) == expected_literal", "description": "A clear description linking to its purpose (e.g., Sample IO, Fatal Point Test, Boundary Case)." }}
  ]
}}
"""
    return prompt

def get_evaluate_solutions_prompt(problem_description: str, initial_solutions:str,test_cases: dict, attention_analysis: Dict[str, Any], thought_content: str) -> str:
    """
    获取评估解决方案的提示
    
    Args:
        problem_description: 问题描述
        test_cases: 测试用例
        attention_analysis: 重点分析结果
        thought_content: 思考内容
        
    Returns:
        提示文本
    """
    import json
    
    prompt = f"""# Phase 2: CTO Technical Solution Evaluation

## Problem Description
{problem_description}

## Sample IO(!!! important !!! must be considered)
```json
{json.dumps(test_cases, ensure_ascii=False, indent=2)}
```
## initial_solutions
{initial_solutions}
## Attention Analysis(!!! important !!! must be considered)
{attention_analysis}


## Technical Solution Evaluation Requirements
As the CTO, please conduct a comprehensive evaluation of the technical solutions follow the RULES:
Please output your evaluation results in this format:
<thought>
0.ensure the plan can pass the sample io and include the attention analysis.
1.Check if the plan defines new formulas that contradict the problem description.
2.check the plan is consider carefully the attention analysis.
3.the solution is wrong ,please check it carefully.like this:
    Note that when n is odd, n+1 must be even (since odd + 1 = even). According to the problem definition, even numbers have a direct formula: tri(even) = 1 + even/2. Therefore, when calculating tri(n) for odd n (which requires tri(n+1) in its formula), tri(n+1) should be computed using the even-number formula directly (1 + (n+1)/2) instead of recursive calls. This avoids circular dependencies and ensures compliance with the problem's definition of even-number cases.
4.write the correct solution in the json format.
</thought>
```json
{{
"solutions": [
    {{
      "name": "Solution Name",
      "detail_steps"(before you write the detail steps,you must consider  and reread the analysis step): ["Step 1", "Step 2", "Step 3"]
    }}
  ]
}}

```

Please ensure your evaluation is professional, comprehensive, and objective, demonstrating CTO-level technical judgment and forward-thinking.
"""
    return prompt

def get_finalize_technical_plan_prompt(problem_description, test_cases, optimized_plan):
    """
    获取CTO确定最终技术方案的提示词
    
    Args:
        problem_description: 问题描述
        test_cases: 测试用例
        optimized_plan: 优化后的技术方案上下文，包含讨论记录
        
    Returns:
        提示词
    """
    # 处理讨论记录，避免在f-string中嵌套过深
    discussion_records = ""
    if "讨论记录" in optimized_plan and optimized_plan["讨论记录"]:
        discussion_records = str(optimized_plan["讨论记录"])
    elif "discussion_history" in optimized_plan and optimized_plan["discussion_history"]:
        discussion_records = str(optimized_plan["discussion_history"])
    
    # 使用字符串拼接而不是嵌套f-string
    prompt = "# Phase 2: CTO Final Technical Plan Determination\n\n"
    
    prompt += "## Problem Description\n"
    prompt += str(problem_description) + "\n\n"
    
    prompt += "## Test Cases\n"
    prompt += str(test_cases) + "\n\n"
    
    prompt += "## Discussion Records\n"
    prompt += discussion_records + "\n\n"
    
    prompt += """As the CTO, you need to determine the final technical implementation plan based on the problem description, test cases, and discussions with the Solution Planning Agent.

Please extract key information directly from the discussion records, analyze the advantages and disadvantages of each approach, and determine an optimal technical solution or create a new solution by combining the strengths of multiple approaches.

Your final technical plan should include:
1. Detailed description of the algorithm or solution approach
2. Data structure choices and rationale
3. Time and space complexity analysis
4. Implementation approach for key functions
5. How to handle edge cases and exceptions
6. How to ensure all test cases pass

Please return the final technical plan in JSON format as follows:
```json
{
  "final_solution": {
    "name": "Final solution name",
    "overview": "Solution overview",
    "algorithm": "Detailed algorithm description - include all key considerations",
    "complexity": {
      "time": "Time complexity",
      "space": "Space complexity"
    },
    "implementation_details": {
      "key_functions": [
        {
          "name": "Function name",
          "purpose": "Function purpose",
          "logic": "Function logic"
        }
      ],
      "edge_cases": ["Edge case 1", "Edge case 2"],
    }
  },
  "rationale": "Rationale for selecting this solution"
}
```

Please ensure your plan is specific, feasible, and effectively solves the problem."""
    
    return prompt

def get_review_code_prompt(problem_description: str, test_cases: dict, technical_plan: dict, code: str, language: str, attention_analysis: Dict[str, Any], thought_content: str) -> str:
    """
    获取CTO代码审查的提示词
    
    Args:
        problem_description: 问题描述
        test_cases: 测试用例/sample io
        technical_plan: 技术方案
        code: 代码
        language: 编程语言
        
    Returns:
        提示词
    """
    # 处理技术方案，避免嵌套过深
    tech_plan_str = str(technical_plan)
    
    # 构建提示词
    prompt = f"""### ROLE AND GOAL
You are a highly precise Code Gatekeeper. Your job is **NOT** to evaluate the logic or structure of the code. Your sole responsibility is to perform two specific, mechanical checks: Public API signature verification and dependency import verification.

## Problem Description
{problem_description}

## Code Implementation (Python3)
```python
{code}
YOUR TASK
You must perform exactly two checks and then generate the corrected code. Your entire thought process must be laid out in the <THOUGHT> tag.
<THOUGHT>
Your thought process must follow these **only two** steps:
Step 1: Public API Signature Verification
1a. Specification: Identify the exact required public API signature from the Problem Description. This includes the function name, all parameters (name, order), and any type hints.
1b. Implementation: Identify the main function in the Code Implementation that is intended to be the public API.
1c. Discrepancy Check: Compare the specification from 1a with the implementation from 1b. List any and all differences (function name, parameter names, type hints).
1d. Helper Functions: List all other helper functions found in the code.
--- CRITICAL CASE LAW: How to Handle Helper Functions ---
SITUATION: Imagine the Problem Description requires def C():. The Code Implementation provides def A():, def B():, and def C_1():, where C_1 is the main function.
YOUR DUTY:
You MUST identify that C_1 needs to be renamed to C.
You MUST NOT modify or delete def A(): and def B():. They are considered internal implementation details and must be preserved exactly as they are.
This principle is absolute. Your only concern is the public-facing API. Do not touch helper functions.
-----------------------------------------------------------
Step 2: Dependency Import Verification
2a. Identify Dependencies: Scan the entire Code Implementation and list all external packages used (e.g., re, math).
2b. Check Imports: Verify if an import statement exists for every dependency identified in 2a. List any missing imports.

</THOUGHT>
<INFO>
[Your final code here. Helper functions MUST be preserved untouched. If no changes are needed, return the original code here.]
</INFO>
"""
    return prompt

def get_check_imports_prompt(code: str, language: str) -> str:
    """
    获取CTO import检查的提示词
    
    Args:
        code: 要检查的代码
        language: 编程语言
        
    Returns:
        提示词
    """
    prompt = f"""### ROLE AND GOAL
You are a {language} Import Validator. Your job is to perform a focused import check to ensure all import statements are correct and necessary.

## Code Implementation ({language})
```{language.lower()}
{code}
```

YOUR TASK
You must perform import validation and then generate the corrected code. Your entire thought process must be laid out in the <THOUGHT> tag.

<THOUGHT>
Your thought process must follow these steps:

Step3: Common Checks
3a. Check Imports is right: such as "from typing import float" is wrong, you should remove it, because float is a built-in type.
3b. Check for unnecessary imports: Remove any import statements that are not used in the code.
3c. Check for missing imports: Add any missing import statements for libraries/modules that are used but not imported.
3d. Check import formatting: Ensure imports follow proper conventions (e.g., standard library imports first, then third-party, then local imports).

For each import statement, verify:
- Is it importing a valid module/function/class?
- Is the imported item actually used in the code?
- Are there any built-in types being incorrectly imported from typing or other modules?
- Are there any syntax errors in import statements?

List all issues found and the corrections needed.
</THOUGHT>

<INFO>
[Your final corrected code here. If no changes are needed, return the original code exactly as provided.]
</INFO>
"""
    return prompt

def get_messages(task_type: str, **kwargs) -> list:
    """
    获取完整的消息列表
    
    Args:
        task_type: 任务类型，如'summarize_test_cases', 'evaluate_solutions'等
        **kwargs: 任务相关参数
        
    Returns:
        消息列表
    """
    messages = [{"role": "system", "content": get_system_prompt()}]
    
    if task_type == "summarize_test_cases":
        messages.append({
            "role": "user", 
            "content": get_summarize_test_cases_prompt(
                kwargs.get("problem_description", ""),
                kwargs.get("test_results", []),
                kwargs.get("sample_io", []),
                kwargs.get("attention_analysis", {})
            )
        })
    elif task_type == "evaluate_solutions":
        messages.append({
            "role": "user", 
            "content": get_evaluate_solutions_prompt(
                kwargs.get("problem_description", ""),
                kwargs.get("initial_solutions", {}),
                kwargs.get("test_cases", {}),
                kwargs.get("attention_analysis", {}),
                kwargs.get("thought_content", "")
            )
        })
    elif task_type == "finalize_technical_plan":
        messages.append({
            "role": "user", 
            "content": get_finalize_technical_plan_prompt(
                kwargs.get("problem_description", ""),
                kwargs.get("test_cases", {}),
                kwargs.get("optimized_plan", {})
            )
        })
    elif task_type == "review_code":
        messages.append({
            "role": "user", 
            "content": get_review_code_prompt(
                kwargs.get("problem_description", ""),
                kwargs.get("test_cases", {}),
                kwargs.get("technical_plan", {}),
                kwargs.get("code", ""),
                kwargs.get("language", "Python"),
                kwargs.get("attention_analysis", {}),
                kwargs.get("thought_content", "")
            )
        })
    elif task_type == "check_imports":
        messages.append({
            "role": "user", 
            "content": get_check_imports_prompt(
                kwargs.get("code", ""),
                kwargs.get("language", "Python")
            )
        })
    else:
        raise ValueError(f"未知的任务类型: {task_type}")
    
    return messages