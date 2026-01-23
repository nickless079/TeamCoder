"""
The Arbiter Agent 提示词
"""

import json
from typing import List, Dict, Any


def get_messages(
    task_type: str,
    problem_description: str = "",
    sample_io: List[str] = None,
    attention_analysis: str = "",
    candidate_testcases: List[Dict] = None,
    initial_attention_analysis: str = "",
    **kwargs
) -> List[Dict[str, str]]:
    """
    根据任务类型返回相应的提示词消息
    
    Args:
        task_type: 任务类型
        problem_description: 问题描述
        sample_io: 样例输入输出
        attention_analysis: 注意力分析
        candidate_testcases: 候选测试用例
        
    Returns:
        消息列表
    """
    if task_type == "arbitrate_tests":
        return _get_arbitrate_tests_messages(
            problem_description, sample_io, attention_analysis, candidate_testcases
        )
    elif task_type == "arbitrate_fatal_point":
        return _get_arbitrate_fatal_point_messages(
            problem_description, sample_io, initial_attention_analysis
        )
    else:
        raise ValueError(f"Unknown task type: {task_type}")


def _get_arbitrate_tests_messages(
    problem_description: str,
    sample_io: List[str],
    attention_analysis: str,
    candidate_testcases: List[Dict]
) -> List[Dict[str, str]]:
    """
    获取仲裁测试用例的提示词消息
    """
    
    # 系统提示词
    system_prompt = """You are The Arbiter, the ultimate authority on logical correctness. Your mission is to establish the absolute 'Rule of Truth' for a problem by writing a self-contained 'Oracle' function, and then use this Oracle to forge the final, undeniable, and correct test suite from a pool of potentially flawed candidates."""
    
    # 用户提示词
    sample_io_str = "\n".join(sample_io) if sample_io else "No sample I/O provided"
    candidate_json = json.dumps(candidate_testcases, ensure_ascii=False, indent=2) if candidate_testcases else "[]"
    
    user_prompt = f"""# Final Arbitration of Test Cases

## 1. The Supreme Law (Level 1 Truth - Immutable)
<PROBLEM_DESCRIPTION>
{problem_description}
</PROBLEM_DESCRIPTION>
<SAMPLE_IO>
{sample_io_str}
</SAMPLE_IO>

## 2. Preliminary Intelligence (A clue, not a law)
This is an analysis from a previous agent. It may offer useful starting points but can be flawed and must be validated against the Supreme Law.
<ATTENTION_ANALYSIS>
{attention_analysis}
</ATTENTION_ANALYSIS>

## 3. Candidate Evidence (The pool to be audited)
{candidate_json}

## Your Mission: Forge the Golden Test Suite.

You must follow a rigorous, non-negotiable arbitration protocol. Your response must use ONLY the following **three** tags in order.

### 1. `<ARBITRATION_THOUGHT>`
Your arbitration process MUST follow these explicit steps:
1.  **Deconstruct the 'Rule of Truth' into an 'Oracle'**: Your first and most critical task is to translate the **Supreme Law** (`PROBLEM_DESCRIPTION` & `SAMPLE_IO`) into a miniature, correct, self-contained Python function that perfectly implements the problem's logic. **This 'Oracle' function will be written *inside this thought block* and is your ONLY standard for correctness.** It MUST correctly pass all `SAMPLE_IO`.
2.  **Audit ALL Candidate Tests using the 'Oracle'**: Now, for EACH assertion in the `Candidate Evidence`, you will perform a code-driven audit.
    a.  Extract the `input` and the `expected_output_from_test`.
    b.  Use your 'Oracle' function to calculate the **True Expected Output**. You must show the call, like `true_output = _oracle_function(input)`.
    c.  State your verdict for that test case: **CORRECT** or **FLAWED**.
3.  **Synthesize the 'Golden Set'**: Based on your audit, assemble the final, minimal, and correct set of test cases. You must include all `SAMPLE_IO` cases, and select a concise set of additional cases from the audited candidates that cover all key logic and boundary conditions revealed by your Oracle. Discard all flawed and redundant tests.

### 2. `<FINAL_THEORY>`
Based on your 'Oracle' function's logic, provide a concise, human-readable summary of the **final, confirmed 'Rule of Truth'**. This will serve as the definitive `attention_analysis` for all subsequent agents (like the Solution Planner and Coder).

### 3. `<CORRECTED_TESTS>`
Output the final, golden test suite in the standard JSON format. Each test case should have at minimum:
{{"assertion": "assert function_name(...) == expected_result", "description": "Brief description"}}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def _get_arbitrate_fatal_point_messages(
    problem_description: str,
    sample_io: List[str],
    initial_attention_analysis: str
) -> List[Dict[str, str]]:
    """
    获取仲裁致命点分析的提示词消息
    """
    
    # 系统提示词
    system_prompt = """You are The Arbiter, the ultimate authority on logical correctness. You have received a preliminary analysis from a junior analyst. Your mission is to establish the absolute 'Rule of Truth' by writing and validating an 'Oracle' function, and then to use this Oracle to conduct a FULL audit of the analyst's work, including their reasoning process and final conclusions, before forging the final, official blueprint."""
    
    # 用户提示词
    sample_io_str = "\n".join(sample_io) if sample_io else "No sample I/O provided"
    
    user_prompt = f"""# Final Arbitration of the Preliminary Analysis

## 1. The Supreme Law (Level 1 Truth - Immutable)
<PROBLEM_DESCRIPTION>
{problem_description}
</PROBLEM_DESCRIPTION>
<SAMPLE_IO>
{sample_io}
</SAMPLE_IO>

## 2. The Preliminary Hypothesis (To be Audited)
This is the full, unedited output from the AttentionAgent, including its reasoning log and its final conclusions. It may contain valuable insights, but also severe logical or computational errors.
<INITIAL_ANALYSIS>
{initial_attention_analysis} # <-- 传入 AttentionAgent 完整的、包含 <RECHECK> 和 <POINTS> 的原始输出
</INITIAL_ANALYSIS>

## Your Mission: Conduct a Full Audit and Forge the Golden Theory.

You must follow a rigorous, non-negotiable arbitration protocol.

## Output (MUST be in the specified multi-part format)

### Part 1:
 <ARBITRATION_THOUGHT> 
Your arbitration process MUST follow these explicit steps:
1.  **'Oracle' Construction and Validation**: First, based ONLY on the **Supreme Law**, write a miniature, correct 'Oracle' Python function that implements the problem's logic. Then, immediately verify it against all `SAMPLE_IO` to confirm its absolute correctness.
2.  **Audit of Analyst's REASONING**: Now, carefully review the analyst's reasoning log (`<RECHECK>` section). Compare their step-by-step simulation with the behavior of your own validated Oracle. Identify and list any specific logical or mathematical errors you find in their reasoning.
3.  **Audit of Analyst's CONCLUSIONS**: Review the analyst's final conclusions (`<POINTS>` section). Based on your Oracle and your audit of their reasoning, render a verdict on their conclusions. (e.g., "The analyst's final conclusion about 'conditional order' is correct, but they arrived at it via a flawed reasoning process. Their secondary point about floating-point numbers is also valid.")
4.  **Synthesis of Final Theory**: Synthesize your findings into the final, correct, and complete 'Rule of Truth'.
</ARBITRATION_THOUGHT>
### part2. 
<FINAL_FATAL_POINT_JSON> 
Output the final, golden 'Fatal Point Analysis' in the standard JSON format. This will be the definitive, trusted theory for all subsequent agents.
```json
{{
  "algorithm_sketch": [
    "Step 1: ...",
    "..."
  ],
  "primary_fatal_point": {{
    "trap_type": "...",
    "description": "..."
  }},
  "secondary_fatal_point": {{
    "trap_type": "...",
    "description": "..."
  }}
}}
```
</FINAL_FATAL_POINT_JSON>
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ] 