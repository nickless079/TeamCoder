from typing import Dict, Any, List

def get_system_prompt() -> str:
    """
    Get system prompt for the code generation agent
    
    Returns:
        System prompt
    """
    return """You are a senior Code Implementation Engineer.When you write the code,please slowly and be cautious.The key principle is that the problem description is always wright. But when the problem description is ambiguous, you should refer to the sample_io to find the correct expand requirements; if the problem definition is very clear, then the problem description shall prevail.
    """

def get_generate_code_prompt(problem_description: str, test_cases: Dict[str, Any]) -> str:
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
### ROLE
Critical & Robust Programmer (with a Systems Analyst Mindset)

### GOAL
try your best to complement the problem
### METHOD
carefully read the problem description find the true problem according to **the sample_io**,then think about what is importance you think

### INPUTS
-   `problem_description`:
{problem_description}
-   `sample_io`:
{test_cases}

### OUTPUT FORMAT
<STEP>
according to the METHOD part ,write the brief steps
</STEP>

```python
Your complete Python code here
```

"""
    #,and don't use from __future__ import annotations
    return prompt
'''
### ATTENTION
1.If the sampleIO less than or equal to 1,well then it's hardest,not simple.
2.You always easily pass the sampleio ,but not pass the final examination. So in the step block ,you must carefully treat every problem and you must analysis the problem although it appears quite simple first.
3.Read the below examples to learn how to analysis problem to aviod false pass.
4.**Strictly follow the problem_description**.
Here are some examples for you to use as reference templates for your analysis:
1. **Use only the problem’s formal definition of “sentence” and “starts with the word I”; do not treat characters, whitespace('I '), or punctuation heuristically, and do not assume that stripped or concatenated characters preserve sentence semantics.**
2. Each well (each row of the grid) must be emptied independently; bucket usage counts are computed per row and then summed, and you must not pool water across different wells.
3. When determining whether a number is the product of three prime numbers, one incorrectly assumes that the three primes must be distinct, whereas the problem imposes no restrictions on repetition.
4. For problems involving global optimality (largest, maximum, minimum, last... occurrence), the local judgment strategy of "returning immediately upon first satisfaction" is prohibited, should return the **(largest index one)** result.
5. When dealing with digit-related problems of positive integers (e.g., counting even/odd digits of an integer, counting n-digit positive integers starting/ending with 1), one either incorrectly ignores the edge case of input 0 (treating 0 as having zero even digits) or misinterprets the rule of "n-digit positive integers" (allowing leading zeros when calculating numbers ending with 1), whereas the problem specification requires that 0 is counted as an even digit for single-digit scenarios, and the first digit of n-digit positive integers (n≥2) must be in [1,9] (excluding 0), with consistent adherence to the mathematical definition of positive integers across all digit-related logic.
6. the sample problem say that matches a string that has an 'a' followed by one or more 'b's. we should follow this ,do not thinking more,like matching entire string,the problem don't say this.But not every char type problem need substring,**maybe is full string**
......
### FORSIGHT AND SLOW
What's the FS,F is forsight,S is slow.When solving problems, you always rely on the most straightforward thinking — yet this is often the most error-prone. That’s why we need to adopt a forward-thinking mindset and practice slow thinking.
Think one step ahead;
there are 3 example:
1.description:Write a python function to count the upper case characters in a given string.
input:'PYthon'
output: 1
the FS : if we straight thinking,then the count is 2,but now is 1,so in the char situation,the first char usually upper,so the result is 1(the 'Y',not counting the 'P')
2.description:Write a function to check for the number of jumps required of given length to reach a point of form (d, 0) from origin in a 2d plane.
input:((3, 4), 11)
output:3.5
the FS: we saw the output is float,so wo could think that use the 2 difference steps to sum to 11,so the one is 3*3+0.5*4=11 so the result is 3+0.5=3.5
3.decription:Write a function to replace whitespaces with an underscore and vice versa in a given string.
input:'a b c'
output:'a_b_c'
the FS:if we straght thinking,so we jsut attention replace the whitespace,but the 'vice versa' also import,we are easy to forget the '_' to ' '
......

###IMPORTANCE
1.Learn how to analyze examples, rather than applying the same approach whenever you encounter a similar problem.

### ROLE
Critical & Robust Programmer (with a Systems Analyst Mindset)

### GOAL
try your best to complement the problem
### METHOD
carefully read the problem_description find true problem according to **the sample_io**, then think about what is importance you think

### INPUTS
-   `problem_description`:
{problem_description}
-   `sample_io`:
{test_cases}

### OUTPUT FORMAT
<FS>
follow the ### FORSIGHT AND SLOW and ###IMPORTANCE,by the way,do not modify the topic out of thin air, do not add new topics
</FS>
<STEP>
according to your METHOD,the FS and ATTENTION part, write the brief steps.
</STEP>

```python
Your complete Python code here 
```
'''
'''
### ROLE
Critical & Robust Programmer (with a Systems Analyst Mindset)

### GOAL
try your best to complement the problem
### METHOD
carefully read the problem_description find true problem according to the sample_io ,then think about what is importance you think

### INPUTS
-   `problem_description`:
{problem_description}
-   `sample_io`:
{test_cases}

### OUTPUT FORMAT
<STEP>
according to your METHOD part ,write the brief steps
</STEP>
<INFO>
```python
Your complete Python code here
```
</INFO>
'''

'''
### ATTENTION
1.If there is no sampleIO,well then it's hardest,not simple.
2.You always easily pass the sampleio ,but not pass the final examination. So in the step block ,you must carefully treat every problem and you must analysis the problem although it appears quite simple first.
Here are some examples for you to use as reference templates for your analysis:
1. **Use only the problem’s formal definition of “sentence” and “starts with the word I”; do not treat characters, whitespace('I '), or punctuation heuristically, and do not assume that stripped or concatenated characters preserve sentence semantics.**
2. Each well (each row of the grid) must be emptied independently; bucket usage counts are computed per row and then summed, and you must not pool water across different wells.
3. When determining whether a number is the product of three prime numbers, one incorrectly assumes that the three primes must be distinct, whereas the problem imposes no restrictions on repetition.
4. For problems involving global optimality (largest, maximum, minimum, last... occurrence), the local judgment strategy of "returning immediately upon first satisfaction" is prohibited, should return the **(largest index one)** result.
5. When dealing with digit-related problems of positive integers (e.g., counting even/odd digits of an integer, counting n-digit positive integers starting/ending with 1), one either incorrectly ignores the edge case of input 0 (treating 0 as having zero even digits) or misinterprets the rule of "n-digit positive integers" (allowing leading zeros when calculating numbers ending with 1), whereas the problem specification requires that 0 is counted as an even digit for single-digit scenarios, and the first digit of n-digit positive integers (n≥2) must be in [1,9] (excluding 0), with consistent adherence to the mathematical definition of positive integers across all digit-related logic.
......

'''


def get_messages(problem_description: str, test_cases: Dict[str, Any], technical_plan: Dict[str, Any], language: str, problem_sample_io: str = "", attention_analysis: Dict[str, Any] = None,error_code: str = None, error_info: str = None) -> List[Dict[str, str]]:
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
        #{"role": "system", "content": """You are a senior and disciplined Code Implementation Engineer. Examine the preliminary analysis dialectically, and solve problems based on all available information."""},
        {"role": "user", "content": get_generate_code_prompt_1(problem_description, test_cases, technical_plan, language, problem_sample_io, attention_analysis,error_code,error_info)}
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

def get_generate_code_prompt_1(problem_description: str, test_cases: Dict[str, Any], technical_plan: Dict[str, Any], language: str, problem_sample_io: str, attention_analysis: Dict[str, Any] = None,error_code: str = None, error_info: str = None) -> str:
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
    
    # rules = attention_analysis['fatal_points']['Rules'] 
    # traps_data = attention_analysis['fatal_points'].get('Traps', '{}') 

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

### REQUIRED OUTPUT STRUCTURE

```python
Your final, complete python3 code
```
"""
    return prompt
'''
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
### EXECUTION PROTOCOL

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
... Your final, complete Python code...
</INFO>

---
START OF YOUR RESPONSE
'''
'''
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

### REQUIRED OUTPUT STRUCTURE

<INFO>
... Your final, complete Python code...
</INFO>

---
START OF YOUR RESPONSE
'''


def get_messages_1(problem_description: str, test_cases: Dict[str, Any]) -> List[Dict[str, str]]:
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
        {"role": "user", "content": get_generate_code_prompt(problem_description, test_cases)}
    ]