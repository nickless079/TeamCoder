"""
Comprehensive Test Agent prompt templates
"""


def get_system_prompt() -> str:
    """
    Get system prompt for the Comprehensive Test Agent
    
    Returns:
        System prompt text
    """
    return """You are a QA (Quality Assurance) Engineer. Your primary directive is to create a comprehensive, executable test suite by critically validating an analyst's report against the problem's ground truth. You trust the problem description above all else.
"""


def get_user_prompt(problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None, sample_io: list = None, attention_analysis: dict = None) -> str:
    """
    Get user prompt for test case generation (minimal format)
    """


    prompt = f"""
### **ROLE AND GOAL**

You are **ProposerAgent**, a **Grandmaster-level Red Team** analyst. Your sole function is to devise the **single, most insightful and devastating adversarial input case** that is **fundamentally different** from the provided Sample I/O.

Your goal is to **break the assumptions** established by the Sample I/O. You must find the "Golden Case" that tests a completely different aspect of the problem's logic.

---

### **INPUT FOR PROPOSAL**

1. **The Supreme Law**: The problem's description and rules.
{problem_description}
    
2. **The Sample I/O**: The existing examples you **must deviate from**.
{sample_io}

---

### **YOUR TASK & OUTPUT FORMAT**

You must first transparently document your thought process, and then provide that single, final input.

#### **Part 1: The Hunt for the Golden Case (Explore, Deviate & Elevate Protocol)**

<ADVERSARIAL_THOUGHTS>  
[You must document your reasoning by following this strict, three-step protocol.

**1. Analyze the Sample I/O's Blind Spot**:

- First, analyze the provided Sample I/O to find its **blind spot** (the logical path it fails to cover).
    

**2. Formulate a Deviant Strategy**:

- Based on the Blind Spot, formulate a strategy to test the **untested path**.
    

**3. Devise the Golden Case (The "Non-Triviality" Rule)**:

- Based on your deviant strategy, you must now devise the single, simplest possible input that exploits the blind spot.
    
- **CRITICAL CONSTRAINT: Your "Golden Case" MUST be "non-trivial".** This means you should **AVOID** universally common, simple edge cases like 0, 1, "", [] **UNLESS** they are the only possible way to test the identified blind spot.
    
- Your primary goal is to find an input that is **structurally interesting** and reveals a deeper flaw in a naive algorithm's logic, not just its handling of empty inputs. Justify its "Golden" and "Non-Trivial" status.
    
    - **A-Grade Example (Generalized & Non-Cheating)**:
        
        > "**Deviant Strategy**: My strategy is to directly test the logic path for negative numbers.  
        > **Golden Case Input**: A list containing a mix of positive and negative numbers, like [1, 2, -1, -2].  
        > **Golden Status**: This input is devastatingly effective. It is **non-trivial** because it tests the interaction between different domains (positive and negative). It is 'Golden' because it will instantly reveal if a developer made lazy assumptions based only on the positive-number examples, forcing them to consider a more general, robust state management."  
        > ]  
        > </ADVERSARIAL_THOUGHTS>

#### **Part 2: The Final Golden Input**

<PROPOSED_INPUT>  
[Provide your single, final, proposed input. Provide only the raw input value, not the function call.]  
[attention the input type should be consistent with the problem description, e.g., if the problem expects a int, provide a int,not string such as The input is 23,not “2”]
</PROPOSED_INPUT>
"""
    
    return prompt


def get_messages(task_name:str, problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None, sample_io: list = None, attention_analysis: dict = None,assertion : str =None) -> list:
    """
    Get complete message list for test case generation
    """
    
    if task_name == "generate_comprehensive_tests":
        return [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": get_user_prompt(problem_description, language, function_signature, function_name, sample_io, attention_analysis)}
        ]
    else :
        return [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": get_evaluate_single_test_prompt(problem_description, assertion,sample_io,attention_analysis=attention_analysis, language=language)}
        ]


def get_evaluate_single_test_prompt(problem_description: str, assertion: str,sample_io: list = [], description: str = "", language: str = "Python", attention_analysis: dict = None) -> str:
    """
    Build prompt for evaluating and minimally fixing a single test assertion.
    """
    return f"""### **ROLE AND GOAL**

You are **SolverAgent**, a **Blue Team** validation unit. You are a meticulous, high-precision execution engine. You have been given a problem definition and a single input case.

Your sole function is to provide the **single, unambiguously correct output** for the given input, based on a strict, literal interpretation of the Supreme Law. You do not guess; you calculate.

---

### **INPUTS FOR SOLVING**

1. **The Supreme Law**: The problem's description and rules.
{problem_description}
    
1.1 **Sample I/O (For Reference)**: Examples of valid inputs and their expected outputs.
{sample_io if sample_io else 'N/A'}

1.2 **The Analyst's Report (For Context)**: An analyst's report highlighting potential pitfalls and edge cases.
{attention_analysis.get("attention_analysis", "") if attention_analysis else 'N/A'}
2. **The Proposed Input**: The single input case you must solve.
{assertion}    

---

### **YOUR TASK & OUTPUT FORMAT**

You MUST provide your response in the following two-tag format. Your output must be the two tags, complete Python assert statement.
<THOUGHT>
How to solve the input case, step-by-step reasoning.
</THOUGHT>
<SOLVED_EXAMPLE>  
[assert function_name(input) == expected_output]  
</SOLVED_EXAMPLE>

---
"""


def get_evaluate_single_test_messages(problem_description: str, assertion: str, description: str = "", language: str = "Python") -> list:
    return [
        {"role": "system", "content": "You are a precise Test Case Validator. Be strict and minimal."},
        {"role": "user", "content": get_evaluate_single_test_prompt(problem_description, assertion, description, language)}
    ]


def get_scenario_generation_prompt(problem_description: str, attention_analysis: str, problem_sample_io: list = None) -> str:
    """
    Get prompt for generating test scenarios based on analyst's report
    """
    sample_io_text = ""
    if problem_sample_io:
        sample_io_text = f"\n\n## 3. Sample I/O (For Reference)\n"
        for i, sample in enumerate(problem_sample_io):
            sample_io_text += f"Sample {i+1}: {sample}\n"
    
    return f"""# Generate Test Scenarios from Analysis

## 1. The Analyst's Report (Your Inspiration)
<FATAL_POINT_ANALYSIS>
{attention_analysis}
</FATAL_POINT_ANALYSIS>

## 2. The Problem Definition
{problem_description}
## 3. Sample I/O (For Reference)
{sample_io_text}

## Your Mission: Design a Comprehensive List of Test Scenarios.

Based on the analyst's report, generate a comprehensive list of test scenarios. For each scenario, you must provide the function `input` and a `description` of what it is testing. **You MUST NOT calculate or provide the expected `output`.**

## Output (exactly ONE JSON Block)(choose the most important test scenarios ,and the number of test scenarios should be less than 10)
```json
{{
  "test_scenarios": [
    {{
      "input": "[function_name]([args...])",
      "description": "Validates: [e.g., Sample I/O; Primary Fatal Point - checks for a naive implementation; Edge Case - empty input]"
    }}
  ]
}}
```"""


def get_scenario_generation_messages(problem_description: str, attention_analysis: str, problem_sample_io: list = None) -> list:
    """
    Get complete message list for test scenario generation
    """
    return [
        {
            "role": "system",
            "content": "You are a QA (Quality Assurance) Scenario Designer. Your mission is to read an analyst's report and generate a comprehensive list of test *scenarios* that must be covered. You focus on 'what' to test, not 'what the answer should be'."
        },
        {
            "role": "user",
            "content": get_scenario_generation_prompt(problem_description, attention_analysis, problem_sample_io)
        }
    ]