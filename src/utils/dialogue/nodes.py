"""
调试节点基类和具体实现
"""
from utils.code_slicer import CodeSlicer
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from agents.BaseAgent import BaseAgent
from .types import NodeType, NodeResult, DebugContext, AgentRole
from .quality_gate import QualityGate
from constants.verboseType import *
from utils.grammarcheck import GrammarChecker
from datasets.Dataset import Dataset
# 配置日志
logger = logging.getLogger(__name__)

class DebugNode(ABC):
    """调试节点基类"""
    
    def __init__(self, node_type: NodeType, quality_gate: QualityGate, verbose: int = 1):
        self.node_type = node_type
        self.quality_gate = quality_gate
        self.verbose = verbose
        self.max_turns = 16  # 节点内最大对话轮数
        
    @abstractmethod
    def execute(self, context: DebugContext, agents: Dict[AgentRole, BaseAgent]) -> NodeResult:
        """执行节点逻辑"""
        pass
    
    def _log(self, message: str, level: int = VERBOSE_MINIMAL):
        """日志输出"""
        if self.verbose >= level:
            print(f"[{self.node_type.value}] {message}")

class DiagnosisNode(DebugNode):
    """节点一: 根本原因诊断"""
    
    def __init__(self, quality_gate: QualityGate, verbose: int = 1):
        super().__init__(NodeType.DIAGNOSIS, quality_gate, verbose)
        
    
    def execute(self, context: DebugContext, agents: Dict[AgentRole, BaseAgent]) -> NodeResult:
        """
        执行诊断节点 - 简单两步流程：SimulationAgent → SolutionAgent
        """
        self._log("🎯 开始根本原因诊断...")
        context.timeout = False
        # === 第零步：提取门控 - 从error log中提取expected value ===
        self._log("🔍 启动提取门控 - 从fail log中提取expected value...")
        
        # 调试信息：打印输入的错误日志
        if self.verbose >= 2:
            self._log(f"[DEBUG] 输入到提取门控的错误日志: {context.error_logs[:300]}..." if len(context.error_logs or "") > 300 else f"[DEBUG] 输入到提取门控的错误日志: {context.error_logs}")
       
        if context.is_competive:
            expected_value = self.quality_gate.extract_simulation_value_from_log_com(
                error_logs=context.error_logs
            )
        else:
            expected_value = self.quality_gate.extract_simulation_value_from_log(
                error_logs=context.error_logs
            )            
        
        # 详细调试信息
        if self.verbose >= 2:
            self._log(f"[DEBUG] 提取门控返回值: '{expected_value}'")
            self._log(f"[DEBUG] 返回值类型: {type(expected_value)}")
            self._log(f"[DEBUG] 返回值长度: {len(expected_value) if expected_value else 0}")
        
        if expected_value:
            context.expected_value = expected_value
            self._log(f"✅ 成功提取expected value: {expected_value}")
            
            # 验证JSON格式
            if self.verbose >= 2:
                try:
                    import json
                    parsed = json.loads(expected_value)
                    self._log(f"[DEBUG] JSON解析成功: {parsed}")
                except json.JSONDecodeError as e:
                    self._log(f"[DEBUG] JSON解析失败: {e}")
                    self._log(f"[DEBUG] 有问题的字符串: '{expected_value}'")
        else:
            self._log("⚠️ 未能从fail log中提取到expected value")
        
        solution_agent = agents[AgentRole.SOLUTION_AGENT]
        simulation_agent = agents.get(AgentRole.SIMULATION_AGENT)
        
        # 检查是否有SimulationAgent可用
        enhanced_mode = simulation_agent is not None
        if enhanced_mode:
            self._log("🔬 检测到SimulationAgent，启用增强诊断模式")
        else:
            self._log("📝 使用标准诊断模式（无SimulationAgent）")
        
        # === 第一步：SimulationAgent 模拟分析（如果可用）===
        simulation_response = None
        # if enhanced_mode:
        #     self._log("🔬 SimulationAgent 开始模拟错误代码...")
        #     simulation_prompt = self._build_simulation_agent_diagnosis_prompt(context, None)
        #     simulation_response = simulation_agent._call_model(simulation_prompt, include_history=False)
        #     self._log("✅ SimulationAgent 模拟完成")
            

        max_attempts = 3
        for attempt in range(max_attempts):
            self._log(f"诊断尝试 {attempt + 1}/{max_attempts}")
            
            

            # _,codes = self._format_current_code(context.current_code)
            
    
            
            # for index,code in enumerate(codes):
            #     if index ==0:
            #         slicer = CodeSlicer(code)
            #         logical_blocks = slicer.slice()   
            #         print(logical_blocks) 
            #         # 2. 准备一个列表来存储所有分析结果
            #         reports = []
            #         sinppets_analysis = []
            #         # 3. 循环遍历字典的每一个逻辑块
            #         #    .items() 会同时给你块的名称和对应的代码片段列表
            #         for block_name, code_snippets in logical_blocks.items(): 
            #             # 每一个逻辑块可能包含一个或多个代码片段
            #             if block_name == 'Header & Imports' :
            #                 continue
            #             for code_slice in code_snippets:          
            #                 analysis_prompt = self._build_diagnosis_prompt(context=context,full_code=code,block_name=block_name,code_slice_to_analyze=code_slice,dynamic_instructions=self._get_dynamic_instructions(block_name))
            #                 response = solution_agent._call_model(analysis_prompt, include_history=False)
            #                 response_json=self._parse_and_augment_llm_response(response,code_slice)
            #                 if response_json is None:
            #                     continue
            #                 reports.append(response_json)

            #         # 过滤
            #         for report in reports:
            #             if report.get('verdict') == 'Flawed':
            #                 sinppets_analysis.append(report)
            #         code_analysis_prompt = self._build_solution_analysis_prompt(context,code,sinppets_analysis)
            #         response = solution_agent._call_model(code_analysis_prompt,include_history=False)
            #         #加入分析
            #         context.all_analysis.append(response)
            #         break

            
            # exit()


            # === 第二步：SolutionAgent 分析 ===
            
            self._log("� SolutionAgent 基于模拟结果进行分析...")
            analysis_prompt = self._build_solution_analysis_prompt(context,"none")
            response = solution_agent._call_model(analysis_prompt, include_history=False)
          
            #response = context.all_analysis
            #print(response)
            
            # 直接进入下一阶段，跳过所有验证，使用原始response
            self._log("✅ 诊断完成 - 直接进入下一阶段（使用原始SolutionAgent回复）")
            context.diagnosis_result = {"raw_response": response}  # 保存原始回复
            
            result_output = {
                "diagnosis": {"raw_response": response},  # 返回原始回复内容
                "response": response
            }
            
            if enhanced_mode:
                result_output["simulation_response"] = simulation_response
                result_output["enhanced_mode"] = True
            
            return NodeResult(
                success=True,
                output=result_output,
                next_node=NodeType.BLUEPRINT_DESIGN
            )
        
        return NodeResult(
            success=False,
            error_message="多次尝试后仍无法获得满足质量要求的诊断分析"
        )
    
    def _validate_format(self, response: str, enhanced_mode: bool = False) -> bool:
        """验证响应格式 - 检查三个标签对是否完整存在"""
        if enhanced_mode:
            # 增强模式：使用新的标签格式
            required_tag_pairs = [
                ("FAILURE_LOCATION", "FAILURE_LOCATION"),
                ("FAILURE_ANALYSIS", "FAILURE_ANALYSIS"), 
                ("EXPLORATORY_QUESTION", "EXPLORATORY_QUESTION")
            ]
        else:
            # 标准模式：使用原有的标签格式
            required_tag_pairs = [
                ("COMPUTATIONAL_TRACE", "COMPUTATIONAL_TRACE"),
                ("DEVIATION_STATEMENT", "DEVIATION_STATEMENT"), 
                ("EXPLORATORY_QUESTION", "EXPLORATORY_QUESTION")
            ]
        
        for start_tag, end_tag in required_tag_pairs:
            # 检查开始和结束标签是否都存在
            if f"<{start_tag}>" not in response :
                return False
            
            # 使用正则表达式验证标签对是否能够正确匹配
            pattern = f'<{start_tag}>(.*?)</{end_tag}>'
            if not re.search(pattern, response, re.DOTALL):
                return False
        
        return True
    
    def _build_diagnosis_prompt(self, context: DebugContext) -> List[Dict[str, str]]:
        """构建诊断提示 - 按照精确的显微镜级别设计"""
        
        prompt_content = f"""
### ROLE AND GOAL
You are an expert **Senior Requirements Analyst** and a meticulous **logic detective**. Your mission is to dissect a software problem description, its accompanying examples (`sampleio`), and any related failure data to uncover all ambiguities, hidden rules, and direct conflicts.

Your output will be a concise **Requirement Clarification Memo**. This memo is the **single source of truth** for all subsequent development. Your primary directive is to treat the `sampleio` as undeniable evidence that reveals the true, precise requirements.

---

### **INPUTS FOR YOUR ANALYSIS**

1.  **Problem Description**:
    -   The natural language description of the function's goal.
    `{context.problem_description}`

2.  **Sample I/O (The Ground Truth Evidence)**:
    -   The concrete examples that demonstrate the required behavior.
    `{context.test_cases}`

---

### **YOUR ANALYTICAL PROTOCOL**

You must perform the following three-part analysis to produce the final memo. **Use the `Initial Failure Clue` to guide your investigation.**

**Part 1: Clarify Ambiguous Terminology**
-   Scan the `Problem Description` for common, ambiguous programming-related terms (e.g., "k-th element", "length", "position", "range").
-   Use the `sampleio` as evidence to determine the precise, unambiguous technical meaning of each term.
-   ***Self-Correction Example with a Clue:*** *The `Failure Clue` shows an `AssertionError` where `'0-6: Clearly'` was produced but `'0-7: Clearly'` was expected. This is a powerful clue that the term "position" has a non-standard meaning. The word 'Clearly' has length 7. To get an output of `'0-7'`, the 'end' must be calculated as `start + length`, not the standard `start + length - 1`.*

**Part 2: Identify Hidden Rules in `sampleio`**
-   Meticulously examine the `sampleio` to find non-obvious rules or behaviors that are **not** explicitly stated or are vaguely described in the `Problem Description`.
-   ***Self-Correction Example with a Clue:*** *The `Failure Clue` is about the word 'Clearly' from the input 'Clearly,'. This is a strong hint that a hidden rule is "words must be stripped of trailing punctuation before being processed."*

**Part 3: Identify Conflicts and Ambiguities**
-   Compare the rules you've uncovered in the previous parts against the literal `Problem Description`.
-   Identify any direct contradictions or areas where the description is too vague and your uncovered rules provide the only clear specification.
-   *Example: "Conflict: The description implies standard, order-sensitive tuple counting, but the `sampleio` requires order-agnostic counting. The `sampleio`'s behavior is the correct one."*

---

### **FINAL OUTPUT STRUCTURE**

Your entire response MUST be a single JSON object.

```json
{{
  "clarified_terms": {{
    "string": "string"
  }},

  "clarified_keywords": [
    "string"
  ],
  "has_conflict": "boolean",
  "conflict_resolution": "string"
}}
```

-   **`clarified_terms`**: A dictionary where keys are the ambiguous terms found in the description (e.g., "k-th element", "length") and values are their precise, technically correct interpretations backed by the `sampleio` (e.g., "0-based indexing (k-1)", "mathematical difference (end - start)"). If no ambiguous terms are found, this can be an empty object `{{}}`.

-   **`clarified_keywords`**: A list of short, powerful phrases that summarize the true, clarified requirements of the problem. These should be extracted primarily from your analysis of the `sampleio`. (e.g., `["order-agnostic counting", "sorted tuple keys"]`).

-   **`has_conflict`**: A boolean value. `true` if you found a direct conflict between the description and the `sampleio`, `false` otherwise.

-   **`conflict_resolution`**:
    -   If `has_conflict` is `true`, this field MUST contain a clear, one-sentence directive that resolves the conflict. (e.g., "The counting logic must treat tuples as order-agnostic pairs by normalizing them, as demonstrated by the `sampleio`.").
    -   If `has_conflict` is `false`, this field should be an empty string `""`.
"""

        return [
            {"role": "user", "content": prompt_content}
        ]
    
    def _extract_diagnosis_result(self, response: str, enhanced_mode: bool = False) -> Dict[str, str]:
        """提取诊断结果的各个标签内容"""
        result = {}
        
        if enhanced_mode:
            # 增强模式：使用新的标签格式
            tags = ["FAILURE_LOCATION", "FAILURE_ANALYSIS", "EXPLORATORY_QUESTION"]
        else:
            # 标准模式：使用原有的标签格式
            tags = ["COMPUTATIONAL_TRACE", "DEVIATION_STATEMENT", "EXPLORATORY_QUESTION"]
        
        for tag in tags:
            match = re.search(f'<{tag}>(.*?)</{tag}>', response, re.DOTALL)
            if match:
                result[tag.lower()] = match.group(1).strip()
        
        return result
    
    def _format_test_cases(self, test_cases: List[Any]) -> str:
        """格式化测试用例"""
        if not test_cases:
            return "无测试用例"
        
        formatted = []
        for i, test_case in enumerate(test_cases[:3]):  # 只显示前3个
            # 处理不同的测试用例格式
            if isinstance(test_case, dict):
                assertion = test_case.get("assertion", "")
            elif isinstance(test_case, str):
                assertion = test_case
            else:
                assertion = str(test_case)
            
            if assertion:
                formatted.append(f"{i+1}. {assertion}")
        
        return "\n".join(formatted)
    
    def _format_ground_truth_examples(self, test_cases: List[Any]) -> str:
        """格式化地面真值示例"""
        if not test_cases:
            return "Ground Truth Examples: None provided"
        
        formatted = ["Ground Truth Examples ,just the sampleio:"]
        for i, test_case in enumerate(test_cases[:5]):  # 显示前5个
            # 处理不同的测试用例格式
            if isinstance(test_case, dict):
                assertion = test_case.get("assertion", "")
            elif isinstance(test_case, str):
                assertion = test_case
            else:
                assertion = str(test_case)
            
            if assertion:
                formatted.append(f"  {i+1}. {assertion}")
        
        return "\n".join(formatted)
    
    def _format_current_code(self, current_code):
        """格式化当前代码，支持字符串或列表格式"""
        if current_code is None:
            return "No current code provided"
        
        if isinstance(current_code, list):
            if not current_code:
                return "No current code provided"
            
            # 如果是列表，显示所有历史代码
            formatted_codes = []
            for i, code in enumerate(current_code):
                if i == 0:
                    formatted_codes.append(f"# Latest Code (Current):\n{code}")
                else:
                    formatted_codes.append(f"# Historical Code {i}:\n{code}")
            
            return "\n\n" + "\n\n".join(formatted_codes),formatted_codes
        else:
            formatted_codes = [current_code]
            return 'trans',formatted_codes
    
    def _build_simulation_agent_diagnosis_prompt(self, context: DebugContext, solution_response: Optional[str]) -> List[Dict[str, str]]:
        """构建SimulationAgent在诊断阶段的模拟提示词 - 直接模拟错误代码"""
        
        # 安全地解析expected_value中的JSON数据
        simulation_text = "No simulation values found"
        if hasattr(context, 'expected_value') and context.expected_value and context.expected_value != "No error log provided":
            try:
                import json
                parsed_data = json.loads(context.expected_value)
                simulation_values = [item['simulation_value'] for item in parsed_data]
                simulation_text = '; '.join(simulation_values) if simulation_values else "No simulation values found"
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self._log(f"[NODE_DIAGNOSIS] ⚠️ 解析expected_value时出错: {e}")
                simulation_text = "No simulation values found"
        
        prompt_content = f"""###### ROLE AND GOAL
You are a SimulatorAgent. You are a dispossessed, step-by-step code execution engine. You do not analyze, critique, or judge. Your ONLY job is to simulate the provided code with **maximum granularity** and report the factual results.

### CRITICAL SIMULATION RULE
**Your ONLY source for execution logic is the `Code to Simulate`.** You are strictly forbidden from using any logic from the `Supreme Law`.

### YOUR CORE SIMULATION PROTOCOL: DEEP EVALUATION
**You must break down every line of code into its most basic operations. For any line that contains a function call or a complex expression, you must "unpack" it to show the internal steps. Do not jump to conclusions.**

---
**Example of the Required Granularity and "Unpacking":**

 Consider this code snippet to simulate with an input of score = 90:

 def get_level(score):
     if score > 90:
         return "Good"
     elif score >= 80:
         return "Common"
     else:
         return "Basic"
 --- A BAD, FORBIDDEN trace would be: ---
 90 is not > 90, but it is >= 80, so it returns "Common".
 (This is a lazy summary and is not allowed)
 --- A GOOD, REQUIRED trace for an input of score = 90: ---
 - Calling function `get_level` with `score = 90`.
 - Line `if score > 90:`:
 -   Evaluating condition: `score > 90`.
 -   Substituting variable: `90 > 90`.
 -   The comparison evaluates to **False**.
 -   Skipping the `if` block, proceeding to `elif`.
 - Line `elif score >= 80:`:
 -   Evaluating condition: `score >= 80`.
 -   Substituting variable: `90 >= 80`.
 -   The comparison evaluates to **True**.
 -   Condition is True, entering the `elif` block.
 - Line `return "Common"`:
 -   Function returns the value `"Common"`
---

### CONTEXT
- **Code to Simulate**:
```python
{context.current_code or "No current code provided"}

The Value for simulation:
{simulation_text}
### YOUR TASK
You must manually simulate the `Code to Simulate` following the `DEEP EVALUATION` protocol. Your trace must unpack all function calls and complex expressions. Your entire response must contain exactly two parts as defined below.

---

This is your final, official output based on your pre-computation.

<SIMULATION_REPORT>
    <TRACE>
    [Your detailed, step-by-step trace of the execution,please attention the compare (ed. 3>3.0 is false) and the corrsponse according to the blueprint]
    </TRACE>
    <FINAL_OUTPUT>
    [The final output produced by the code, or the error/crash that occurred.]
    </FINAL_OUTPUT>
</SIMULATION_REPORT>
```"""
        
        return [{"role": "user", "content": prompt_content}]
    
    def _build_solution_analysis_prompt(self, context: DebugContext, simulation_response:str) -> List[Dict[str, str]]:
        """构建SolutionAgent基于模拟结果的分析提示词"""
        
        prompt_content = f"""
### **ROLE AND GOAL**

You are **SolutionAgent**, acting as a **Failure Review Expert**. Your mission is to analyze a failed coding attempt by examining the discrepancy between the **strategy** that was supposed to be followed and the **reality** of the execution failure.

Your ultimate goal is **not to solve the problem yourself**, but to produce a high-fidelity **"Learning from Failure" Report**. This report will provide CodeAgent with a crystal-clear understanding of not just what went wrong, but why the initial strategic thinking was flawed. You are the bridge between a failed past and a successful future.

---

### **INPUTS FOR YOUR REVIEW**

1. **The Supreme Law (Problem Description & Ground Truth)**:
    
    - The ultimate, non-negotiable source of truth.
        
    - {context.problem_description}
        
    - {self._format_ground_truth_examples(context.test_cases)}
        
        
2. **The Evidence of Failure**:
    
    - The flawed code (the result of the flawed plan) and the specific failure log.
        
    - {self._format_current_code(context.current_code)}
        
    - {context.error_logs}
        

---

### **YOUR CORE ANALYTICAL PROTOCOL**

1. **Identify the Doctrinal Error**: First, you must pinpoint the core conflict between the Supreme Law and the Flawed Strategic Analysis. What fundamental misunderstanding of the rules led to this entire failure?
    
2. **Trace the Consequences**: Second, briefly explain how this doctrinal error in the strategy directly manifested as the flawed logic in the code, which in turn produced the specific failure log.
    
3. **Formulate the Core Lesson**: Finally, distill this entire analysis into a single, powerful "lesson learned". This lesson will be the core of your handoff to CodeAgent.
    

---

### **FINAL OUTPUT STRUCTURE**

Your response MUST be structured into the following three parts.

#### **Part 1: The Strategic Miscalculation**

<STRATEGIC_MISCALCULATION>...</STRATEGIC_MISCALCULATION>

- **A. The Ground Truth**: Quote the single most critical requirement directly from the Supreme Law.
    
- **B. The Flawed Doctrine**: Quote the single sentence from the Flawed Strategic Analysis that directly contradicts the Ground Truth.
    
- **C. The Core Conflict**: In one precise sentence, define the fundamental conflict between A and B. (e.g., "The conflict is between a requirement for 'Global Knowledge' and a strategy based on 'Local Decision-Making'.").
    

#### **Part 2: The Lesson Learned**

<LESSON_LEARNED>...</LESSON_LEARNED>

- **Purpose**: To synthesize the failure into a concise, actionable insight for your partner.
    
- **Action**: Based on the Core Conflict you just identified, formulate the single most important lesson that must be understood to solve this problem correctly.
    
- **Format**: State the lesson clearly and strategically.
 
    - **so your output like this in this block,A-Grade Example and Don't use this example**:
        
        > "The key lesson is that any strategy that attempts to make a final decision about an element in a single pass is doomed to fail. The problem's nature requires a two-phase approach: first, gather complete global information, and only then, make decisions based on that complete information."
        

#### **Part 3: The Investigative Handoff**

<INVESTIGATIVE_HANDOFF>...</INVESTIGATIVE_HANDOFF>

- **Purpose**: To hand over the investigation to CodeAgent with a powerful, guiding insight.
    
- **Action**: Formulate **one** clear, open-ended question that frames the problem around the Lesson Learned.
    
- **Critical Constraint**: Your question **must not** reveal specific code, variables, or values. It should be a strategic prompt for design, not a hint for debugging.
    - **so your output like this in this block,A-Grade Example and Don't use this example**:
        
        > "CodeAgent, we have learned that the previous failure was caused by a flawed strategy of making premature decisions based on incomplete information. Your task is to design a new algorithm from first principles. How can you structure your approach to ensure that all filtering decisions are made only after possessing the complete, global information required by the Supreme Law?"

"""

        return [
            {"role": "user", "content": prompt_content}
        ]

    def _build_solution_analysis_prompt11(self, context: DebugContext, simulation_response:str) -> List[Dict[str, str]]:
        """构建SolutionAgent基于模拟结果的分析提示词"""
        
        prompt_content = f"""
### **INPUTS FOR YOUR ANALYSIS**

1.  **The Original Problem Statement (For Context ONLY)**:
    -   This is the original, potentially ambiguous description. Use it only to understand the general intent.
    `{context.problem_description}`

3.  **The Evidence of Failure**:
    {context.error_logs}

4.  **The Flawed Code (The Subject of the Bug Fix)**:
    -   **Full Code:** 
    `{context.current_code}`

---

### **YOUR ANALYTICAL PROTOCOL**

You MUST perform the following two-step analysis. Your reasoning must be laser-focused on the provided inputs, prioritizing the **Requirement Clarification Memo**.

**1. Root Cause Synthesis (The "Why"):**
-   **Step A: Identify the Violated Requirement.** Look at the `Requirement Clarification Memo`. Which specific clarified term, keyword, or conflict resolution directive did the `Flawed Code` violate?
-   **Step B: Connect to the Evidence.** How did this violation lead to the specific `Incorrect Output` observed in the `Evidence of Failure`?
-   **Step C: Formulate the Diagnosis.** Synthesize these findings into a single, concise sentence that explains the **fundamental conceptual mismatch**. This is your `final_diagnosis`.
    -   *Example Diagnosis:* "The root cause is that the code implements a standard, order-sensitive tuple comparison, directly violating the clarified requirement for 'order-agnostic counting', which led to the incorrect count for mirrored tuples."

**2. Surgical Correction Planning (The "How"):**
-   Based on your diagnosis, devise the most direct and minimal set of changes to the **code** to fix the bug.
-   Your `correction_blueprint` must be a concrete, actionable plan that directly implements the violated requirement from the memo.
    -   *Example Blueprint Step:* "To implement 'order-agnostic counting', normalize each tuple into a canonical, sorted form before using it as a dictionary key."

---

### **FINAL OUTPUT STRUCTURE**

*(The output structure remains the same)*

```json
{{
  "final_diagnosis": "string",
  "correction_blueprint": [
    "string"
  ]
}}
```
-   `final_diagnosis`: Your final, synthesized analysis of the **root cause** of the code's failure, directly linked to the clarified requirements.
-   `correction_blueprint`: A list of strings, where each string is a clear, actionable step to **fix the code** according to the clarified requirements.

"""

        return [
            {"role": "user", "content": prompt_content}
        ]

 
    def _get_dynamic_instructions(self,block_name):
        # 这是一个简单的指令查找表
        instructions ={
    # 类别一：代码脚手架与定义
    "Header & Imports": """
    1.  **Identify Purpose:** What specific functionalities are being imported?
    2.  **Validate Necessity:** Is every imported library or function actually used within the `Full Code Context`? Unused imports are code clutter and should be flagged.
    3.  **Scrutinize Best Practices:** Are the imports standard, well-maintained libraries? Is the import style idiomatic (e.g., avoiding `from ... import *`)?
    """,
    "Helper Function Definition": """
    1.  **Identify Single Responsibility:** What is the single, well-defined purpose of this helper function?
    2.  **Validate Algorithm:** Is the logic within this function algorithmically sound and correct according to first principles?
    3.  **Assess Necessity and Design:** Does this logic truly warrant its own helper function, or is it an over-abstraction? Is the function pure (i.e., free of side effects)?
    """,
    "Core Algorithm Component Definition": """
    1.  **Identify the Principle:** What is the exact mathematical formula or core algorithmic principle this nested function represents (e.g., "This function calculates `f(x)` for Newton's method")?
    2.  **State the Textbook Definition:** Write down the formal, textbook-correct definition or formula for this principle.
    3.  **Compare Rigorously:** Compare the code implementation line-by-line against the textbook definition. Is it an exact and correct translation?
    """,

    # 类别二：预执行与状态设置
    "Input Validation": """
    1.  **Identify Assertions:** What specific preconditions and constraints about the input data is this code asserting?
    2.  **Validate Coverage:** Is this validation comprehensive? What edge cases is it NOT checking for (e.g., empty lists, incorrect data types, values out of a logical range)?
    3.  **Assess Error Handling:** Is the chosen error (e.g., `ValueError`) appropriate? Is the error message clear and helpful for a developer to debug?
    """,
    "Initial State Setup": """
    1.  **Identify All Variables:** List all variables being initialized in this block.
    2.  **Justify Initial Values:** For each variable, scrutinize its initial value. Is it a magic number? If it's a calculated starting point (like a heuristic), is that heuristic robust and well-justified for the algorithm in use?
    3.  **Assess Data Types:** Are the chosen data types (e.g., `int`, `float`, a list) appropriate for their purpose throughout the algorithm's execution?
    """,

    # 类别三：核心迭代逻辑
    "Main Execution Loop": """
    1.  **Identify Purpose:** What is the high-level goal of this loop (e.g., iteration, convergence, searching)?
    3.  **Justify the Algorithmic Choice:** Is this loop the most efficient and appropriate way to achieve the purpose? Should a different algorithm or data structure have been used to avoid this loop entirely or reduce its complexity?
    """,
    "State Update Logic": """
    1.  **Identify Algorithm Step:** What specific iterative step of the parent algorithm does this code represent (e.g., "This is the state update `x_new = ...` for the next iteration")?
    2.  **Validate Implementation Against Principle:** Does this code correctly and precisely implement the mathematical or logical formula for this specific update step? There is no room for error here.
    """,
    "Termination Condition": """
    1.  **Identify All Conditions:** List every distinct logical condition within this block that causes the loop to terminate (e.g., `if abs(dfx) < 1e-09`, `if abs(x1 - x0) < tolerance`).
    2.  **Analyze Robustness:** Scrutinize each condition. Does it robustly handle its intended case (e.g., convergence, error prevention)? What happens if this condition is never met (potential for an infinite loop)? Does it correctly prevent issues like division by zero?
    """,
    "Conditional Logic (in-loop)": """
    1.  **Identify the Condition:** What specific scenario or state is this `if` statement checking for within an iteration?
    2.  **Justify the Special Case:** Why is this conditional branch necessary? What specific edge case or alternative path does it handle that the main `State Update Logic` does not?
    3.  **Validate the Logic:** Is the logic *within* this conditional branch the correct response to the identified special case?
    """,

    # 类别四：终结与通用
    "Final Output & Return": """
    1.  **Identify the Return Value:** What exact variable or expression is being returned?
    2.  **Validate Final Transformation:** Scrutinize any final operations applied to the result before returning (e.g., rounding, type casting, formatting). Is this transformation specified in the requirements or is it an arbitrary decision that could be losing precision or information?
    3.  **Check Against Specification:** Does the returned value's type and format precisely match the function's type hints and the problem description?
    """,
    "General Statement": """
    1.  **Identify the Purpose:** What is the intended purpose of this code block?
    2.  **Validate Correctness :** Does this code correctly fulfill its stated purpose within the context of the overall program? Is it implemented in a clear and maintainable way?
    """,
    "default": """
    1.  **Identify the Purpose:** What is the intended purpose of this code block?
    2.  **Validate Correctness & Robustness:** Does this code correctly and robustly fulfill its stated purpose within the context of the overall program? Is it implemented in a clear and maintainable way?
    """
}
        return instructions.get(block_name, instructions["default"])

    def _parse_and_augment_llm_response(
            self,
            llm_response_str: str, 
            code_slice: str
        ) -> Optional[Dict[str, Any]]:
        import json
        import re
        from typing import Dict, Any, Optional
        # 1. 提取 JSON: 使用正则表达式查找第一个 '{' 到最后一个 '}' 之间的内容
        #    re.DOTALL 标志让 '.' 也可以匹配换行符
        match = re.search(r'\{.*\}', llm_response_str, re.DOTALL)

        if not match:
            print(f"Error: No JSON object found in the response:\n{llm_response_str}")
            return None

        json_str = match.group(0)

        try:
            # 2. 解析 JSON
            parsed_json = json.loads(json_str)

            # 3. 验证必需的字段是否存在
            if 'verdict' not in parsed_json or 'explanation' not in parsed_json:
                print(f"Error: Parsed JSON is missing required keys ('verdict', 'explanation').\nParsed JSON: {parsed_json}")
                return None

            # 4. 增强数据: 构建最终的输出字典
            #    我将您的字段名 'sinapints' 理解为 'code_slice'，如果需要可以修改
            augmented_result = {
                "code_slice": code_slice.strip(),
                "verdict": parsed_json['verdict'],
                "explanation": parsed_json['explanation']
            }

            return augmented_result

        except json.JSONDecodeError as e:
            print(f"Error: Failed to decode JSON from the extracted string.\nError: {e}\nExtracted string: {json_str}")
            return None

class BlueprintDesignNode(DebugNode):
    """节点二: 蓝图设计与审查"""
    
    def __init__(self, quality_gate: QualityGate, verbose: int = 1):
        super().__init__(NodeType.BLUEPRINT_DESIGN, quality_gate, verbose)
    
    def execute(self, context: DebugContext, agents: Dict[AgentRole, BaseAgent]) -> NodeResult:
        """
        执行蓝图设计节点 - 按照精密状态机流程执行
        
        完整实现七步流程：
        1. 节点启动 2. 主循环开始 3. 接收与解析 4. 角色轮换与决策 
        5. 准备修改 6. 健康度监控 7. 节点收尾
        """
        self._log("🎯 开始蓝图设计与审查...")
        
        solution_agent = agents[AgentRole.SOLUTION_AGENT]
        code_agent = agents[AgentRole.CODE_AGENT]
        
        # 检查是否有SimulationAgent可用
        simulation_agent = agents.get(AgentRole.SIMULATION_AGENT)
        enhanced_mode = simulation_agent is not None
        
        if enhanced_mode:
            self._log("🔬 检测到SimulationAgent，启动第二阶段增强模式")
        else:
            self._log("📝 使用标准模式（无SimulationAgent）")
        
        # === 第一步: 节点启动 (Node Initialization) ===
        current_speaker = AgentRole.CODE_AGENT  # 设置发言者为 CodeAgent
        approved_node_1_output = self._format_diagnosis_output(context)
        approved_node_1_output_str=f"""{context.diagnosis_result.get("raw_response","No diagnosis result provided")}"""
        # 构建 PROMPT_A_CODE_AGENT_PROPOSE
        initial_prompt = self._build_code_agent_propose_prompt(context, approved_node_1_output_str)
        
        # 调用 CodeAgent 并等待回复
        response = code_agent._call_model(initial_prompt, include_history=False)
        
        # === 第二步: 主循环开始 (Main Loop Start) ===
        dialogue_history = [{"speaker": "CodeAgent", "content": response}]
        turn_count = 0
        blueprint_approved = False
        current_blueprint = None
        blueprint_history = []  # 新增：存储所有蓝图历史
        max_blueprint_retries = 2  # 最大重试次数
        review_num=6  # 每隔多少轮进行一次中期回顾
        # 导演建议缓存
        orchestrator_intervention_for_solution = None
        orchestrator_intervention_for_code = None
        
        # 中期回顾结果缓存
        midterm_review_for_solution = None
        midterm_review_for_code = None
        
        # 动态蓝图存储list：平时len=1，中期回顾时len=2
        blueprint_storage = []
        simulation_responses = []
        while turn_count <= self.max_turns and not blueprint_approved:
            simulation_agent.start_new_session() if simulation_agent else None
            turn_count += 1
            self._log(f"🔄 对话轮次 {turn_count}/{self.max_turns}")
            
            
            # === 第三步: 接收与解析 (Receive & Parse) ===
            current_response = dialogue_history[-1]["content"]
            current_speaker_name = dialogue_history[-1]["speaker"]
            
            # # 基础格式检查
            # if current_speaker_name == "CodeAgent":
            #     required_tags = [] if turn_count == 1 else ["RESPONSE_TO_CRITIQUE", "REFINED_BLUEPRINT"]
            # elif current_speaker_name == "SolutionAgent":
            #     required_tags = ["BLUEPRINT_CRITIQUE"]  # 另一个标签是可选的
            # elif current_speaker_name == "SimulationAgent":
            #     # SimulationAgent不需要格式检查，直接传递给下一个Agent
            #     required_tags = []
            # else:
            #     required_tags = []  # Orchestrator 干预无需检查格式
            
            # if required_tags:
            #     format_check = self.quality_gate.validate_required_tags(current_response, required_tags)
            #     if not format_check["valid"]:
            #         self._log(f"❌ {current_speaker_name} 格式检查失败: {format_check['missing_tags']}")
            #         # 要求同一Agent重试
            #         retry_feedback = f"Your previous response was invalid. You MUST use the required tags: {', '.join([f'<{tag}></{tag}>' for tag in required_tags])}. Please try again.But remember just to add the missing tags and keep the original content unchanged."
                    
            #         if current_speaker_name == "CodeAgent":
            #             retry_prompt = self._build_code_agent_retry_prompt(context, dialogue_history, retry_feedback)
            #             retry_response = code_agent._call_model(retry_prompt, include_history=False)
            #             dialogue_history[-1] = {"speaker": "CodeAgent", "content": retry_response}
            #         elif current_speaker_name == "SolutionAgent":
            #             retry_prompt = self._build_solution_agent_retry_prompt(context, dialogue_history, retry_feedback)
            #             retry_response = solution_agent._call_model(retry_prompt, include_history=False)
            #             dialogue_history[-1] = {"speaker": "SolutionAgent", "content": retry_response}
            #         elif current_speaker_name == "SimulationAgent":
            #             # SimulationAgent重试（虽然不检查格式，但保留重试机制以防万一）
            #             retry_prompt = self._build_simulation_agent_retry_prompt(context, dialogue_history, retry_feedback)
            #             retry_response = simulation_agent._call_model(retry_prompt, include_history=False)
            #             dialogue_history[-1] = {"speaker": "SimulationAgent", "content": retry_response}
                    
            #         continue  # 跳过本轮后续步骤，重新开始循环
            
            self._log("✅ 格式检查通过")
            
            # 提取当前蓝图（如果是CodeAgent的回复）
            if current_speaker_name == "CodeAgent":
                #current_blueprint = self._extract_blueprint_from_response(current_response)
                current_blueprint = dialogue_history[-1]["content"]
                self._log(f"📋 更新当前蓝图")
                
                # 动态存储：平时只存储当前蓝图（len=1）
                blueprint_storage = [current_blueprint]
                self._log(f"💾 存储当前蓝图，blueprint_storage长度: {len(blueprint_storage)}")
                
            # === 第六步: 健康度监控 (Health Checks) ===
            # 检查中期回顾 - 每6轮生成中期回顾block
            if turn_count > review_num and turn_count % (review_num) == 1:
                self._log(f"🎬 触发中期回顾 - 第{turn_count}轮对话")
                
                # 提取各自Agent的对话历史
                solution_dialogue = [msg["content"] for msg in dialogue_history if msg["speaker"] == "SolutionAgent"]
                code_dialogue = [msg["content"] for msg in dialogue_history if msg["speaker"] == "CodeAgent"]
                
                # 获取必要的参数
                context_problemdescription = context.problem_description
                approved_node_1_output = approved_node_1_output_str  # 第一节点的内容
                current_blueprint_content = current_blueprint or "No blueprint generated yet"
                
                # 获取最近两次 solution_dialogue 
                solution_dialogue_recent = "\n\n".join(solution_dialogue[-2:]) if len(solution_dialogue) >= 2 else "\n\n".join(solution_dialogue)
                
                # 为CodeAgent生成中期回顾block
                if code_dialogue:
                    code_meta_prompt = self.quality_gate.build_code_agent_meta_refine_prompt(
                        context_problemdescription=context_problemdescription,
                        approved_node_1_output=approved_node_1_output,
                        current_blueprint=current_blueprint_content,
                        solution_dialogue_recent=solution_dialogue_recent
                    )
                    self._log("🔧 生成CodeAgent中期回顾block...")
                    code_meta_response = code_agent._call_model([{"role": "user", "content": code_meta_prompt}], include_history=False)
                    
                    # 解析 ALTERNATIVE_BLUEPRINT 标签内容
                    alternative_blueprint = self._extract_alternative_blueprint_from_response(code_meta_response)
                    if alternative_blueprint:
                        self._log("🎯 成功解析到 ALTERNATIVE_BLUEPRINT 内容")
                        # 中期回顾时：重新构建list，包含当前蓝图和替代蓝图（len=2）
                        blueprint_storage = [current_blueprint, alternative_blueprint]
                        self._log(f"💾 中期回顾模式：重构blueprint_storage，长度: {len(blueprint_storage)}")
                        self._log(f"📋 ALTERNATIVE_BLUEPRINT 内容长度: {len(alternative_blueprint)} 字符")
                    else:
                        self._log("⚠️ 未能解析到 ALTERNATIVE_BLUEPRINT 内容")
                        # 即使解析失败，也保持当前蓝图在list中
                        blueprint_storage = [current_blueprint,code_meta_response]
                        self._log(f"💾 解析失败，保持当前蓝图，blueprint_storage长度: {len(blueprint_storage)}")
                
                
                self._log("✅ 中期回顾block生成完成")    
           
            
            # === 第四步: 角色轮换与决策 (Role Rotation & Decision Making) ===
            
            if current_speaker_name == "CodeAgent":
                # Case 1: CodeAgent刚发言，轮到下一个Agent
                
                # 增强模式：CodeAgent → SimulationAgent
                self._log("🔬 切换到 SimulationAgent 模拟分析")
                current_speaker = AgentRole.SIMULATION_AGENT
                
                # 循环处理 blueprint_storage 中的所有蓝图
                
                for i, blueprint in enumerate(blueprint_storage):
                    self._log(f"🔬 模拟第 {i+1}/{len(blueprint_storage)} 个蓝图")
                    if i==0:
                        self._log("💾 使用当前蓝图进行模拟")

                    # 构建针对特定蓝图的SimulationAgent提示词
                    simulation_prompt = self._build_simulation_agent_prompt(
                        context, 
                        dialogue_history, 
                        blueprint_override=blueprint,  # 传入特定蓝图
                        orchestrator_intervention=None  # 暂时不支持导演干预
                    )
                    
                    simulation_response = simulation_agent._call_model(simulation_prompt, include_history=False)
                    simulation_responses.append(simulation_response)
                    
                    # 只有第一次的响应进入dialogue_history
                    if i == 0:
                        dialogue_history.append({"speaker": "SimulationAgent", "content": simulation_response})
                        self._log("📝 第1个模拟响应已加入dialogue_history")
                    else:
                        self._log(f"📝 第{i+1}个模拟响应仅存储，不加入dialogue_history")
                    
                self._log(f"💾 总计处理 {len(simulation_responses)} 个模拟响应")
               

                
            
            elif current_speaker_name == "SimulationAgent":
                # Case 2: SimulationAgent刚发言，循环检测所有模拟响应
                self._log("🔬 开始 SimulationAgent 质量验证循环")
                
                simulation_passed = False
                
                # 循环检测所有模拟响应
                for i, response in enumerate(simulation_responses):
                    self._log(f"🔍 检测第 {i+1}/{len(simulation_responses)} 个模拟响应")
                    
                    # 对每个响应进行结论验证
                    conclusion_result = self.quality_gate.verify_simulation_conclusion(str(context.expected_value), response)
                    
                    if conclusion_result == "PASSED":
                        self._log(f"✅ 第{i+1}个模拟响应质量门控验证通过 - 模拟结果正确，直接批准蓝图")
                        blueprint_approved = True
                        current_blueprint = blueprint_storage[i]
                        break  # 只要有一个通过就批准蓝图
                    else:
                        self._log(f"❌ 第{i+1}个模拟响应质量门控验证失败")
                

                # 如果所有响应都没有通过验证，且有多个候选蓝图，启动分诊系统
                if not blueprint_approved and len(simulation_responses) > 1:
                    self._log("🏥 所有模拟响应验证失败，且有多个候选蓝图 - 启动分诊系统")
                    
                    # 调用分诊检查系统
                    triage_result = self.quality_gate.triage_blueprint_selection(
                        supreme_law=context.problem_description,
                        candidate1_simulation=simulation_responses[0],
                        candidate2_simulation=simulation_responses[1]
                    )
                    
                    chosen_index = triage_result["chosen_candidate"] - 1  # 转换为0-based索引
                    self._log(f"🏥 分诊系统选择了候选蓝图 {triage_result['chosen_candidate']}")
                    self._log(f"🏥 分诊理由: {triage_result['justification'][:150]}..." if len(triage_result['justification']) > 150 else f"🏥 分诊理由: {triage_result['justification']}")
                    
                    # 根据分诊结果更新当前蓝图和dialogue_history
                    current_blueprint = blueprint_storage[chosen_index]
                    
                    # 如果选择的不是第一个候选，需要更新dialogue_history中的SimulationAgent响应
                    if chosen_index != 0:
                        # 替换dialogue_history中最后一个SimulationAgent的响应
                        for i in range(len(dialogue_history) - 1, -1, -1):
                            if dialogue_history[i]["speaker"] == "SimulationAgent":
                                dialogue_history[i]["content"] = simulation_responses[chosen_index]
                                current_blueprint = blueprint_storage[chosen_index]
                                self._log(f"🏥 已更新dialogue_history中的SimulationAgent响应为选中的候选{triage_result['chosen_candidate']}")
                                break
                
                simulation_responses = []  # 清空模拟响应缓存
                blueprint_storage = []  # 清空蓝图存储缓存

                self._log("💾 清空模拟响应和蓝图存储缓存")
                # 如果所有响应都没有通过验证
                if not blueprint_approved:
                    self._log("❌ 所有模拟响应验证失败 - 继续让SolutionAgent审查")
                    simulation_passed = True
                
                
                # 如果蓝图已批准，退出主循环
                if blueprint_approved:
                    break
                
                # 如果验证完成但蓝图未批准，继续让SolutionAgent审查
                if simulation_passed:
                    self._log("👤 SimulationAgent → SolutionAgent 审查")
                    current_speaker = AgentRole.SOLUTION_AGENT
                
                    
                    # 如果注入了导演建议，清空缓存
                    if orchestrator_intervention_for_solution:
                        self._log("✅ 导演建议已注入SolutionAgent prompt，清空缓存")
                        orchestrator_intervention_for_solution = None
                    
                    # 如果注入了中期回顾，清空缓存
                    if midterm_review_for_solution:
                        self._log("✅ 中期回顾已注入SolutionAgent prompt，清空缓存")
                        midterm_review_for_solution = None

                  
                
                    #对 语义解读
                    SimulationReader_prompt=self._build_simulationreader_prompt(context, dialogue_history)
                    simulation_report_analysis=solution_agent._call_model(SimulationReader_prompt, include_history=False)

                    # 构建 PROMPT_B_SOLUTION_AGENT_REVIEW（增强模式，包含SimulationAgent的分析）
                    review_prompt = self._build_solution_agent_review_prompt(
                        context, 
                        dialogue_history, 
                        orchestrator_intervention=orchestrator_intervention_for_solution,
                        midterm_review_block=midterm_review_for_solution,
                        current_blueprint=current_blueprint
                    )

                    solution_response = solution_agent._call_model(review_prompt, include_history=False)

                    solution_response = {"Semantic_Diagnosis": simulation_report_analysis,
                                        "Logic_Diagnosis":solution_response}
                    solution_response_str=f"""{solution_response}"""
                    
                    dialogue_history.append({"speaker": "SolutionAgent", "content": solution_response_str})
                
            elif current_speaker_name == "SolutionAgent":
                # Case 2: SolutionAgent刚发言，进行三级检查
                self._log("🔍 分析 SolutionAgent 意图")
                
                    
                if enhanced_mode:
                    # 增强模式：SolutionAgent → CodeAgent（跳过SimulationAgent，直接修改）
                    self._log("🔧 增强模式：SolutionAgent → CodeAgent 修改")
                    current_speaker = AgentRole.CODE_AGENT
                else:
                    # 标准模式：SolutionAgent → CodeAgent
                    self._log("🔧 标准模式：SolutionAgent → CodeAgent 修改")
                    current_speaker = AgentRole.CODE_AGENT
                
                # 构建 PROMPT_C_CODE_AGENT_REFINE，检查是否需要注入导演建议和中期回顾
                refine_prompt = self._build_code_agent_refine_prompt(
                    context, 
                    dialogue_history, 
                    current_blueprint,
                    orchestrator_intervention=orchestrator_intervention_for_code,
                )
                
                # 如果注入了导演建议，清空缓存
                if orchestrator_intervention_for_code:
                    self._log("✅ 导演建议已注入CodeAgent prompt，清空缓存")
                    orchestrator_intervention_for_code = None
                
              
                
                code_response = code_agent._call_model(refine_prompt, include_history=False)
                dialogue_history.append({"speaker": "CodeAgent", "content": code_response})
                
           
            
            else:
                # Orchestrator 干预后，继续流程
                self._log("🎬 导演干预完成，继续流程")
                continue
            
        # === 第七步: 节点收尾 (Node Finalization) ===
        if blueprint_approved:
            self._log("🎉 蓝图设计阶段成功完成")
            
            # 解析最后三条对话记录 (code, simulation, solution)
            last_three_dialogue = self._extract_last_three_dialogue(dialogue_history, enhanced_mode)
            
            # 分别设置 context 中的三个字段
            context.blueprint = current_blueprint
            context.simulation = last_three_dialogue.get("simulation")
            context.solution = last_three_dialogue.get("solution")
            
            return NodeResult(
                success=True,
                output={
                    "blueprint": current_blueprint, 
                    "turn_count": turn_count,
                    "dialogue_history": dialogue_history,
                    "last_code_response": last_three_dialogue.get("code"),
                    "last_simulation_response": last_three_dialogue.get("simulation"),
                    "last_solution_response": last_three_dialogue.get("solution")
                },
                next_node=NodeType.IMPLEMENTATION
            )
        else:
            self._log("⏰ 超时强制结束，需要超时处理节点")
            
            # 解析最后三条对话记录 (code, simulation, solution)
            last_three_dialogue = self._extract_last_three_dialogue(dialogue_history, enhanced_mode)
            
            # 将对话历史存储到context中，供超时处理节点使用
            context.dialogue_history = dialogue_history
            
            # 设置其他context字段
            context.blueprint = current_blueprint or "No blueprint generated"
            context.simulation = last_three_dialogue.get("simulation", "No simulation response")
            context.solution = last_three_dialogue.get("solution", "No solution response")
            context.timeout = True
            return NodeResult(
                success=True,
                output={
                    "blueprint": current_blueprint or "No blueprint generated", 
                    "turn_count": turn_count,
                    "dialogue_history": dialogue_history,
                    "timeout_reason": "Blueprint design exceeded maximum turns",
                    "last_code_response": last_three_dialogue.get("code"),
                    "last_simulation_response": last_three_dialogue.get("simulation", "No simulation response"),
                    "last_solution_response": last_three_dialogue.get("solution", "No solution response")
                },
                next_node=NodeType.TIMEOUT_HANDLER
            )
            
           
    
    def _format_diagnosis_output(self, context: DebugContext) -> str:
        """格式化诊断阶段的完整输出"""
        diagnosis = context.diagnosis_result
        return f"""<COMPUTATIONAL_TRACE>
{diagnosis.get('computational_trace', '')}
</COMPUTATIONAL_TRACE>

<DEVIATION_STATEMENT>
{diagnosis.get('deviation_statement', '')}
</DEVIATION_STATEMENT>

<EXPLORATORY_QUESTION>
{diagnosis.get('exploratory_question', '')}
</EXPLORATORY_QUESTION>"""
    
    def _build_code_agent_propose_prompt(self, context: DebugContext, approved_node_1_output: str) -> List[Dict[str, str]]:
        """构建 PROMPT_A_CODE_AGENT_PROPOSE"""
        prompt_content = f"""
You are **CodeAgent**, a master software architect. Your mission is to design a **new, correct, and robust algorithm** from first principles.

You will **NOT** be shown any previous flawed code. Your design will be guided exclusively by the Supreme Law and a **"Learning from Failure" Report** prepared by your partner, SolutionAgent. Your goal is to architect a solution that is **immune** to the previously identified strategic flaws.

---

### **CONTEXT FOR YOUR DESIGN**

1. **The Supreme Law (The Problem Definition)**:
    
    - The ultimate, non-negotiable source of truth.
        
    - {context.problem_description}

        
2. **The "Learning from Failure" Report (from SolutionAgent)**:
    
    - **This is your most critical input.** It contains a precise critique of a past strategic error and distills the core lesson needed for success.
        
    - {approved_node_1_output}
        

---

### **CORE ARCHITECTURAL PRINCIPLE**

**LOGIC MUST BE DERIVED FROM RULES, NOT EXAMPLES.** Your blueprint must be a direct translation of the general principles from the Supreme Law and the Lesson Learned into an algorithm. A blueprint that relies on specific example values is not a robust algorithm and will be rejected.

---

### **YOUR TASK**

This is the blueprint design phase. Your response must be structured into two parts, following a strict "analysis-first, then-code" protocol.

#### **Part 1: The Analysis & Strategy Synthesis**

<ANALYSIS_SYNTHESIS>...</ANALYSIS_SYNTHESIS>

- **Internalize the Core Lesson**: First, in your own words, state the key insight from the **<LESSON_LEARNED>** section of your partner's report. This confirms you understand the fundamental principle for success and the primary strategic error to avoid.
    
- **Propose a High-Level Plan**: Based on the Lesson Learned, outline a clear, multi-step plan to solve the problem. Your plan must be inherently designed to neutralize the strategic flaw identified in the report. (e.g., "Given that the core lesson is to avoid premature decisions, my plan will be: Step 1: Perform a full pass solely to gather global information... Step 2: In a separate, second pass, use this complete information to construct the final result...").
    
- **Select Key Data Structures**: For each step in your plan, specify the data structures you will use (e.g., Dictionary/Hash Map for counting, List for ordered results) and briefly justify why each is the correct tool to execute your plan.
    
- **Validate the Strategy**: Perform a final mental check. Briefly confirm that your proposed plan inherently respects **all** constraints of the Supreme Law (e.g., correctness, order preservation, etc.).
    

#### **Part 2: The Initial Blueprint**

<INITIAL_BLUEPRINT>...</INITIAL_BLUEPRINT>

- **Implement Your Strategy**: Provide a **pure pseudocode algorithm** that is a direct and concrete implementation of the **High-Level Plan** you just proposed.
    
- **COMPLETE IMPLEMENTATION REQUIREMENT**: Your final blueprint **MUST** include the complete and verbatim implementation of **ALL** functions defined in the Supreme Law. This includes both the function you are redesigning and any helper or contextual functions provided. For instance, if the task is to write decode_cyclic and the Supreme Law provides both encode_cyclic and decode_cyclic definitions, your final blueprint must contain the full code for both.
    
- **FATAL TRAP**: You are **STRICTLY FORBIDDEN** from writing comments that explain your thought process, derive formulas, or restate the problem inside the <INITIAL_BLUEPRINT>. All strategic thinking belongs in <ANALYSIS_SYNTHESIS>. The blueprint must contain only the essential, actionable steps of the algorithm

"""
        
        return [{"role": "user", "content": prompt_content}]

    def _build_code_agent_propose_prompt1(self, context: DebugContext, approved_node_1_output: str) -> List[Dict[str, str]]:
        """构建 PROMPT_A_CODE_AGENT_PROPOSE"""
        prompt_content = f"""

### ROLE AND GOAL
You are a **Principal Software Engineer**. Your mission is to write the final, correct, and production-ready Python code based on a definitive diagnostic report.

You will **not** be shown any previous flawed code. Your implementation must be a direct and robust realization of the provided specification and the correction blueprint.

---

### **INPUTS FOR YOUR IMPLEMENTATION**

1.  **Ground Truth (The Unchanging Specification)**:
    -   The complete problem description and function signatures. This is the ultimate source of truth for the final code's structure.
    -   `{context.problem_description}`
    -   The sample io
    -   `{context.test_cases}`

2.  **Final Diagnosis and Correction Blueprint**:
    -   **This is your primary guide.** It contains the root cause analysis of previous failures and a prioritized, step-by-step plan for the correct implementation.
    -   `{approved_node_1_output}`
        
---

### **YOUR TASK: DIRECT IMPLEMENTATION**

Your **sole task** is to write the complete, runnable Python code that correctly implements the algorithm described in the **`Ground Truth`** and meticulously follows every step in the **`Correction Blueprint`**.
-   Your code must be robust, clean, and directly reflect the logic prescribed in the correction_blueprint!.
-   It must adhere strictly to the function signatures provided in the `Ground Truth`.

---

### **FINAL OUTPUT STRUCTURE**

Your entire response MUST be a single, complete, and runnable Python code block.

"""
        
        return [{"role": "user", "content": prompt_content}]

    def _build_solution_agent_review_prompt(self, context: DebugContext, dialogue_history: List[Dict[str, str]], orchestrator_intervention: Optional[str] = None, midterm_review_block: Optional[str] = None, current_blueprint: Optional[str] = None) -> List[Dict[str, str]]:
        """构建 PROMPT_B_SOLUTION_AGENT_REVIEW"""
        latest_message = dialogue_history[-1]["content"] if dialogue_history else ""
        
        
        
        prompt_content = f"""

### ROLE
You are the **Universal Logic Auditor**.
Your mandate is to perform an impartial, evidence-based review of a failed code execution.

**CORE PHILOSOPHY**:
1. **Presumption of Innocence**: Do not assume the code logic is "wrong" just because the test failed. The code might be following the rules perfectly, but the rules (or the test case) might be ambiguous.
2. **Fact Over Narrative**: Never invent data (e.g., indices, values) to fit a failure narrative. Stick to the absolute Ground Truth of the Input.
3. **Mechanism over Outcome**: Focus on *HOW* the decision was made, not just *WHAT* the output was.

---

### INPUT DATA
1. **The Supreme Law (Rules)**:
   The abstract requirements.
   {context.problem_description}

2. **The Ground Truth (Input Data)**:
   The raw, immutable input provided to the function.
   {context.expected_value}

4. **The Execution Log (Trace)**:
   The step-by-step recording of what the code actually did.
   {latest_message}


---

### AUDIT PROTOCOL (Strict Reasoning Process)

You must follow this **"State-Rule-Check"** workflow internally.

#### STEP 1: Freeze the Ground Truth (The Ledger)
Look at input data. Create a mental "Ledger" of the data **before** any code touched it.
- If Input is a List: Note exactly the Index (0, 1, 2...) and Value of each item.
- If Input is String: Note specific characters at specific indices.
- *Constraint*: **DO NOT** let the trace influence this step. Read the raw input only.

#### STEP 2: The "Rule vs. Action" Verification
Iterate through the critical decisions in the execution log. For each decision, ask:
"Did this specific action violate a specific rule from the problem description?"

*   **Type A Check (Transformation)**:
    - Rule: "Keep only even numbers."
    - Action: Code kept 5.
    - Verdict: **VIOLATION**.

*   **Type B Check (Comparison/Sorting)**:
    - Rule: "Sort by Value, then by Index."
    - Action: Code placed Item A before Item B.
    - Verdict: Check the Ledger.
      - Is Value(A) < Value(B)? (Yes -> Valid)
      - If Values equal, is Index(A) < Index(B)? (Yes -> Valid)
      - If NO -> **VIOLATION**.

*   **Type C Check (Mutation)**:
    - Rule: "Check last character."
    - Action: Code stripped whitespace.
    - Verdict: Does this modify the "last character"? Yes. **POTENTIAL VIOLATION**.

#### STEP 3: The Root Cause Triangle
Based on Step 2, determine where the blame lies. Choose ONE path:

*   **Path 1: The Code Lied (Implementation Logic Error)**
    - The code explicitly violated a rule found in the text. (e.g., It compared X instead of Y).
    - *Evidence*: Point to the exact line in the Trace where the violation happened.

*   **Path 2: The Code Obeyed, But Failed (Semantic/Requirement Gap)**
    - The code followed every written rule perfectly (Step 2 passed).
    - BUT, the output still contradicts the Expected Output.
    - *Conclusion*: The prompt/rules were ambiguous, or the test case relies on an unwritten rule (e.g., "digits" implies 0-9, "sort" implies stable sort even if not asked).

*   **Path 3: The Hallucination Check (Self-Correction)**
    - If you think the code is wrong, double-check your "Ledger" from Step 1. Are you sure about the indices/values? If you invented an index to make the code look wrong, STOP and recant.

---

### REQUIRED OUTPUT FORMAT (JSON)

{{
  "Input_Audit": {{
    "Key_Properties": "Describe the critical features of input (e.g., 'Input is [1, -1]. Index of 1 is 0. Index of -1 is 1.')",
    "Data_Integrity_Status": "State if the code preserved the data or mutated it (e.g., 'Code stripped spaces', 'Code preserved indices')."
  }},
  "Logic_Verification": [
    {{
      "Action_Analyzed": "Describe a key step (e.g., 'Comparison between 1 and -1')",
      "Rule_Applied": "Quote the rule (e.g., 'Sort by digit sum, then original index')",
      "Is_Compliant": true/false,
      "Reasoning": "Strict mathematical/logical justification. (e.g., 'Sum(1)=1, Sum(-1)=1. Tie. Index(1)=0, Index(-1)=1. 0<1. So 1 MUST come before -1.')"
    }}
  ],
  "Final_Diagnosis": {{
    "Error_Type": "Choose: 'Logic Implementation Error' OR 'Requirement/Semantic Ambiguity'",
    "The_Truth": "Explain what actually went wrong without hallucinating. if you think the expected output in the test case is incorrect,then the problem imply some underlying rule ,you must figure out to help the codeagent.Remember the sampleio and problem are always right,instead the code."
  }}
}}
"""
        
        return [{"role": "user", "content": prompt_content}]
    
    def _build_simulationreader_prompt(self, context: DebugContext, dialogue_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        latest_message = dialogue_history[-1]["content"] if dialogue_history else ""
        """构建 SimulationReader 提示词"""
        prompt_content = f"""
### ROLE

You are the **Semantic Consistency Diagnoser**.

Your sole responsibility is to determine whether the **observed execution behavior** is *semantically consistent* with the **problem specification**, independent of implementation mechanics.

You do **not** judge whether the code is “well written”.
You judge whether the code **respects the meaning of the rules**.

---

### INPUT DATA

1. **The Specification (Natural Language Rules)**
   The authoritative description of expected behavior.
   {context.problem_description}
2. **The Ground Truth (Input Data)**:
   The raw, immutable input provided to the function.
   {context.expected_value}

3. **The Simulation Report (Observed Behavior)**
   A concrete, step-by-step execution trace showing:

   * input values
   * evaluated conditions
   * produced outputs
     {latest_message}

---

### CORE SEMANTIC PRINCIPLES

You must reason using these principles:

1. **Specification is Law**
   Natural language rules define *what must be true*, even if not formally expressed.

2. **Boundary Conditions Are Semantics**
   Exact values explicitly mentioned in the specification (e.g. “4.0 maps to A+”) are **semantic anchors** and must be respected exactly.

3. **Execution ≠ Intention**
   A program may execute consistently and still violate meaning.

4. **No Control-Flow Policing**
   Do NOT evaluate ordering of branches, loops, or code structure unless it directly alters semantic meaning.

5. **Examples Are Binding, Not Illustrative**
Any example explicitly listed in the specification defines ground-truth semantics.
You MUST NOT reinterpret, justify, or generalize an example.

6. **No Rule Induction from Examples**
Examples define semantic truth ONLY for the exact input shown.
You MUST NOT:
- Generalize an example into a broader rule
- Summarize examples into natural-language policies
- Introduce conditions not explicitly stated in the specification

An example may only produce this contract:
Exact_Input → Exact_Expected_Output

---

### ⚠️ SEMANTIC UNIT INTEGRITY (CRITICAL ADDITION)

Before evaluating correctness, you MUST explicitly verify that the **semantic unit being reasoned over**
matches the **semantic unit defined by the specification**.

You MUST NOT silently upgrade, decompose, or reinterpret semantic units.

Typical violations include (but are not limited to):

- Treating a **number range problem** as a **digit-extraction problem**
- Treating **digits** as “digits appearing inside numbers” when the specification only defines digits as atomic values (e.g. 0–9)
- Introducing intermediate structures (e.g. digit lists, character streams, decomposed components) that are not authorized by the specification

⚠️ Example of a semantic trap:
If a specification asks for “even digits between a and b” and explicitly maps an input like `(10, 14)` to `[]`,
then reasoning over digits extracted from numbers such as `10 → {1, 0}` constitutes a **Category Definition Drift**,
even if the extracted digits themselves are even.

Any mismatch between **defined semantic units** and **observed semantic units** must be treated as a semantic violation.

---

### SEMANTIC DIAGNOSIS PROCEDURE

You must follow this process internally.

---

#### STEP 1: Extract Semantic Contracts from Specification

From the specification, extract **explicit semantic commitments**, such as:

* Exact-value mappings
  (“4.0 → A+”)
* Inclusive vs exclusive boundaries
  (“> 3.7”, “≥ 3.7”, “equal to”)
* Implied invariants
  (“last character”, “original order”, “digit”)

Represent them mentally as:

Input Condition → Required Output Meaning

⚠️ Semantic Extraction Constraint:
Extract ONLY explicitly stated or exemplified semantics.
Do NOT infer, normalize, or repair the specification.
Ambiguity is a semantic fact, not a defect to be corrected.

---

#### STEP 2: Identify Boundary-Relevant Observations in Simulation

From the simulation report, locate:

* Inputs that lie **exactly on semantic boundaries**
* Inputs that are **named or exemplified** in the specification
* Observed outputs for those inputs

Ignore internal branching mechanics unless needed to explain meaning violation.

---

#### STEP 3: Semantic Consistency Check

For each semantic contract:

Ask:

> “Does the observed behavior preserve the intended meaning of this rule?”

Key checks include (but are not limited to):

* Equality vs strict inequality mismatches
* Off-by-one or off-by-epsilon boundaries
* Silent reinterpretation of categories
* Implicit exclusions or expansions of explicitly defined cases

If a contract is violated, mark it as a **Semantic Violation**.

---

### SEMANTIC ERROR CLASSIFICATION

If a violation exists, classify it as one of:

* **Boundary Semantics Error**
  (e.g. `>` used where equality is required)

* **Category Definition Drift**
  (e.g. reasoning over digits extracted from numbers when only digits themselves are defined)

* **Implicit Rule Omission**
  (e.g. specification assumes stability or inclusivity not implemented)

---
🚫 Prohibited Reasoning:
Do NOT reference code mechanisms or execution causes.
Explain only semantic alignment or contradiction.

---
### REQUIRED OUTPUT FORMAT (JSON)
```json
{{
  "Semantic_Contracts": [
    {{
      "Specification_Clause": "Quote or paraphrase the rule",
      "Expected_Meaning": "What must be true semantically",
      "Boundary_Condition": "Exact value or condition if applicable"
    }}
  ],
  "Semantic_Evaluation": [
    {{
      "Observed_Input": "Concrete input value",
      "Observed_Output": "Output from simulation",
      "Is_Semantically_Valid": false,
      "Explanation": "Explain the meaning mismatch, not the code structure"
    }}
  ],
  "Semantic_Diagnosis": {{
    "Status": "PASS or FAIL",
    "Primary_Issue_Type": "Boundary Semantics Error / Category Drift / Implicit Rule Omission / None",
    "Summary": "Concise explanation of the semantic truth"
  }}
}}
```
        """
        return [{"role": "user", "content": prompt_content}]
    def _build_code_agent_refine_prompt(self, context: DebugContext, dialogue_history: List[Dict[str, str]], current_blueprint: any, is_pass: bool = False, orchestrator_intervention: Optional[str] = None, midterm_review_block: Optional[str] = None) -> List[Dict[str, str]]:
        """构建 PROMPT_C_CODE_AGENT_REFINE"""
        full_dialogue = self._format_dialogue_history(dialogue_history)
        latest_message = dialogue_history[-1]["content"] if dialogue_history else ""
        failed_blueprint = dialogue_history[-3]["content"] if dialogue_history else ""
        failed_blueprint =self._extract_blueprint_from_response(failed_blueprint)
        

        prompt_content = f"""### ROLE AND GOAL
You are CodeAgent. Your partner, SolutionAgent, has reviewed your previous blueprint and provided feedback based on the Supreme Law. Your goal is to carefully address the feedback and provide an improved blueprint.

### CORE CONTEXT (Your Unchanging Source of Truth)
1.  **The Supreme Law**: 
{context.problem_description}
{context.test_cases}
**You cannot redefine the Supreme Law (e.g., if the Supreme Law defines func(n) = func(a) + func(b), you cannot propose func(n) = func(a) * func(b)).**

### LATEST PARTNER'S CONTENT
{latest_message}

### YOUR TASK
Your response must be structured into two parts. You must carefully consider all feedback provided.

1.  `<RESPONSE_TO_CRITIQUE>`:
    *   **If `MIDTERM REVIEW INSIGHTS` is present**:
        *   **Acknowledge the Midterm Review First**: Start by explicitly stating the **"Forbidden Logic"** identified in the review. This proves you understand the core strategic failure.
        *   **Introduce the New Strategy**: Explain how your new blueprint's core algorithm is a **"Breakout Strategy"** that fundamentally avoids this forbidden logic.
        *   **Address Partner's Feedback**: After establishing the new strategy, explain how this new approach also resolves the specific points raised by your partner in the `<REFINEMENT_REQUEST>`.

    *   **If `MIDTERM REVIEW INSIGHTS` is NOT present**:
        *   **Acknowledge Partner's Feedback**: Briefly acknowledge the specific points raised in the `<REFINEMENT_REQUEST>`.
        *   **Critique Your Previous Logic**: Look at your own `<YOUR PREVIOUS BLUEPRINT>`. Briefly explain why its core logic failed to meet the Supreme Law, based on the partner's feedback. This demonstrates self-correction.
        *   **Explain the Fix**: Describe how your new blueprint's logic directly corrects the flaws you just identified.

2.  `<REFINED_BLUEPRINT>`:
    *   Provide the **new, complete** version of your pseudocode blueprint that incorporates the necessary changes.
    *   Ensure your new blueprint is a **full, standalone algorithm** that does not rely on any previous blueprint and avoids past logical errors.
    *   Do not write any output examples (e.g., print(func(3)) # its output value) in your blueprint.

### FINAL INSTRUCTIONS
*   The refined blueprint you provide should be a full, standalone algorithm.
"""
        
        return [{"role": "user", "content": prompt_content}]
    
    def _build_code_agent_retry_prompt(self, context: DebugContext, dialogue_history: List[Dict[str, str]], feedback: str) -> List[Dict[str, str]]:
        """构建CodeAgent重试提示词"""
        # 获取最后的提示词并添加反馈
        if len(dialogue_history) == 1:  # 首轮重试
            base_prompt = self._build_code_agent_propose_prompt(context, self._format_diagnosis_output(context))
        else:  # 修改轮重试
            base_prompt = self._build_code_agent_refine_prompt(context, dialogue_history[:-1], midterm_review_block=None)
        
        base_prompt[0]["content"] += f"\n\n### ORCHESTRATOR FEEDBACK:\n{feedback}"
        return base_prompt
    
    def _build_simulation_agent_prompt(self, context: DebugContext, dialogue_history: List[Dict[str, str]], orchestrator_intervention: Optional[str] = None, blueprint_override: Optional[str] = None) -> List[Dict[str, str]]:
        """构建 SimulationAgent 提示词"""
        latest_message = dialogue_history[-1]["content"] if dialogue_history else ""
        
        # 提取CodeAgent的蓝图内容 - 如果有override则使用override
        if blueprint_override:
            code_agent_blueprint = self._extract_blueprint_from_response(blueprint_override)
        else:
            code_agent_blueprint = self._extract_blueprint_from_response(latest_message)
        
        # 安全地解析expected_value中的JSON数据
        simulation_goal_text = "No simulation values found"
        if hasattr(context, 'expected_value') and context.expected_value and context.expected_value != "No error log provided":
            try:
                import json
                parsed_data = json.loads(context.expected_value)

                simulation_values = []
                for item in parsed_data:
                    # 1. 优先尝试获取 'simulation_value' (旧的 assert 格式)
                    if 'simulation_value' in item:
                        simulation_values.append(item['simulation_value'])

                    # 2. 如果没有，尝试获取 'input' (新的 Standard I/O 格式)
                    elif 'input' in item:
                        # 对于 Standard I/O，'input' 就是我们模拟的值
                        # 为了显示清晰，可以加个前缀，或者直接用 item['input']
                        simulation_values.append(f"Input: {item['input']}")

                    # 3. 如果都没有，给个默认值防止报错
                    else:
                        simulation_values.append("Unknown Input")

                simulation_goal_text = '; '.join(simulation_values) if simulation_values else "No simulation values found"

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self._log(f"[NODE_BLUEPRINT] ⚠️ 解析expected_value时出错: {e}")
                simulation_goal_text = "No simulation values found"

        intervention_block = (
            f"""
### ORCHESTRATOR INTERVENTION
**IMPORTANT**: The Orchestrator has intervened with new instructions. This may override your normal simulation process. Please prioritize the following command:

{orchestrator_intervention}

Follow the Orchestrator's new instructions. If the intervention asks you to perform a task different from the standard simulation, structure your response accordingly.
---"""
            if orchestrator_intervention
            else ""
        )
        
        prompt_content = f"""### ROLE AND GOAL
You are a SimulatorAgent. You are a dispossessed, step-by-step code execution engine. You do not analyze, critique, or judge. Your ONLY job is to simulate the provided blueprint and report the factual results with **maximum granularity**.

### CRITICAL SIMULATION RULE
**Your ONLY source for execution logic is the `Blueprint to Simulate`.** You are strictly forbidden from using any logic, formulas, or example values from the `Supreme Law` to execute steps. The `Supreme Law` is ONLY for the final comparison.

### YOUR CORE SIMULATION PROTOCOL: ATOMIC OPERATIONS
**You must break down every line of code into its most basic, atomic operations. Do not jump to conclusions, even for simple calculations.** You must "show your work" for every single step.

### CONTEXT

- **Blueprint to Simulate**:
{code_agent_blueprint}
{intervention_block}
3.  **The GOAL FOR SIMULATION **: 
{simulation_goal_text}

### YOUR TASK
You must manually simulate the `Blueprint to Simulate` following the **ATOMIC OPERATIONS** protocol. Your trace must be extremely detailed.
You must adhere to strict, unambiguous mathematical and logical rules.** For example, the comparison `3 > 3.0` is strictly **False**. Any deviation from standard computation rules will invalidate the entire simulation.

**Example of the Required Granularity and "Unpacking":**

 Consider this code snippet to simulate with an input of score = 90:

 def get_level(score):
     if score > 90:
         return "Good"
     elif score >= 80:
         return "Common"
     else:
         return "Basic"
 --- A BAD, FORBIDDEN trace would be: ---
 90 is not > 90, but it is >= 80, so it returns "Common".
 (This is a lazy summary and is not allowed)
 --- A GOOD, REQUIRED trace for an input of score = 90: ---
 - Calling function `get_level` with `score = 90`.
 - Line `if score > 90:`:
 -   Evaluating condition: `score > 90`.
 -   Substituting variable: `90 > 90`.
 -   The comparison evaluates to **False**.
 -   Skipping the `if` block, proceeding to `elif`.
 - Line `elif score >= 80:`:
 -   Evaluating condition: `score >= 80`.
 -   Substituting variable: `90 >= 80`.
 -   The comparison evaluates to **True**.
 -   Condition is True, entering the `elif` block.
 - Line `return "Common"`:
 -   Function returns the value `"Common"`
---
**If the blueprint provides an instruction that cannot be completed using ONLY the information within the blueprint itself (e.g., it asks for a value without specifying how to calculate it), you must do the following:**
1.  Stop execution at that exact point.
2.  In your `<TRACE>`, clearly state that the simulation is **BLOCKED** due to an ambiguous or incomplete instruction.
3.  Set the `<FINAL_OUTPUT>` to `INCOMPLETE`.


If the simulation can be completed, report the results as normal.

### FINAL INSTRUCTIONS
*   Do not add any explanation, critique, or refinement requests outside of the specified tags.
*   Your entire response must be enclosed in the `<SIMULATION_REPORT>` tag 

## The Official Simulation Report
This is your final, official output based on your pre-computation.

<SIMULATION_REPORT>
    <TRACE>
    [Your detailed, step-by-step trace of the execution,please attention the compare (eg. 3>3.0 is false,so it maps the B,1.7>1.7 is false ,so it maps C-, 2 >2.0 is false,so it maps C,3.5>3.7 is false & 3.5>3.0 is true, so it maps B+) and the corrsponse according to the blueprint]
    </TRACE>
    <FINAL_OUTPUT>
    [The final output produced by the code, or the error/crash that occurred.]
    </FINAL_OUTPUT>
</SIMULATION_REPORT>
"""
        
        return [{"role": "user", "content": prompt_content}]
    
    def _build_solution_analysis_prompt(self, context: DebugContext, simulation_response: str) -> List[Dict[str, str]]:
        """构建SolutionAgent基于模拟结果的分析提示词"""
        
        prompt_content = f"""### ROLE AND GOAL
You are SolutionAgent. Your mission is to perform a forensic analysis of a code failure based on the objective simulation results provided by a SimulationAgent.

Your goal is to act as a laser-focused analyst. You will not retell the story of the simulation. Instead, you will pinpoint the **single line of code** that is the origin of the failure and explain **why** it is the origin.

### CONTEXT FOR YOUR ANALYSIS
1.  **The Supreme Law (Problem Description & Ground Truth)**:
{context.problem_description}


### SIMULATION RESULTS FROM SIMULATIONAGENT
{simulation_response}

### YOUR CORE ANALYTICAL PROTOCOL
Your task is not to summarize the simulation, but to use it as evidence to find the single root cause. Follow this protocol:

1. **Identify the Golden Path**: Determine the expected sequence of states a correct program would generate based on the Ground Truth. (e.g., the target is [1, 3, 2, 8]).

2. **Find the First Divergence**: Compare the simulation trace, step-by-step, to the Golden Path. Identify the first moment the program's state deviates or the first illegal operation it attempts.

3. **Isolate the Culprit**: Pinpoint the single line of code in the Flawed Code responsible for that first divergence.

### YOUR TASK
Your response MUST be structured into the following three parts. The first two parts are new and designed for direct analysis. The final part remains for handoff.

#### **Part 1: The Root Cause Location**
`<FAILURE_LOGIC>...</FAILURE_LOGIC>`:
Based on the provided "step-by-step code tracing log", pinpoint the source code line of the failure logic. You must strictly follow these requirements:

*   **Clarify the Abnormal Variable First**: Based on the difference between the "expected output" and "actual output", identify which core variable (e.g., current_group/balance/result) first becomes abnormal? And copy the record of this variable’s first abnormal state from the tracing log.
*   **Locate the Faulty Logic Block**: Find the code **segment** in the tracing log that "should have modified the above abnormal variable but actually did not modify it/modified it incorrectly", and quote the entire relevant **block**.
*   **Describe the Pre-Execution State**: Extract the state of key variables immediately before the execution of this code line from the tracing log (must include at least: the value of the currently processed char, the value of the abnormal variable, and the value of balance).
*   **Verify the Logic Deviation**: Explain "what state the variable should be in if this code line were executed correctly" to prove that the absence/error of this code line is the root cause of the failure.


#### **Part 2: The Root Cause Analysis**
`<FAILURE_ANALYSIS>...</FAILURE_ANALYSIS>`:
*   **Purpose**: To explain why the **logic block** identified in `<FAILURE_LOGIC>` is the root cause of the failure.
*   **Action**: Provide a concise analysis that connects the culprit **logic block** to the Supreme Law or Ground Truth.
*   **Details**: Your explanation must clearly state the conflict. For example: "This line is the root cause because it initializes the list with [3], which is an immediate logical deviation from the Golden Path, which requires the list to begin with [1]."

#### **Part 3: The Investigative Handoff**
`<EXPLORATORY_QUESTION>...</EXPLORATORY_QUESTION>`:
*   **Purpose**: To officially hand over the investigation to `CodeAgent`.
*   **Action**: Formulate **one** clear, open-ended question that does not reveal specific details from your analysis.
*   **ULTIMATE CRITICAL CONSTRAINT**: Your question's text **MUST NOT** contain any specific details, variable names, or values from your trace (e.g., do not mention `result[i-3]`, `i=3`, `index 4`, etc.). Your question should only reference the *existence* of the deviation you stated and direct `CodeAgent` to begin their own analysis.

    *   **A-Grade Example (for any failure type)**:
        > "CodeAgent, the trace and deviation statement confirm at which point the code's behavior parted from the desired outcome. Your task is to conduct the first level of analysis: Examine the logic in the `Flawed Code` and compare it against the `Supreme Law`. What is the fundamental conflict that causes the deviation I identified?"


"""
        return [{"role": "user", "content": prompt_content}]


    def _build_simulation_agent_retry_prompt(self, context: DebugContext, dialogue_history: List[Dict[str, str]], feedback: str) -> List[Dict[str, str]]:
        """构建SimulationAgent重试提示词"""
        base_prompt = self._build_simulation_agent_prompt(context, dialogue_history[:-1])
        base_prompt[0]["content"] += f"\n\n### ORCHESTRATOR FEEDBACK:\n{feedback}"
        return base_prompt
    
    def _build_code_agent_refinement_from_quality_gate(self, context: DebugContext, dialogue_history: List[Dict[str, str]], quality_feedback: str) -> List[Dict[str, str]]:
        """构建CodeAgent质量门控反馈提示词"""
        prompt_content = f"""### ORCHESTRATOR QUALITY GATE FEEDBACK

{quality_feedback}

### CORE CONTEXT (Your Unchanging Source of Truth)
1.  **The Supreme Law**: {context.problem_description}
2.  **The Flawed Code**: 
```python
    {context.current_code or "No current code provided"}
```
3.  **The Failure Log**: {context.error_logs or "No failure log provided"}

### ADDITIONAL GUIDANCE
Remember that a concrete algorithm should:
- Use specific mathematical operations and variable assignments
- Define exactly HOW to compute each value (not just WHAT to compute)
- Be mechanically executable step-by-step without interpretation
- Avoid high-level concepts like "calculate the next triangular number" without specifying the exact formula

### REQUIRED OUTPUT FORMAT
Your response must contain the complete `<REFINED_BLUEPRINT>` tag pair with the improved, concrete algorithm inside.
the tag pair like this:<REFINED_BLUEPRINT>...</REFINED_BLUEPRINT>
"""
        
        return [{"role": "user", "content": prompt_content}]
    
    def _build_solution_agent_retry_prompt(self, context: DebugContext, dialogue_history: List[Dict[str, str]], feedback: str) -> List[Dict[str, str]]:
        """构建SolutionAgent重试提示词"""
        base_prompt = self._build_solution_agent_review_prompt(context, dialogue_history[:-1], midterm_review_block=None)
        base_prompt[0]["content"] += f"\n\n### ORCHESTRATOR FEEDBACK:\n{feedback}"
        return base_prompt
    
    def _extract_last_three_dialogue(self, dialogue_history: List[Dict[str, str]], enhanced_mode: bool) -> Dict[str, Optional[str]]:
        """提取最后三条对话记录 (code, simulation, solution)"""
        result = {"code": None, "simulation": None, "solution": None}
        
        if not dialogue_history:
            return result
        
        # 反向遍历对话历史，找到最后的三种角色的发言
        found_roles = set()
        target_roles = {"CodeAgent", "SolutionAgent"}
        if enhanced_mode:
            target_roles.add("SimulationAgent")
        
        for entry in reversed(dialogue_history):
            speaker = entry["speaker"]
            content = entry["content"]
            
            if speaker == "CodeAgent" and "code" not in found_roles:
                result["code"] = content
                found_roles.add("code")
            elif speaker == "SimulationAgent" and enhanced_mode and "simulation" not in found_roles:
                result["simulation"] = content
                found_roles.add("simulation")
            elif speaker == "SolutionAgent" and "solution" not in found_roles:
                result["solution"] = content
                found_roles.add("solution")
            
            # 如果已经找到所有需要的角色，提前退出
            expected_count = 3 if enhanced_mode else 2
            if len(found_roles) >= expected_count:
                break
        
        return result
    
    def _format_dialogue_history(self, dialogue_history: List[Dict[str, str]]) -> str:
        """格式化对话历史"""
        formatted = []
        for i, entry in enumerate(dialogue_history):
            speaker = entry["speaker"]
            content = entry["content"]
            formatted.append(f"=== {speaker} (Turn {i+1}) ===\n{content}\n")
        return "\n".join(formatted)
    
    def _extract_blueprint_from_response(self, response: str) -> str:
        """从回复中提取蓝图内容"""
        # 尝试提取不同的蓝图标签
        for tag in ["REFINED_BLUEPRINT", "INITIAL_BLUEPRINT","ALTERNATIVE_BLUEPRINT"]:
            # 1. 优先匹配 <TAG>content</TAG>
            match = re.search(rf'<{tag}>(.*?)</{tag}>', response, re.DOTALL)
            if match:
                return match.group(1).strip()

            # 2. 如果没有关闭标签，就匹配 <TAG>content（到行尾或字符串结尾）
            match = re.search(rf'<{tag}>(.*)', response, re.DOTALL)
            if match:
                return match.group(1).strip()
        return response  # 如果没有找到标签，返回整个回复
    
    def _check_dialogue_repetition(self, dialogue_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        检查对话是否陷入重复循环
        
        Returns:
            检测结果 {
                has_repetition: bool,
                repetition_type: str,  # "solution_agent", "code_agent", "both", "none"
                solution_check: Dict,  # SolutionAgent的重复检测详情
                code_check: Dict       # CodeAgent的重复检测详情
            }
        """
        if len(dialogue_history) < 4:
            return {
                "has_repetition": False,
                "repetition_type": "none",
                "solution_check": {"checked": False, "reason": "insufficient_history"},
                "code_check": {"checked": False, "reason": "insufficient_history"}
            }
        
        # 提取最近的消息
        recent_messages = dialogue_history[-4:]
        solution_messages = [msg["content"] for msg in recent_messages if msg["speaker"] == "SolutionAgent"]
        code_messages = [msg["content"] for msg in recent_messages if msg["speaker"] == "CodeAgent"]
        
        # 检查SolutionAgent重复性
        solution_check = {"checked": False}
        if len(solution_messages) >= 2:
            solution_check = self.quality_gate.check_content_repetition(
                solution_messages[-1], solution_messages[:-1], threshold=0.8
            )
            solution_check["checked"] = True
            if solution_check["is_repetitive"]:
                self._log(f"🔍 SolutionAgent重复检测: 相似度={solution_check['similarity_score']:.2f}, 分析={solution_check['llm_analysis'][:100]}...")
        else:
            solution_check["reason"] = "insufficient_messages"
        
        # 检查CodeAgent重复性  
        code_check = {"checked": False}
        if len(code_messages) >= 2:
            code_check = self.quality_gate.check_content_repetition(
                code_messages[-1], code_messages[:-1], threshold=0.8
            )
            code_check["checked"] = True
            if code_check["is_repetitive"]:
                self._log(f"🔍 CodeAgent重复检测: 相似度={code_check['similarity_score']:.2f}, 分析={code_check['llm_analysis'][:100]}...")
        else:
            code_check["reason"] = "insufficient_messages"
        
        # 判断重复类型
        solution_repetitive = solution_check.get("is_repetitive", False)
        code_repetitive = code_check.get("is_repetitive", False)
        
        if solution_repetitive and code_repetitive:
            repetition_type = "both"
        elif solution_repetitive:
            repetition_type = "solution_agent"
        elif code_repetitive:
            repetition_type = "code_agent"
        else:
            repetition_type = "none"
        
        has_repetition = repetition_type != "none"
        
        return {
            "has_repetition": has_repetition,
            "repetition_type": repetition_type,
            "solution_check": solution_check,
            "code_check": code_check
        }
    
    def _extract_code_from_blueprint(self, blueprint: str) -> str:
        """从蓝图中提取代码内容"""
        if not blueprint:
            return ""
        
        # 尝试提取代码块
        import re
        
        # 查找Python代码块
        code_patterns = [
            r'```python\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'<code>\s*(.*?)\s*</code>',
            r'<BLUEPRINT>\s*(.*?)\s*</BLUEPRINT>',
            r'<REFINED_BLUEPRINT>\s*(.*?)\s*</REFINED_BLUEPRINT>',
            r'<INITIAL_BLUEPRINT>\s*(.*?)\s*</INITIAL_BLUEPRINT>'
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, blueprint, re.DOTALL | re.IGNORECASE)
            if matches:
                # 返回第一个匹配的代码块
                return matches[0].strip()
        
        # 如果没有找到代码块，返回整个蓝图内容
        return blueprint.strip()
    
    def _extract_trace_from_simulation(self, simulation_response: str) -> str:
        """从模拟响应中提取追踪内容"""
        if not simulation_response:
            return ""
        
        import re
        
        # 查找TRACE标签中的内容
        trace_patterns = [
            r'<TRACE>\s*(.*?)\s*</TRACE>',
        ]
        
        for pattern in trace_patterns:
            matches = re.findall(pattern, simulation_response, re.DOTALL | re.IGNORECASE)
            if matches:
                # 返回第一个匹配的追踪内容
                return matches[0].strip()
        
        # 如果没有找到特定标签，尝试查找看起来像追踪的内容
        # 查找包含步骤描述的段落
        lines = simulation_response.split('\n')
        trace_lines = []
        in_trace_section = False
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['step', 'trace', 'execution', 'simulation', 'calling', 'evaluating', 'assignment']):
                in_trace_section = True
                trace_lines.append(line)
            elif in_trace_section and line and not line.startswith('<') and not line.startswith('#'):
                trace_lines.append(line)
            elif in_trace_section and (line.startswith('<') or line.startswith('#')):
                break
        
        if trace_lines:
            return '\n'.join(trace_lines)
        
        # 最后兜底，返回原始响应
        return simulation_response.strip()
    
    def _build_simulation_agent_retry_prompt_for_accuracy(self, context: DebugContext, dialogue_history: List[Dict[str, str]], quality_response: str) -> List[Dict[str, str]]:
        """构建SimulationAgent重试提示，专门用于提高模拟准确性"""
        # 获取最新的蓝图内容
        latest_code_message = None
        for msg in reversed(dialogue_history):
            if msg["speaker"] == "CodeAgent":
                latest_code_message = msg["content"]
                break
        
        latest_blueprint = self._extract_blueprint_from_response(latest_code_message) if latest_code_message else ""
        
        prompt_content = f"""### RETRY REQUEST FOR ACCURACY
Your previous simulation was rejected by the quality gate because it contained inaccuracies in the trace. Please regenerate the simulation with higher accuracy.

### QUALITY GATE FEEDBACK
The quality auditor provided the following detailed feedback about your previous simulation:

{quality_response}

### CONTEXT FOR RE-SIMULATION
**Problem Description**: {context.problem_description}
**Current Blueprint to Simulate**: 
{latest_blueprint}
**Failure Log**: {context.error_logs or "No failure log provided"}

### CRITICAL REQUIREMENTS FOR ACCURATE SIMULATION
Based on the quality gate feedback above, you must:
1. **Step-by-step precision**: Every calculation, variable assignment, and operation must be exactly correct.
2. **Verify each step**: Before reporting a result, double-check your calculation mentally.
3. **Match the blueprint exactly**: Your simulation must perfectly reflect what the blueprint actually does, not what you think it should do.
4. **Address specific inaccuracies**: Pay special attention to the specific issues identified in the quality gate feedback.

### YOUR TASK
Please re-simulate the blueprint with extreme precision, addressing the specific inaccuracies identified by the quality gate. Use the same output format as before:

```xml
<SIMULATION_REPORT>
    <TRACE>
    [Your corrected, step-by-step trace]
    </TRACE>
    <FINAL_OUTPUT>
    [The final output]
    </FINAL_OUTPUT>
    <COMPARISON>
    [Comparison with expected result]
    </COMPARISON>
    <CONCLUSION>
    [PASSED or FAILED]
    </CONCLUSION>
</SIMULATION_REPORT>
```"""

        return [{"role": "user", "content": prompt_content}]
    
    def _extract_alternative_blueprint_from_response(self, response: str) -> str:
        """
        从中期回顾响应中解析 ALTERNATIVE_BLUEPRINT 标签内容
        
        解析策略：
        1. 首先尝试解析双标签 <ALTERNATIVE_BLUEPRINT>...</ALTERNATIVE_BLUEPRINT>
        2. 如果没有找到闭合标签，就解析单标签 <ALTERNATIVE_BLUEPRINT> 后面的所有内容
        
        Args:
            response: 中期回顾的响应内容
            
        Returns:
            解析出的 ALTERNATIVE_BLUEPRINT 内容，如果没有找到则返回空字符串
        """
        if not response:
            return ""
        
        import re
        
        self._log("🔍 开始解析 ALTERNATIVE_BLUEPRINT 标签...")
        
        # 策略1: 尝试解析双标签 <ALTERNATIVE_BLUEPRINT>...</ALTERNATIVE_BLUEPRINT>
        double_tag_pattern = r'<ALTERNATIVE_BLUEPRINT>\s*(.*?)\s*</ALTERNATIVE_BLUEPRINT>'
        double_match = re.search(double_tag_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if double_match:
            self._log("✅ 找到双标签 ALTERNATIVE_BLUEPRINT")
            return double_match.group(1).strip()
        
        # 策略2: 如果没有找到双标签，尝试解析单标签后面的所有内容
        single_tag_pattern = r'<ALTERNATIVE_BLUEPRINT>\s*(.*)'
        single_match = re.search(single_tag_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if single_match:
            self._log("✅ 找到单标签 ALTERNATIVE_BLUEPRINT，解析后续所有内容")
            return single_match.group(1).strip()
        
        # 如果都没有找到，返回空字符串
        self._log("⚠️ 未找到 ALTERNATIVE_BLUEPRINT 标签")
        return ""

class ImplementationNode(DebugNode):
    """节点三: 最终代码实现"""
    
    def __init__(self, quality_gate: QualityGate, verbose: int = 1):
        super().__init__(NodeType.IMPLEMENTATION, quality_gate, verbose)
    
    def execute(self, context: DebugContext, agents: Dict[AgentRole, BaseAgent]) -> NodeResult:
        """
        执行实现节点
        
        目标: 将经过完整设计和测试的蓝图准确翻译成可执行的Python代码
        参与者: CodeAgent + Orchestrator
        """
        self._log("🎯 开始最终代码实现...")
        
        code_agent = agents[AgentRole.CODE_AGENT]
        grammar_checker = GrammarChecker(
            fixer_agent=code_agent,
            verbose=self.verbose,
            max_fix_attempts=2,
        )
        # 构建实现提示
        implementation_prompt = self._build_implementation_prompt(context)
        
        # CodeAgent 生成最终代码
        response = code_agent._call_model(implementation_prompt, include_history=False)
        
        # 验证格式
        format_check = self.quality_gate.validate_required_tags(response, ["FINAL_CODE"])
        
        if not format_check["valid"]:
            return NodeResult(
                success=False,
                error_message="最终代码格式错误，缺少FINAL_CODE标签"
            )
        
        # 提取最终代码
        final_code = self._extract_final_code(response)

        # 使用语法检查器检查代码（仅针对 Python 语言）
        grammar_summary = None
        if True:
            if self.verbose >= VERBOSE_MINIMAL:
                print("\n🧹 运行语法检查器 (pyflakes)...")

            grammar_context = {
                "problem_description": context.problem_description,
                "test_cases": context.test_cases if isinstance(context.test_cases, list) else [],
            }

            try:
                grammar_result = grammar_checker.ensure_clean(
                    final_code,
                    context=grammar_context,
                )
            except RuntimeError as exc:
                grammar_summary = {
                    "success": False,
                    "fixed": False,
                    "attempts": 0,
                    "report": str(exc),
                    "issues": [],
                    "history": [],
                    "error": str(exc),
                }
                
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"语法检查器不可用: {exc}")
            else:
                def _issue_to_dict(issue):
                    return {
                        "line": issue.line,
                        "column": issue.column,
                        "message": issue.message,
                        "raw": issue.raw,
                    }

                grammar_summary = {
                    "success": grammar_result.success,
                    "fixed": grammar_result.fixed,
                    "attempts": grammar_result.attempts,
                    "report": grammar_result.report,
                    "issues": [_issue_to_dict(it) for it in grammar_result.issues],
                    "history": grammar_result.history,
                }

                final_code = grammar_result.code


                if self.verbose >= VERBOSE_MINIMAL:
                    status = "通过" if grammar_result.success else "失败"
                    print(f"语法检查结果: {status}")
                    if not grammar_result.success and grammar_result.issues:
                        for issue in grammar_result.issues[:5]:
                            loc = f"行 {issue.line}" if issue.line else "未知位置"
                            print(f"  - {loc}: {issue.message}")


        if not final_code:
            return NodeResult(
                success=False,
                error_message="无法提取最终Python代码"
            )
        
        self._log("✅ 最终代码生成完成")
        context.final_code = final_code
        
        return NodeResult(
            success=True,
            output={"final_code": final_code, "response": response},
            next_node=NodeType.VALIDATION
        )
    
    def _build_implementation_prompt(self, context: DebugContext) -> List[Dict[str, str]]:
        """构建实现提示"""
        
        # 构建模拟分析部分
        simulation_section = ""
        if context.simulation:
            simulation_section = f"""
### THE SIMULATION ANALYSIS (For Your Understanding)
Here is the simulation analysis that validated the blueprint:
{context.simulation}
"""

        # 构建最终审查部分
        solution_section = ""
        if context.solution:
            solution_section = f"""
### THE APPROVAL RATIONALE (For Your Understanding)
Here is the final review and approval from SolutionAgent:
{context.solution}
"""
        
        prompt_content = f"""### ROLE AND GOAL
You are CodeAgent, a **senior software engineer**. The design phase is complete. Your final task is to construct the production-ready code by **integrating** the `Supreme Law`'s requirements for base cases with the core logic from the `Approved Blueprint`.

### CORE CONTEXT (Your Unchanging Source of Truth)
1.  **The Supreme Law**: 
{context.problem_description}

### THE FINAL APPROVED BLUEPRINT (Your Implementation Specification)
This is the blueprint that has been successfully simulated and approved. You must implement its logic for the general case (`n >= 2`).
{context.blueprint}


### YOUR TASK
Your response must demonstrate a professional engineering process by first creating a plan and then writing the code. It MUST contain **two** distinct parts, in order.

1.  `<IMPLEMENTATION_PLAN>`:
    *   Before writing any code, you must articulate your integration plan.
    *   Your plan **MUST** explicitly address how you will combine the different sources of truth to create a single, cohesive algorithm:
        1.  **Base Cases (`n=0`, `n=1`)**: Based on the **`Supreme Law`**, how will you correctly initialize and handle the outputs for `n=0` and `n=1`? Your logic here must be robust and not a simple hardcoded list.
        2.  **General Case (`n>=2`)**: How will you implement the main loop **exactly as specified in `THE FINAL APPROVED BLUEPRINT`** to handle all remaining cases?

2.  `<FINAL_CODE>`:
    *   Based on your integration plan, provide the complete, final Python function.
    *   The code must be clean, well-commented, and its structure must directly follow the logic you outlined in your `<IMPLEMENTATION_PLAN>`.
    *   ensure the finalcode's signature is the supreme law's definition
    *   Match the supreme law's function name and parameters
    *   the helper functions like this (the supreme law define the func_a and func_b,but the func_a help the func_b ,when you implement the func_b,you must write the func_a first)
---
### REQUIRED OUTPUT FORMAT
```xml
<IMPLEMENTATION_PLAN>
[Your detailed plan addressing the two required components: Base Cases (from Supreme Law) and the General Case (from the Blueprint).]
</IMPLEMENTATION_PLAN>
<FINAL_CODE>
[Your final, robust Python code that implements the plan.Including the helper function if exits]
</FINAL_CODE>
"""
        
        return [
            {"role": "user", "content": prompt_content}
        ]
    
    def _extract_final_code(self, response: str) -> str:
        """提取最终代码 - 支持双标签和单标签格式"""
        # 首先尝试提取双标签格式 <FINAL_CODE>...</FINAL_CODE>
        match = re.search(r'<FINAL_CODE>(.*?)</FINAL_CODE>', response, re.DOTALL)
        if match:
            code = match.group(1).strip()
            # 移除可能的代码块标记
            if code.startswith('```python'):
                code = code[9:]
            elif code.startswith('```'):
                code = code[3:]
            if code.endswith('```'):
                code = code[:-3]
            return code.strip()
        
        # 双标签匹配失败，尝试查找单标签 FINAL_CODE 后的代码
        # 查找 FINAL_CODE 标签后的内容（可能有冒号或其他分隔符）
        single_tag_patterns = [
            r'FINAL_CODE[:\s]*\n(.*?)(?=\n\S|\Z)',  # FINAL_CODE: 或 FINAL_CODE 后跟换行
            r'<FINAL_CODE[^>]*>\s*(.*?)(?=\n<|\Z)',  # 单开标签，如 <FINAL_CODE>
            r'```python\s*#\s*FINAL_CODE\s*(.*?)```',  # 在代码块中的注释形式
        ]
        
        for pattern in single_tag_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                # 移除可能的代码块标记
                if code.startswith('```python'):
                    code = code[9:]
                elif code.startswith('```'):
                    code = code[3:]
                if code.endswith('```'):
                    code = code[:-3]
                return code.strip()
        
        # 所有模式都匹配失败，返回空字符串
        return ""

class ValidationNode(DebugNode):
    """节点四: 自动验证与裁决"""
    
    def __init__(self, quality_gate: QualityGate, verbose: int = 1):
        super().__init__(NodeType.VALIDATION, quality_gate, verbose)
    
    def execute(self, context: DebugContext, agents: Dict[AgentRole, BaseAgent]) -> NodeResult:
        """
        执行验证节点
        
        目标: 对最终代码进行实机测试，做出最终的"通过"或"失败"裁决
        参与者: Orchestrator(唯一行动者)
        """
        self._log("🎯 开始自动验证与裁决...")
        
        if not context.final_code:
            return NodeResult(
                success=False,
                error_message="没有可验证的最终代码"
            )
        
        # 执行代码验证
        validation_result = self._validate_code(context,context.final_code, context.test_cases)
        
        if validation_result["passed"]:
            self._log("✅ 代码验证通过，流程成功完成")
            return NodeResult(
                success=True,
                output={
                    "validation_result": validation_result,
                    "final_code": context.final_code
                }
            )
        else:
            self._log(f"❌ 代码验证失败: {validation_result['error']}")
            context.error_logs = validation_result.get("test_result", "No detailed test result available.")
            
            # 累积历史失败代码：将新的失败代码添加到历史记录中
            if isinstance(context.current_code, list):
                # 如果已经是列表，在开头插入最新的失败代码
                context.current_code.insert(0, context.final_code)
            elif context.current_code is not None:
                # 如果当前是字符串，转换为列表格式
                context.current_code = [context.final_code, context.current_code]
            else:
                # 如果当前为空，直接设置为最新失败代码
                context.current_code = context.final_code
            
            context.error_logs = f"Validation failed: {validation_result['error']}\n\n"
            return NodeResult(
                success=False,
                output={"validation_result": validation_result},
                rollback_to=NodeType.DIAGNOSIS,
                error_message=f"代码验证失败: {validation_result['error']}"
            )
    
    def _validate_code(self,context: DebugContext, code: str, test_cases: List[Any]) -> Dict[str, Any]:
        """验证代码"""
        try:
            # 导入调试智能体进行代码测试
            from agents.core.DebugAgent import DebugAgent
            
            debug_agent = DebugAgent(verbose=self.verbose)
            
            # # 使用调试智能体的测试功能
            # test_result = debug_agent.test_with_sample_io(
            #     code=code, 
            #     sample_io=test_cases, 
            #     timeout=10
            # )
            if context.is_competive :
                # APPS: 使用 ExecEval 测试（input/output 格式）
                if self.verbose >= VERBOSE_MINIMAL:
                    print("使用 ExecEval 测试 APPS 代码...")

                sample_io_passed, test_log = context.dataset.evaluate_sample_io(
                    item=context.item,
                    code=code,
                    language='Python3'
                )

                # 构建与 DebugAgent 兼容的结果格式
                sample_io_result = {
                    "success": sample_io_passed,
                    "output": test_log,
                    "error": "" if sample_io_passed else test_log,
                    "error_type": None if sample_io_passed else "ExecEval",
                    "failed_tests": [] if sample_io_passed else [{"test": "APPS test", "error": test_log}]
                }
            else :
                # HumanEval/MBPP: 使用 DebugAgent 本地测试（assert 语句）
                if self.verbose >= VERBOSE_MINIMAL:
                    print("使用本地执行测试代码...")

                sample_io_result = debug_agent.test_with_sample_io(
                    code=code,
                    sample_io=test_cases,
                    timeout=10
                )
                sample_io_passed = sample_io_result["success"]

            test_result=sample_io_result
            # 检查是否有失败的测试
            failed_tests = test_result.get("failed_tests", [])
            
            if not failed_tests:
                return {
                    "passed": True,
                    "error": None,
                    "test_result": test_result
                }
            else:
                error_details = []
                for failed_test in failed_tests:
                    error_details.append(f"测试失败: {failed_test.get('test', '')}, 错误: {failed_test.get('error', '')}")
                
                return {
                    "passed": False,
                    "error": "; ".join(error_details),
                    "test_result": test_result
                }
                
        except Exception as e:
            return {
                "passed": False,
                "error": f"代码执行异常: {str(e)}",
                "test_result": None
            }
    
    # ===== 兼容性方法 (为其他节点保留) =====
    
    def _build_initial_blueprint_prompt(self, context: DebugContext, guiding_question: str) -> List[Dict[str, str]]:
        """构建初始蓝图设计提示 - 兼容性方法"""
        return self._build_code_agent_propose_prompt(context, self._format_diagnosis_output(context))
    
    def _build_review_prompt(self, context: DebugContext, blueprint: str, code_response: str) -> List[Dict[str, str]]:
        """构建蓝图审查提示 - 兼容性方法"""
        dialogue_history = [{"speaker": "CodeAgent", "content": code_response}]
        return self._build_solution_agent_review_prompt(context, dialogue_history, midterm_review_block=None)
    
    def _build_refinement_prompt(self, context: DebugContext, refinement_request: str) -> List[Dict[str, str]]:
        """构建蓝图改进提示 - 兼容性方法"""
        # 构建模拟的对话历史
        dialogue_history = [
            {"speaker": "CodeAgent", "content": "Previous blueprint"},
            {"speaker": "SolutionAgent", "content": f"<REFINEMENT_REQUEST>{refinement_request}</REFINEMENT_REQUEST>"}
        ]
        return self._build_code_agent_refine_prompt(context, dialogue_history, midterm_review_block=None)
    
    def _extract_blueprint(self, response: str) -> str:
        """提取蓝图内容 - 兼容性方法"""
        return self._extract_blueprint_from_response(response)


class TimeoutHandlerNode(DebugNode):
    """超时处理节点 - 处理蓝图设计阶段的超时情况"""
    
    def __init__(self, quality_gate: QualityGate, verbose: int = 1):
        super().__init__(NodeType.TIMEOUT_HANDLER, quality_gate, verbose)
    
    def execute(self, context: DebugContext, agents: Dict[AgentRole, BaseAgent]) -> NodeResult:
        """
        执行超时处理节点
        
        目标: 在蓝图设计阶段超时后，进行最后的突破性尝试
        参与者: CodeAgent (作为BreakthroughAgent)
        """
        self._log("🚨 开始超时处理 - 最终突破尝试...")
        
        code_agent = agents[AgentRole.CODE_AGENT]
        
        # # 从context中获取对话历史
        dialogue_history = context.dialogue_history or []
        
        # # 解析对话历史，提取solution和code的内容
        # solution_content = self._extract_solution_content(dialogue_history)
        code_content = self._extract_code_content(dialogue_history)
        if context.timeout == False:
            code_content = context.current_code
        auditor_response = []
        for code_content_item in code_content:
            prompt = self._build_CodeAuditor_prompt(context, code_content_item)
            response = code_agent._call_model(prompt, include_history=False)

            #解析内容
            response = self._extract_flaw_diagnosis(response)
            
            auditor_response.append(response)
        

        # 构建超时处理提示
        timeout_prompt = self._build_timeout_handler_prompt(context, auditor_response)
        
        # CodeAgent 进行最终突破尝试
        response = code_agent._call_model(timeout_prompt, include_history=False)
        
        # 验证格式 - 检查必需的标签
        required_tags = ["FAILURE_REFLECTION", "FINAL_BLUEPRINT"]
        format_check = self.quality_gate.validate_required_tags(response, required_tags)
        
        if not format_check["valid"]:
            self._log(f"❌ 格式检查失败: {format_check['missing_tags']}")
            return NodeResult(
                success=False,
                error_message=f"超时处理响应格式错误，缺少标签：{format_check['missing_tags']}"
            )
        
        # 提取最终蓝图与反思
        final_blueprint = self._extract_final_blueprint(response)
        if not final_blueprint:
            return NodeResult(
                success=False,
                error_message="无法提取FINAL_BLUEPRINT内容"
            )
        failure_reflection = self._extract_failure_reflection(response)
        
        self._log("✅ 超时处理完成 - 获得突破性蓝图")
        
        # 更新context
        context.blueprint = final_blueprint
        
        return NodeResult(
            success=True,
            output={
                "timeout_response": response,
                "final_blueprint": final_blueprint,
                "failure_reflection": failure_reflection,
                "auditor_response": auditor_response
            },
            next_node=NodeType.IMPLEMENTATION
        )
    
    def _extract_solution_content(self, dialogue_history: List[Dict[str, str]]) -> List[str]:
        """从对话历史中提取SolutionAgent的所有内容"""
        solution_content = []
        for entry in dialogue_history:
            if entry["speaker"] == "SolutionAgent":
                solution_content.append(entry["content"])
        return solution_content
    
    def _extract_code_content(self, dialogue_history: List[Dict[str, str]]) -> List[str]:
        """从对话历史中提取CodeAgent的所有内容"""
        code_content = []
        for entry in dialogue_history:
            if entry["speaker"] == "CodeAgent":
                content = self._extract_blueprint_from_response(entry["content"])
                code_content.append(content)
        return code_content
    
    def _build_timeout_handler_prompt(self, context: DebugContext,auditor_response : List[str] ) -> List[Dict[str, str]]:
        """构建超时处理的提示词"""
        
        
        prompt_content = f"""
### **ROLE AND GOAL**

You are **`SynthesisGrandmasterAgent`**. All previous attempts to solve this problem have failed. You have been provided with a **complete forensic analysis** of every single past failure, in the form of a "Failure DNA List".

Your mission is to **transcend all past errors**. You will first **reflect** on the entire history of failure to synthesize a single "Immunity Principle", and then, you will use this principle to formulate a **new, superior, and final blueprint**.

---

### **INPUTS FOR YOUR SYNTHESIS**

1.  **The Supreme Law**: The ultimate source of truth.
    `{context.problem_description}`
2.  **The "Failure DNA List"**: A list of the core logical flaws from every past attempt. This is your primary evidence.
    `{auditor_response}`

---

### **YOUR TASK & OUTPUT FORMAT**

You MUST provide your response in the following **two-part format, in this exact order**.

---
#### **PART 1: THE REFLECTION (Synthesizing the Meta-Flaw)**

<FAILURE_REFLECTION>
1.  **The Persistent Failure Pattern (The Meta-Flaw)**: First, you must read the entire `Failure DNA List` and identify the **single, recurring, high-level "meta-flaw"** that connects all the individual failures.
2.  **The Unresolved Challenge**: Based on this meta-flaw, you must state the single, most critical **"Unresolved Challenge"** that your new blueprint must now solve. This is the final boss.
    *   **A-Grade Example (Generalized)**:
        > "**Persistent Failure Pattern**: The `Failure DNA List` reveals a repeated failure to implement the main recurrence relation correctly, specifically when it involves a dependency on an uncomputed value.
        > **The Unresolved Challenge**: The final task is to find a specific, implementable algorithm that correctly resolves the complex dependency identified in the recurrence relation."

</FAILURE_REFLECTION>

---
#### **PART 2: THE FINAL BLUEPRINT (via Algorithmic Ladder Ascent)**

<FINAL_BLUEPRINT>
[You will now construct your final blueprint. Your thought process **MUST** follow the "Algorithmic Thinking Ladder" to solve the `Unresolved Challenge` defined above.

**1. Ascending the Ladder (Your documented thought process):**
*   **Layer 1: Basic Toolkit (Direct Simulation)**
    *   **Attempt & Analysis**: [Attempt to solve the `Unresolved Challenge` with a direct simulation. Explain why it fails. **Crucially, re-examine the `Supreme Law`'s examples.** State any "Hidden Truth" you discover here.]
*   **Layer 2: Intermediate Paradigms**
    *   *(If needed)* **Attempt & Analysis**: [Attempt to solve the `Unresolved Challenge` with intermediate paradigms.]
*   **Layer 3: Advanced Paradigms**
    *   *(If needed)* **Attempt & Analysis**: [Attempt to solve the `Unresolved Challenge` with advanced paradigms.]

**2. The "Eureka Insight" (The Winning Strategy):**
*   [This is your most critical output. State the **Winning Strategy** you discovered during your ladder ascent. This MUST be the **simplest, lowest-level strategy** that successfully solves the `Unresolved Challenge`. You MUST explain how your insight (often a "Hidden Truth" from Layer 1) makes this strategy work.]
    *   **A-Grade Eureka Example (Generalized)**:
        > "**Winning Strategy**: The winning strategy was discovered at **Layer 1**. The `Unresolved Challenge` (a complex dependency) is an illusion. The 'Hidden Truth' from the `Supreme Law`'s examples is that the condition triggering the complex dependency *itself* falls under a special case, for which a simple, direct formula is provided elsewhere in the rules. Therefore, the winning strategy is a **simple, forward, single-pass iteration**, where the complex dependency is resolved by a **direct substitution** of the simpler formula. The complexity was in meticulous rule-connection, not advanced algorithms."

**3. The Final Code:**
*   [Provide the complete, final Python code that is a direct and flawless implementation of your `Winning Strategy`.]
]
</FINAL_BLUEPRINT>
"""
        
        return [{"role": "user", "content": prompt_content}]
    

    def _build_CodeAuditor_prompt(self, context: DebugContext, code_content: str) -> List[Dict[str, str]]:
        """构建CodeAuditor的提示词"""
        prompt_content = f"""
### **ROLE AND GOAL**
You are CodeAuditorAgent, a high-speed code auditor. Your goal is to identify **the primary logical flaw in a blueprint's *code***.

### **THE SUPREME LAW: HOW THE CODE *MUST* BEHAVE**
This law has two parts. The second part is the absolute, unyielding rule.

#### Part 1 (Ambiguous General Description - Use with caution):
{context.problem_description}

#### Part 2 (The Unyielding Rule - THIS IS THE TRUE REQUIREMENT):
{context.test_cases}

### **THE FLAWED BLUEPRINT**
This blueprint contains flawed code and a misleading self-analysis.
{code_content}

### **YOUR MISSION & CRITICAL AUDIT PROCEDURE**
Your task is to find the flaw in the blueprint's **code**. You must follow this procedure strictly:

1.  **STEP 1: DEDUCE THE TRUE RULE.** Look *only* at `Part 2 (The Unyielding Rule)`. From this example, deduce the non-obvious requirements. Ask yourself: "Does the order of numbers inside a tuple matter? Must the tuples be transformed or normalized before counting?" This example is your **only source of truth**.

2.  **STEP 2: IGNORE THE BLUEPRINT'S OWN ANALYSIS.** The commentary inside `code_content` is written by the author of the flawed code. **Their analysis is wrong and designed to mislead you.** Do not let it influence your judgment. You are smarter than the blueprint's author.

3.  **STEP 3: AUDIT THE CODE AGAINST THE TRUE RULE.** Compare the blueprint's `<REFINED_BLUEPRINT>` code against the true requirements you deduced in STEP 1. Identify precisely where the code's logic fails to meet the requirements of `The Unyielding Rule`.

4.  **STEP 4: STATE THE FLAW.** Based on your audit in Step 3, state the primary logical flaw of the code in a single sentence.

### **TASK**
Execute the procedure above. In a single, concise sentence, identify the primary logical flaw of the blueprint's code when compared to the Supreme Law. Do not propose a fix. Just state the error.

### **OUTPUT FORMAT**
<UnyieldingRule>
find the unyielding rule from part 2
</UnyieldingRule>
<FLAW_DIAGNOSIS>
[Your one-sentence diagnosis of the code's flaw.]
</FLAW_DIAGNOSIS>

        """
        return [{"role": "user", "content": prompt_content}]


    def _extract_flaw_diagnosis(self, response: str) -> str:
        """从 CodeAuditor 响应中提取 <FLAW_DIAGNOSIS> 内容，大小写不敏感，支持单开标签兜底。"""
        if not response:
            return ""
        match = re.search(r'<FLAW_DIAGNOSIS>\s*(.*?)\s*</FLAW_DIAGNOSIS>', response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        open_tag = re.search(r'<FLAW_DIAGNOSIS>\s*(.*)', response, re.DOTALL | re.IGNORECASE)
        if open_tag:
            tail = open_tag.group(1).strip()
            closer = re.search(r'(.*?)\s*</[^>]+>', tail, re.DOTALL)
            return (closer.group(1) if closer else tail).strip()
        return ""

    def _extract_failure_reflection(self, response: str) -> str:
        """从超时阶段响应中提取 <FAILURE_REFLECTION> 内容。"""
        match = re.search(r'<FAILURE_REFLECTION>(.*?)</FAILURE_REFLECTION>', response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_final_blueprint(self, response: str) -> str:
        """从超时阶段响应中提取 <FINAL_BLUEPRINT> 内容；支持双标签与单开标签兜底。"""
        if not response:
            return ""
        double_match = re.search(r'<FINAL_BLUEPRINT>\s*(.*?)\s*</FINAL_BLUEPRINT>', response, re.DOTALL | re.IGNORECASE)
        if double_match:
            return double_match.group(1).strip()
        single_match = re.search(r'<FINAL_BLUEPRINT>\s*(.*)', response, re.DOTALL | re.IGNORECASE)
        if single_match:
            return single_match.group(1).strip()
        return ""

    def _extract_blueprint_from_response(self, response: str) -> str:
        """从回复中提取蓝图内容"""
        # 尝试提取不同的蓝图标签
        for tag in ["REFINED_BLUEPRINT", "INITIAL_BLUEPRINT","ALTERNATIVE_BLUEPRINT"]:
            # 1. 优先匹配 <TAG>content</TAG>
            match = re.search(rf'<{tag}>(.*?)</{tag}>', response, re.DOTALL)
            if match:
                return match.group(1).strip()

            # 2. 如果没有关闭标签，就匹配 <TAG>content（到行尾或字符串结尾）
            match = re.search(rf'<{tag}>(.*)', response, re.DOTALL)
            if match:
                return match.group(1).strip()
        return response  # 如果没有找到标签，返回整个回复