from typing import Dict, Any, List

def get_messages(task_type: str, **kwargs) -> List[Dict[str, str]]:
    """
    根据任务类型获取AttentionAgent的提示消息
    
    Args:
        task_type: 任务类型
        **kwargs: 任务参数
        
    Returns:
        消息列表
    """
    if task_type == "find_fatal_points":
        return _get_find_fatal_points_messages(**kwargs)
    elif task_type == "find_stage_errors":
        return _get_find_stage_errors_messages(**kwargs)
    elif task_type == "self_correction":
        return _get_self_correction_messages(**kwargs)
    else:
        raise ValueError(f"不支持的任务类型: {task_type}")

def _get_find_fatal_points_messages(
    problem_description: str,
    sample_io: List[str] = None,
    **kwargs
) -> List[Dict[str, str]]:
    """
    获取找出最致命关键点任务的消息
    """
    sample_io_text = ""
    if sample_io:
        sample_io_text = f"\n" + "\n".join(f"{io}" for io in sample_io)
    
    user_content = f"""### ROLE AND GOAL
You are a master-level Failure Analyst. Your purpose is to analyze a programming problem and identify the most critical and non-obvious **"Fatal Traps"**. A "Fatal Trap" is the negative consequence of failing to implement a core requirement in a robust way. Your analysis must be forward-looking and constructive.

### The "Principle-To-Trap" Deduction Protocol
You MUST perform the following steps in order. Your entire analysis is a positive deduction of principles and the risks of violating them.

**Step 1: The 'Rule of Truth' Deduction.**
-   Deduce the core requirements and all hidden constraints by meticulously analyzing the `Problem Description` and every `Sample I/O`.
-   **Crucially, challenge your initial interpretation. Is there a non-obvious way to model the problem that leads to a different outcome? Consider the problem from a mathematical or combinatorial perspective, not just a literal one.**
    *   *(Self-Correction Example: "Initial thought: 'Find unique elements' implies just using a set. Re-evaluation: Does the order of elements matter? The problem description is silent, but the sample I/O `[1, 5, 2, 1]` -> `[1, 5, 2]` shows that the original order of first appearance must be preserved. Therefore, a simple set conversion is wrong; the 'Rule of Truth' requires maintaining order.")*
-   This establishes the foundational "what" that needs to be done.

**Step 2: The "Critical Operations & Robust Principles" Analysis.**
-   Based on the 'Rule of Truth', identify the 1-3 most **critical operations** required for a solution (e.g., "splitting the input string", "checking the primary condition").
-   For **each** critical operation, you must define the **"Robust Implementation Principle"**. This is a clear, positive statement of the correct, most resilient way to implement that single operation to handle all cases.
    *   *(Abstract Example: "For the 'data splitting' operation, the Robust Principle is to use a method that correctly handles consecutive and trailing delimiters.")*

**Step 3: The 'Fatal Traps' Distillation.**
-   **This is your final and most important step.** You will now directly translate each "Robust Principle" into a corresponding "Fatal Trap".
-   A "Fatal Trap" is defined as **the specific, negative outcome that will occur if a developer fails to adhere to a "Robust Implementation Principle"** you identified in Step 2.
-   **Primary Trap**: This MUST be the trap derived from the **most critical and subtle** Robust Principle. Your description of the trap should be a clear warning.
    *   *(Abstract Example Derivation: "From the Robust Principle for 'data splitting', I deduce the Primary Trap: 'Failing to handle consecutive delimiters will result in processing invalid empty strings, leading to incorrect counts or errors.'")*
-   **Secondary Trap**: This should be the trap derived from another important Robust Principle.

---

NOW you can start your analysis:
True Problem Description(attention any detail,don't miss any detail):
{problem_description}
True SAMPLE_IO(may is none):
{sample_io_text}
--------------------------------
### REQUIRED OUTPUT FORMAT

Please only Return in the following two Parts:

1.  **the first part:**
    <RECHECK>
    You MUST transparently execute the 3-step "Principle-To-Trap" Deduction Protocol here. Your reasoning for each step, especially the direct link between the principles in Step 2 and the traps in Step 3, must be clear.
    </RECHECK>

2.  **the second part:**
    <POINTS>
    Based on your final distillation in Step 3, write the fatal traps in the standard JSON format.
    </POINTS>
"""

    return [
        # {
        #     "role": "system",
        #     "content": "You are an expert agent skilled at analyzing programming problems. Your sole purpose is to identify the most easily overlooked but fatal critical points in programming problems. If these points are ignored, it will lead to failure in solving the programming problem."
        # },
        {
            "role": "user",
            "content": user_content
        }
    ]

def _get_find_stage_errors_messages(
    problem_description: str,
    content: str,
    sample_io: List[str] = None,
    **kwargs
) -> List[Dict[str, str]]:
    """
    获取找出阶段错误的消息
    """
    sample_io_text = ""
    if sample_io:
        sample_io_text = f"\nSample IO:\n" + "\n".join(f"{io}" for io in sample_io)
    
    user_content = f"""Please analyze the following programming problem and stage content to identify the most fatal critical points that could be easily overlooked.

Problem Description:
{problem_description}{sample_io_text}

Stage Content to Analyze:
{content}

You are an expert agent skilled at analyzing programming problems and stage content. Your task is to identify the most easily overlooked but fatal critical points in the stage content that could lead to failure in solving the programming problem.

Please carefully examine:
1. Whether the stage content correctly interprets the problem requirements
2. Whether there are logical inconsistencies in the stage content
3. Whether the stage content contradicts the sample IO
4. Whether critical edge cases or constraints are missed in the stage content
5. Whether the stage content introduces errors that weren't in the original problem

Return your analysis in this format:
<points>the most fatal point in the stage content</points>"""

    return [
        {
            "role": "system",
            "content": "You are an expert agent skilled at analyzing programming problems and stage content. Your sole purpose is to identify the most easily overlooked but fatal critical points in stage content that could lead to failure in solving the programming problem."
        },
        {
            "role": "user",
            "content": user_content
        }
    ]

def _get_self_correction_messages(
    problem_description: str,
    sample_io: List[str],
    fatal_points: str,
    recheck: str,
    **kwargs
) -> List[Dict[str, str]]:
    """
    获取自我纠错任务的消息
    """
    user_content = f"""# Cross-Examination of a Previous Analysis

## 1. The Document Under Scrutiny (The Previous Analysis)
This is the full analysis from the previous step. It is **assumed to be flawed** until you can prove it correct.
<PREVIOUS_RECHECK>(Must be included wrong information)
{recheck}
</PREVIOUS_RECHECK>
<PREVIOUS_POINTS>
{fatal_points}
</PREVIOUS_POINTS>

## 2. The Ground Truth (The Supreme Law)
This is the only source of truth you can use to conduct your cross-examination.
# True Problem Description(attention any detail,don't miss any detail):
{problem_description}
# True SAMPLE_IO(may is none):
{sample_io}

## Your Mission: Conduct a Formal Cross-Examination and Issue a Corrected Report.

You must follow a rigorous, non-negotiable protocol.

## Output Format:
Your entire response MUST be structured using the following two tags. You will begin your response immediately with the `<RECHECK>` tag.

---
### START OF YOUR RESPONSE
---

<RECHECK>
**Here, you will log your entire cross-examination process.**
You MUST structure your recheck as a formal cross-examination log, following these sections in order:

**Section 1: Audit of the 'Implementation Blueprint'**
-   **Claim from Previous Analysis**: I will now re-state the `Core Logic & Control Flow` blueprint proposed in the `PREVIOUS_RECHECK`.
-   **Cross-Examination**: Is this blueprint a correct and complete translation of the `Problem Description`'s rules?
-   **Verdict**: State your verdict: **"Blueprint is CORRECT"** or **"Blueprint is FLAWED"**. If flawed, explain the error.

**Section 2: Audit of the 'Simulation'**
-   **Claim from Previous Analysis**: I will re-state the final simulated output claimed in the `PREVIOUS_RECHECK`.
-   **Cross-Examination (The Core of Your Work)**: I will now perform a **new, independent, step-by-step 'On-Paper' simulation** of the blueprint from the previous analysis, using the most complex `SAMPLE_IO`. **I must write down the result of EVERY single logical comparison.**
    *(This is a purely abstract example of the required thinking):
    ` - Tracing value_1:`
    `   - Check 1: Is value_1(70) >= 90? No.`
    `   - Check 2: Is value_1(70) > 80? Yes.`
    `   - Check 3: Is value_1(70) > 70.0? **NO**!!!.`
    `   - Check 4: Is value_1(70) > 60.0? **YES**!!!.`
    `   - Concluded Category for value_1: '60<value_1 <70.0'.`*
-   **Verdict**: Compare your new, meticulous simulation result with the result claimed in the `PREVIOUS_RECHECK`. State your verdict: **"The original simulation was MATHEMATICALLY CORRECT"** or **"The original simulation contained CALCULATION ERRORS"**.

**Section 3: Final Corrected Blueprint**
-   Based on the verdicts from the audits above, present the **final, 100% correct, and validated** implementation blueprint in pseudocode. If the original was correct, re-state it. If it was flawed, you must provide the corrected version here.
</RECHECK>

<POINTS>
**Here, you will provide the final, corrected findings.**
Based **ONLY** on your **Final Corrected Blueprint** from Section 3 of your `<RECHECK>`, formulate the final, correct `POINTS` analysis in the standard JSON format.
</POINTS>
"""

    return [
        {
            "role": "system",
            "content": "You are a Cross-Examiner AI. Your sole purpose is to ruthlessly audit a previous analysis for factual, logical, and mathematical errors. You are skeptical by default and trust only your own, newly performed calculations."
        },
        {
            "role": "user",
            "content": user_content
        }
    ] 