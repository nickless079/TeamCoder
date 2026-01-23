from typing import Dict, Any, List

def get_system_prompt() -> str:
    """
    Get system prompt for the code generation agent
    
    Returns:
        System prompt
    """
    return """You are a senior and disciplined Code Implementation Engineer. Your task is to precisely and faithfully translate a given algorithmic blueprint into high-quality, clean, and robust code. You must justify every block of code you write.
"""

def get_generate_code_prompt(problem_description: str, test_cases: Dict[str, Any], technical_plan: Dict[str, Any], language: str, problem_sample_io: str, attention_analysis: Dict[str, Any] = None) -> str:
    """
    Get code generation prompt
    
    Args:
        problem_description: Problem description
        test_cases: Test cases
        technical_plan: Technical plan
        language: Programming language
        problem_sample_io: Sample input/output examples
        
    Returns:
        Code generation prompt
    """
    prompt = f"""  
Translate the Final Blueprint into Production-Ready Code, Step-by-Step

## 1. The Blueprint (Your Primary Directive)
This is the algorithm from the Solution Architect. Your primary task is to translate this blueprint into clean, executable Python3 code.
<TECHNICAL_PLAN>
{technical_plan}
</TECHNICAL_PLAN>

## 2. The Ground Truth (Your Core Requirements)
This defines the problem and any provided helper functions.
<THE_SUPREME_LAW>
{problem_description}
</THE_SUPREME_LAW>

## 3. The Analyst's Notes (Your Quality Mandate)
This contains the critical failure points you must avoid. This is your guide for resolving any ambiguities in the blueprint.
<ATTENTION_ANALYSIS>
{attention_analysis}
</ATTENTION_ANALYSIS>

Your Mission: Faithfully translate the <TECHNICAL_PLAN> into robust code that avoids the 'Fatal Traps' in <ATTENTION_ANALYSIS>. If the plan and traps conflict, prioritize avoiding the traps.

Output Format:
You MUST respond with a sequence of <THOUGHT> and <CODE_BLOCK> pairs for each step in the blueprint, followed by a final <INFO> block.

- <THOUGHT>: For each step, copy the blueprint text. Then, explain your implementation plan, its correctness, and how it avoids relevant traps.
- <CODE_BLOCK>: Provide ONLY the Python3 code for that single step.

START OF YOUR RESPONSE

<THOUGHT>
**Final Assembly**: I have now translated all steps of the blueprint, ensuring each part is robust against the identified fatal traps. I will now assemble all the `<CODE_BLOCK>` parts, including any necessary helper functions from `<THE_SUPREME_LAW>`, into the final, complete code.
</THOUGHT>
<INFO>
## The final, complete, and runnable Python3 code.
## This code is the logical assembly of all the preceding code blocks.
## It includes all necessary helper functions.
## The function signature, especially the return type, MUST EXACTLY match what is required in <THE_SUPREME_LAW>.
[Your final assembled code here,not use any ```python or ``` signs]
</INFO>

"""
    return prompt

def get_messages(problem_description: str, test_cases: Dict[str, Any], technical_plan: Dict[str, Any], language: str, problem_sample_io: str = "", attention_analysis: Dict[str, Any] = None) -> List[Dict[str, str]]:
    """
    Get complete message list for code generation
    
    Args:
        problem_description: Problem description
        test_cases: Test cases
        technical_plan: Technical plan
        language: Programming language
        problem_sample_io: Sample input/output examples
        
    Returns:
        Message list
    """
    return [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": get_generate_code_prompt_1(problem_description, test_cases, technical_plan, language, problem_sample_io, attention_analysis)}
    ] 

def get_fix_code_prompt(code: str, debug_feedback: Dict[str, Any], problem_description: str = "", language: str = "Python3") -> str:
    """
    Get prompt for fixing code based on debug feedback
    
    Args:
        code: Original code with errors
        debug_feedback: Debug feedback containing error information
        problem_description: Problem description for context
        language: Programming language
        
    Returns:
        Code fixing prompt
    """
    error_info = ""
    if not debug_feedback["success"]:
        error_type = debug_feedback.get('error_type', 'Unknown')
        error_message = debug_feedback.get('error', 'No specific error message')
        feedback = debug_feedback.get('feedback', '')
        
        # Add failed test details if available
        failed_tests_info = ""
        if 'failed_tests' in debug_feedback and debug_feedback['failed_tests']:
            failed_tests_info = "\n## Failed Tests\n"
            for i, test in enumerate(debug_feedback['failed_tests']):
                failed_tests_info += f"### Test {i+1}\n"
                failed_tests_info += f"Assertion: `{test['test']}`\n"
                failed_tests_info += f"Error: ```\n{test['error']}\n```\n"
        
        # Add generated test results if available
        generated_tests_info = ""
        if 'generated_test_results' in debug_feedback and debug_feedback['generated_test_results']:
            test_output = debug_feedback['generated_test_results'].get('output', '')
            test_error = debug_feedback['generated_test_results'].get('error', '')
            
            if test_output or test_error:
                generated_tests_info = "\n## Generated Test Results\n"
                if test_output:
                    generated_tests_info += f"Output:\n```\n{test_output}\n```\n"
                if test_error:
                    generated_tests_info += f"Errors:\n```\n{test_error}\n```\n"
        
        error_info = f"""
## Error Information
Error Type: {error_type}

Error Message:
```
{error_message}
```

Feedback: {feedback}
{failed_tests_info}
{generated_tests_info}
"""

    prompt = f"""# Code Fixing

Re-read the Technical Plan in this session. Identify any missing details, edge cases, or constraints not fully considered. Then refine the implementation to satisfy ALL requirements.

IMPORTANT: The previously generated code is incorrect because it fails the test cases (assert statements). You must fix it.

Here are the current issues and signals:
{error_info}

Before writing the final code, first evaluate whether the code you are about to generate will pass the previously failed test case(s) (the assert statements). If your reasoning indicates it still fails, refine the approach and re-evaluate until it will pass.

Additionally, the Problem Description may define helper functions, required signatures, or pre-declared code. Before returning, re-check and include all such helpers exactly as required (do not rename or omit).

IMPORTANT: Your code will be immediately executed after submission. If your code fails ANY sample I/O or ANY test case again, you will be penalized. Ensure your solution is correct before submitting.

Return your fixed code in the following format, with no additional text or explanations:

<EVALUATION>
Simulate step by step against the failed assert(s) and explain succinctly why the new code will pass them. If not, adjust and re-evaluate until it will pass.
</EVALUATION>
<INFO>
your fixed code here only, not any test cases(eg. assert) or other content
</INFO>
"""
    return prompt

def get_fix_messages(code: str, debug_feedback: Dict[str, Any], problem_description: str = "", language: str = "Python3") -> List[Dict[str, str]]:
    """
    Get complete message list for code fixing
    
    Args:
        code: Original code with errors
        debug_feedback: Debug feedback containing error information
        problem_description: Problem description for context
        language: Programming language
        
    Returns:
        Message list
    """
    return [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": get_fix_code_prompt(code, debug_feedback, problem_description, language)}
    ]

def get_generate_code_prompt_1(problem_description: str, test_cases: Dict[str, Any], technical_plan: Dict[str, Any], language: str, problem_sample_io: str, attention_analysis: Dict[str, Any] = None) -> str:
    """
    Get code generation prompt based only on Attention Analysis.
    
    Args:
        problem_description: Problem description
        test_cases: Test cases (ignored, but kept for signature consistency)
        technical_plan: Technical plan (ignored)
        language: Programming language
        problem_sample_io: Sample input/output examples
        attention_analysis: The failure analysis which becomes the primary directive.
        
    Returns:
        Code generation prompt
    """
    prompt = f"""  
### ROLE & MISSION
You are a Principal Software Engineer. Your mission is to write production-ready Python3 code. You must critically evaluate all provided information to create the most robust and correct solution possible, avoiding subtle bugs and edge cases.

### 1. The Ground Truth (Core Requirements)
This defines the problem, its constraints, and any provided helper functions. Your code MUST adhere to this specification perfectly.
<THE_SUPREME_LAW>
{problem_description}
</THE_SUPREME_LAW>

### 2. Preliminary Failure Analysis (A Guide, Not Gospel)
This contains an initial analysis of potential failure points. Your primary task is to critically review this analysis, correct it if necessary, and then write code that avoids all **true** fatal traps.
<PRELIMINARY_ANALYSIS>
{attention_analysis}
</PRELIMINARY_ANALYSIS>

---

### EXECUTION PROTOCOL & OUTPUT FORMAT
You MUST produce your response by completing the following sequence of structured thought blocks, followed by the final code block.

**STEP 1: Structured Thinking**
You must fill out the following three blocks in order.

<RULE_SYNTHESIS_AND_CRITIQUE>
1.  **Rule Synthesis:** First, you MUST synthesize and list the **complete** set of grading rules from `<THE_SUPREME_LAW>` in a clear, unambiguous format (e.g., "Rule 1: If GPA == 4.0, Grade is A+"; "Rule 2: If GPA > 3.7, Grade is A"). This list of synthesized rules is now your foundational truth.
2.  **Critique:** Second, critically review the `<PRELIMINARY_ANALYSIS>` against the rules you just synthesized. Is the analysis factually correct? Does it miss any crucial details or traps that become obvious from your synthesized rules? Quote any part you find incorrect and provide a correction.
</RULE_SYNTHESIS_AND_CRITIQUE>

<PLAN_DECOMPOSITION>
Based on your synthesized rules from the previous step, decompose your implementation plan into two distinct parts:
A. **The General Case:** Describe the logic for handling the rules based on inequalities (e.g., `>`).
B. **Edge Cases & Exceptions:** Explicitly list **all** rules based on **exact equality** (e.g., `==`) and state precisely how your code will handle them.
</PLAN_DECOMPOSITION>

<CODE_JUSTIFICATION>
Justify the robustness of your complete plan. Specifically, explain how your proposed combination of general and edge-case logic will successfully implement your synthesized rules and avoid every true fatal trap.
</CODE_JUSTIFICATION>

**STEP 2: The Final Code (<INFO>)**
Following and consider your multi-stage blueprint, provide the final, complete, and runnable Python3 code inside a single pair of `<INFO>` tags.

---
### REQUIRED OUTPUT STRUCTURE

<RULE_SYNTHESIS_AND_CRITIQUE>
...
</RULE_SYNTHESIS_AND_CRITIQUE>
<PLAN_DECOMPOSITION>
...
</PLAN_DECOMPOSITION>
<CODE_JUSTIFICATION>
...
</CODE_JUSTIFICATION>
<INFO>
... Your final, complete Python code ...
</INFO>

---
START OF YOUR RESPONSE
"""
    return prompt

def get_messages_1(problem_description: str, test_cases: Dict[str, Any], technical_plan: Dict[str, Any], language: str, problem_sample_io: str = "", attention_analysis: Dict[str, Any] = None) -> List[Dict[str, str]]:
    """
    Get complete message list for code generation based on attention analysis.
    
    Args:
        problem_description: Problem description
        test_cases: Test cases
        technical_plan: Technical plan (ignored)
        language: Programming language
        problem_sample_io: Sample input/output examples
        attention_analysis: The failure analysis.
        
    Returns:
        Message list
    """
    return [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": get_generate_code_prompt_1(problem_description, test_cases, technical_plan, language, problem_sample_io, attention_analysis)}
    ]