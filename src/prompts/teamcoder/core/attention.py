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
    elif task_type == "generate_blueprint":
        return _get_generate_blueprint_messages(**kwargs)
    elif task_type == "analyze_traps":
        return _get_analyze_traps_messages(**kwargs)
    else:
        raise ValueError(f"不支持的任务类型: {task_type}")

def _get_find_fatal_points_messages(
    problem_description: str,
    sample_io: List[str] = None,
    error_info: List[str] = None,
    error_code: str = "",
    **kwargs
) -> List[Dict[str, str]]:
    """
    获取找出最致命关键点任务的消息
    """
    sample_io_text = ""
    if sample_io:
        sample_io_text = f"\n" + "\n".join(f"{io}" for io in sample_io)
    
    user_content = f"""
### ROLE AND GOAL
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

**Step 3: The 'Fatal Traps' Distillation (Semantic vs Logical Traps)**

* **This is your final and most important step.** You will now translate each "Robust Principle" from Step 2 into one or more **Fatal Traps**.

* **Trap Types:**

  * **Semantic Trap:** Occurs when the implementation fails to adhere to the *actual meaning* or *hidden semantic constraints* of the problem. This includes misidentifying the semantic object, domain, or scope of the solution.
  * **Logical / Operational Trap:** Occurs when the semantic understanding is correct, but the implementation fails in its operations, such as boundary handling, ordering, duplication, or other correctness rules.

* **Distillation Instructions:**

  1. For **each Robust Principle**, identify whether violating it leads to a **Semantic Trap** or a **Logical/Operational Trap**.
  2. Provide a clear, concise description of the trap, including:

     * **What** the trap is (specific failure).
     * **Why** it occurs (link to the violated principle).
     * **Consequence** (impact on correctness or output).
  3. List **all identified traps** separately under their respective categories; do **not** rank them by priority.

* **Abstract Example:**

  * **Semantic Trap:** “Misinterpreting the problem as 'return even digits of all numbers in the range' instead of 'only digits 0,2,4,6,8 are valid' leads to outputs that violate the specification.”
  * **Logical/Operational Trap:** “Within the correct set of digits, failing to sort the output ascendingly produces outputs that are semantically valid but do not respect the ordering rule.”


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
    
    user_content = f"""
### **Final, Corrected, and Simplified English Prompt**

### ROLE & MISSION
You are a "Specification Detective." Your mission is to deduce the true requirements of a problem by analyzing a flawed description and a failed code attempt against a correct I/O example. You will then output a new, corrected problem description.

### 1. Surface Description
This is the initial description, which is likely flawed or incomplete.
<SURFACE_DESCRIPTION>
{problem_description}
</SURFACE_DESCRIPTION>

### 2. Failed Implementation
This is a literal implementation of the `<SURFACE_DESCRIPTION>`, which fails the ground truth test.
<FAILED_IMPLEMENTATION>
{content}
</FAILED_IMPLEMENTATION>

### 3. Ground Truth I/O
This is the **single source of truth**.
<GROUND_TRUTH_IO>
{sample_io_text}
</GROUND_TRUTH_IO>

---

### EXECUTION PROTOCOL
You MUST produce your response by completing the following sequence.

**STEP 1: Structured Thinking**

<ANALYSIS_AND_DEDUCTION>
1.  **Conflict:** State in one sentence why the `<SURFACE_DESCRIPTION>` is wrong, as proven by the `<GROUND_TRUTH_IO>`.
2.  **Deduced Rule:** State the correct, hidden rule you have deduced by reverse-engineering the `<GROUND_TRUTH_IO>`.
</ANALYSIS_AND_DEDUCTION>

**STEP 2: The Final Output**

<CORRECTED_DESCRIPTION>
Provide the rewritten, accurate problem description as **plain text**. This text should clearly explain the "Deduced Rule" and be precise enough for a developer to implement the solution correctly.
</CORRECTED_DESCRIPTION>

---
### REQUIRED OUTPUT STRUCTURE
<CORRECTED_DESCRIPTION>
... Your final, rewritten problem description as plain text ...
</CORRECTED_DESCRIPTION>

"""

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

def _get_generate_blueprint_messages(
    problem_description: str,
    sample_io: List[str] = None,
    error_code: str = "",
    error_info: List[str] = None,
    trap: str = None,
    **kwargs
) -> List[Dict[str, str]]:
    """
    Gets messages for the Blueprint Generator agent.
    """
    sample_io_text = ""
    if sample_io:
        sample_io_text = "\\n".join(f"{io}" for io in sample_io)

    user_content = f"""
### ROLE
Specification Augmentation Analyst (with a focus on proactive prevention)

### GOAL
To augment the `problem_description` by incorporating the lesson learned from the identified `fatal_trap`. Your goal is to create a new, unambiguous specification that proactively prevents this trap.

### CORE PRINCIPLE
-   **The Trap is the Problem, The Rule is the Solution**: The provided `fatal_trap` precisely defines the problem. The `supplementary_rule` you formulate MUST be the direct solution or logical inverse of that problem.
-   **From Diagnosis to Prescription**: Your task is to convert the trap's diagnosis of what went wrong into a clear prescription of what must be done right.

### INPUTS
-   `problem_description`: **(The Original Text)** The initial, ambiguous specification that needs enhancement.
{problem_description}
-   `correct_sample_io`: **(The Ground Truth)** The authoritative example of correct behavior.
{sample_io_text}
-   `fatal_trap`: **(The Diagnosis)** A precise, evidence-based definition of the flawed logic that must be prevented. This is your primary input for analysis.
{trap}
### ANALYTICAL PROCESS
1.  **Deconstruct the Trap**: Analyze the `trap_statement` from the `fatal_trap` input to fully understand the core misinterpretation.
2.  **Formulate the Antidote**: Formulate the `supplementary_rule` as the direct "antidote" to the trap. If the trap is "ignoring X", the rule is "you must handle X".
3.  **Synthesize the Final Specification**: Combine the original description with this new, preventative rule to create the final, trap-proof `summary-rule`.

### AUGMENTED SPECIFICATION (OUTPUT)

{{
  "verification": [
    {{
      "sample": "State the correct sample being analyzed.",
      "observation": "Briefly explain the core ambiguity in the `problem_description` that the `fatal_trap` successfully exploited.",
      "verification": "Explain how applying the `supplementary_rule` (the trap's antidote) correctly leads to the result seen in `correct_sample_io`."
    }}
  ],
  "supplementary_rule": "State the concise rule that is the direct logical inverse of the provided `fatal_trap`. This rule's purpose is to make the trap impossible to fall into.",
  "summary-rule": "Combine the initial description and the supplementary rule into the final, unambiguous specification that is now immune to the identified trap."
}}

"""
    return [
        {
            "role": "user",
            "content": user_content
        }
    ]

def _get_analyze_traps_messages(
    problem_blueprint_json: str,
    problem_description: str,
    sample_io: List[str] = None,
    error_code: str = "",
    error_info: List[str] = None,
    **kwargs
) -> List[Dict[str, str]]:
    """
    Gets messages for the Trap Analyst agent.
    """
    sample_io_text = ""
    if sample_io:
        sample_io_text = "\\n".join(f"{io}" for io in sample_io)

    user_content = f"""

### ROLE
Fatal Trap Analyst (with a Root Cause Analysis Mindset).

### GOAL
To define the Fatal Trap that results from a literal but flawed interpretation of the **misleading `problem_description`**. Your task is to use the provided failure case as evidence to uncover this hidden trap.

### UNBREAKABLE LAWS OF ANALYSIS
1.  **THE `correct_sample_io` IS ABSOLUTE TRUTH**: The `correct_sample_io` is the **single, immutable, non-negotiable ground truth**. It is NEVER wrong. Any analysis that concludes the sample is incorrect is a complete failure of your task. Your entire purpose is to find a logical explanation that makes this sample correct.
2.  **THE `problem_description` IS DELIBERATELY MISLEADING**: Assume the `problem_description` contains a subtle ambiguity or omits a critical piece of context. It is designed to be misinterpreted if read too literally.
3.  **THE `failed_code` IS THE PROOF**: The `failed_code` is the perfect, logical result of a programmer falling for the misleading description. It is the physical evidence of the trap in action.

### INPUTS
-   `problem_description`: **(The Lure)** The initial, misleading text.
{problem_description}
-   `correct_sample_io`: **(The Oracle)** The absolute, correct ground truth.
{sample_io_text}
-   `failed_code`: **(The Exhibit)** A perfect implementation of the flawed interpretation.
{error_code}
-   `failed_output`: **(The Consequence)** The observable result of falling into the trap.
{error_info}
### ANALYTICAL PROCESS
1.  **Isolate the Misinterpretation**: Start from the premise that the `failed_code` is a rational interpretation of the `problem_description`.
2.  **Identify the Contradiction**: Pinpoint exactly why this rational interpretation produces a `failed_output` that contradicts the **absolute truth** of the `correct_sample_io`.
3.  **Define the Trap**: The contradiction you found *is* the trap. Articulate it as the specific, hidden rule that the `problem_description` failed to mention.

### OUTPUT FORMAT
Provide the final trap in the specified minified JSON format.```json
{{
  "Primary_Trap": {{
    "trap_statement": "Describe the core misinterpretation invited by the `problem_description`. This misinterpretation is the Fatal Trap.",
    "violating_logic_example": "Start by quoting the key logic from `failed_code`. Explain that this logic is a perfect implementation of the `problem_description`'s misleading surface-level meaning. Then, show how this directly causes the discrepancy between the `failed_output` and the `correct_sample_io`."
  }}
}}


"""
    return [
        {
            "role": "user",
            "content": user_content
        }
    ]