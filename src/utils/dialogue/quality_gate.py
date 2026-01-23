"""
质量门控系统 - 负责评估各节点的输出质量
"""

import re
from typing import Dict, Any, Optional, List
from agents.BaseAgent import BaseAgent
from models.Base import BaseModel
from constants.verboseType import *

class QualityGate:
    """
    质量门控系统
    使用辅助LLM进行质量评估，确保每个节点的输出达到标准
    """
    
    def __init__(self, model: BaseModel, verbose: int = 1):
        """
        初始化质量门控
        
        Args:
            model: 用于质量评估的LLM模型
            verbose: 输出详细程度
        """
        self.model = model
        self.verbose = verbose
        
    def evaluate_diagnosis_depth(self, diagnosis_result: Dict[str, str], problem_context: str) -> Dict[str, Any]:
        """
        评估诊断分析的质量 - 两步验证：一致性审查 + 问题质量审查
        
        Args:
            diagnosis_result: 包含三个部分的诊断结果字典
            problem_context: 问题上下文
            
        Returns:
            评估结果 {is_deep: bool, feedback: str, classification: str, consistency_check: str, purity_check: str}
        """
        computational_trace = diagnosis_result.get("computational_trace", "")
        deviation_statement = diagnosis_result.get("deviation_statement", "")
        exploratory_question = diagnosis_result.get("exploratory_question", "")
        
        # 检测任务1: 一致性审查 (Internal Consistency Check)
        consistency_prompt = f"""### ROLE
You are a meticulous auditor bot. Your sole function is to check for logical consistency between a body of evidence and a conclusion. You do not judge the correctness of the evidence itself, only whether the conclusion is a direct and faithful summary of it.

### FULL PROBLEM CONTEXT
This audit is related to the following programming problem:
- **Problem Description**: {problem_context}

### CONTEXT
An AI assistant has produced a factual trace of a program's execution and a statement summarizing the direct cause of the program's failure. Your task is to verify if the statement is directly and logically supported by the facts presented in the trace.

### EVIDENCE: The Computational Trace
{computational_trace}

### CONCLUSION: The Deviation Statement
{deviation_statement}

### YOUR TASK
Carefully read the **EVIDENCE** and the **CONCLUSION**.
Does the conclusion directly follow from the facts presented in the evidence?

- Answer **CONSISTENT** if the statement is a direct summary of an event explicitly shown in the trace. For example, if the trace shows an `IndexError` at index 4, and the statement says the error was an `IndexError` at index 4.
- Answer **INCONSISTENT** if the statement makes a claim that is not supported by, or contradicts, the information in the trace. For example, if the trace shows the error happened at `i=3`, but the statement claims it happened at `i=2`.

### OUTPUT FORMAT
Your entire response must be a single word: **CONSISTENT** or **INCONSISTENT**. Do not add any other text, explanation, or punctuation."""
        
        consistency_response = self.model.chat([{"role": "user", "content": consistency_prompt}])
        consistency_check = consistency_response.strip().upper()
        
        # 检测任务2: 问题质量审查 (Question Purity Check)
        purity_prompt = f"""### ROLE
You are a Socratic method expert bot. Your function is to evaluate the quality of a question based on a strict pedagogical principle: a good question guides a student to discover an answer for themselves, while a bad question spoils the answer by giving away too many clues.

### FULL PROBLEM CONTEXT
This audit is related to the following programming problem:
- **Problem Description**: {problem_context}

### CONTEXT
An AI assistant has analyzed a code failure and must now pose a question to its partner to start a discussion. The question must guide the partner to investigate the facts, but it is strictly forbidden from hinting at the solution.

**Spoilers** include:
- Mentioning specific implementation details (e.g., "loop direction", "array size", "recursion").
- Referencing specific data points from the analysis (e.g., "result[i-3]", "index 4", "the value 6").

A **pure** question should only:
- Reference the existence of a deviation.
- Point the partner to the source documents (the code and the requirements) to conduct their own analysis.

### THE QUESTION TO EVALUATE:
{exploratory_question}

### YOUR TASK
Analyze the question provided above. Does it guide the partner to perform their own analysis, or does it spoil the answer by including forbidden hints?

- Answer **GUIDING** if the question is pure and follows the rules.
- Answer **SPOILING** if the question contains any of the forbidden hints mentioned in the context.

### OUTPUT FORMAT
Your entire response must be a single word: **GUIDING** or **SPOILING**. Do not add any other text, explanation, or punctuation."""
        
        purity_response = self.model.chat([{"role": "user", "content": purity_prompt}])
        purity_check = purity_response.strip().upper()
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n[QualityGate] 诊断分析质量评估结果:")
            print(f"  - 一致性审查: {consistency_check}")
            print(f"  - 问题质量审查: {purity_check}")

        # 只有两个检测都通过才算通过
        is_consistent = consistency_check == "CONSISTENT"  # 结论忠于事实
        is_guiding = purity_check == "GUIDING"            # 问题很好
        is_deep = is_consistent and is_guiding
        
        # 根据2x2失败情况矩阵生成精确的反馈
        if is_consistent and is_guiding:
            # Case A: 成功 (CONSISTENT + GUIDING)
            feedback = "Perfect analysis. Both trace-conclusion consistency and question purity passed."
            classification = "DEEP"
            action_required = "approve"
            
        elif is_consistent and not is_guiding:
            # Case B: 结论正确，但问题作弊 (CONSISTENT + SPOILING)
            feedback = """Your `<COMPUTATIONAL_TRACE>` and `<DEVIATION_STATEMENT>` were accurate and consistent. However, your `<EXPLORATORY_QUESTION>` spoiled the solution by including specific details from your analysis.

**Your new task:** Please preserve your original trace and statement, but **rewrite only the question** to be more abstract and open-ended, as per the original instructions."""
            classification = "SURFACE"
            action_required = "retry_question_only"
            
        elif not is_consistent and is_guiding:
            # Case C: 结论错误，但问题碰巧写得好 (INCONSISTENT + GUIDING)
            feedback = """There is a critical failure in your analysis. Your `<DEVIATION_STATEMENT>` is not consistent with the facts presented in your `<COMPUTATIONAL_TRACE>`. The conclusion you drew is not supported by the evidence.

**Your new task:** Discard your previous statement and question. Please **re-analyze your trace** with extreme care and write a new deviation statement that is a direct, logical summary of the facts."""
            classification = "SURFACE"
            action_required = "retry_full_analysis"
            
        else:
            # Case D: 双重失败 (INCONSISTENT + SPOILING)
            feedback = """There is a critical failure in your analysis. Your `<DEVIATION_STATEMENT>` is not consistent with the facts presented in your `<COMPUTATIONAL_TRACE>`. The conclusion you drew is not supported by the evidence.

**Your new task:** Discard your previous statement and question. Please **re-analyze your trace** with extreme care and write a new deviation statement that is a direct, logical summary of the facts."""
            classification = "SURFACE"
            action_required = "retry_full_analysis"
        
        return {
            "is_deep": is_deep,
            "classification": classification,
            "feedback": feedback,
            "action_required": action_required,
            "consistency_check": consistency_check,  # 结论
            "purity_check": purity_check,            # 问题
            "raw_consistency_response": consistency_response,
            "raw_purity_response": purity_response
        }
    
    def evaluate_blueprint_approval(self, solution_response: str) -> Dict[str, Any]:
        """
        评估SolutionAgent的回复是否表示批准蓝图
        
        Args:
            solution_response: SolutionAgent的回复内容
            
        Returns:
            评估结果 {is_approval: bool, confidence: float, reasoning: str}
        """
        # 首先检查是否包含REFINEMENT_REQUEST标签
        has_refinement_request = bool(re.search(r'<REFINEMENT_REQUEST>', solution_response, re.IGNORECASE))
        
        if has_refinement_request:
            return {
                "is_approval": False,
                "confidence": 1.0,
                "reasoning": "包含REFINEMENT_REQUEST标签，明确要求修改"
            }
        
        # 使用LLM判断意图
        prompt = f"""
你需要判断以下SolutionAgent的回复意图是"批准蓝图"还是"要求修改"。

SolutionAgent回复：
{solution_response}

请仔细分析回复的语气、用词和结论，判断其真实意图。

回复格式：
<INTENT_ANALYSIS>
意图: [批准/要求修改]
置信度: [0.0-1.0]
理由: [分析推理过程]
</INTENT_ANALYSIS>
"""
        
        response = self.model.chat([{"role": "user", "content": prompt}])
        
        # 解析LLM评估结果
        analysis_match = re.search(r'<INTENT_ANALYSIS>(.*?)</INTENT_ANALYSIS>', response, re.DOTALL)
        if analysis_match:
            content = analysis_match.group(1).strip()
            
            # 提取意图
            intent_match = re.search(r'意图:\s*([^\\n]+)', content)
            is_approval = False
            if intent_match:
                intent = intent_match.group(1).strip()
                is_approval = "批准" in intent
            
            # 提取置信度
            confidence_match = re.search(r'置信度:\s*([0-9.]+)', content)
            confidence = 0.5
            if confidence_match:
                confidence = float(confidence_match.group(1))
            
            # 提取理由
            reasoning_match = re.search(r'理由:\s*([^\\n]+)', content)
            reasoning = ""
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            
            return {
                "is_approval": is_approval,
                "confidence": confidence,
                "reasoning": reasoning,
                "raw_response": response
            }
        
        # 如果解析失败，返回保守判断
        return {
            "is_approval": False,
            "confidence": 0.3,
            "reasoning": "无法解析LLM评估结果，采用保守策略",
            "raw_response": response
        }
    
    def validate_required_tags(self, content: str, required_tags: List[str]) -> Dict[str, Any]:
        """
        验证回复是否包含所需的标签
        
        Args:
            content: 要检查的内容
            required_tags: 必需的标签列表
            
        Returns:
            验证结果 {valid: bool, missing_tags: List[str], found_tags: List[str]}
        """
        missing_tags = []
        found_tags = []
        
        for tag in required_tags:
            # 检查开始和结束标签
            if re.search(f'<{tag}>', content, re.IGNORECASE):
                found_tags.append(tag)
            else:
                missing_tags.append(tag)
        
        return {
            "valid": len(missing_tags) == 0,
            "missing_tags": missing_tags,
            "found_tags": found_tags
        }
    
    def check_content_repetition(self, current_content: str, history: List[str], threshold: float = 0.7) -> Dict[str, Any]:
        """
        使用LLM检查内容是否与历史记录在语义上重复
        
        Args:
            current_content: 当前内容
            history: 历史内容列表
            threshold: 相似度阈值（对LLM评估结果的置信度要求）
            
        Returns:
            检查结果 {is_repetitive: bool, similarity_score: float, similar_content: str, llm_analysis: str}
        """
        if not history:
            return {
                "is_repetitive": False,
                "similarity_score": 0.0,
                "similar_content": "",
                "llm_analysis": "No history to compare"
            }
        
        # 使用LLM进行语义重复性检测
        history_formatted = "\n".join([f"Historical Message {i+1}:\n{content}\n" for i, content in enumerate(history)])
        
        prompt_content = f"""### ROLE
You are a semantic repetition detection bot. Your task is to determine if a current message is substantially repeating the same ideas, concerns, or suggestions as any previous messages, even if the wording is different.

### TASK
Compare the CURRENT MESSAGE with the HISTORICAL MESSAGES below. Determine if the current message is semantically repetitive.

### CURRENT MESSAGE
{current_content}

### HISTORICAL MESSAGES
{history_formatted}

### EVALUATION CRITERIA
A message is considered **REPETITIVE** if:
- It expresses the same core concern, criticism, or suggestion as a previous message
- It proposes the same solution or approach, even with different wording
- It raises the same objection or issue that was already discussed

A message is considered **NOT REPETITIVE** if:
- It addresses new aspects or details not previously mentioned
- It builds upon previous ideas with substantial new insights
- It responds to new information or clarifications

### OUTPUT FORMAT
Your response must follow this exact format:

ANALYSIS: [Brief explanation of your reasoning]
MOST_SIMILAR: [Quote the most similar historical message, or "NONE" if not repetitive]
SIMILARITY_SCORE: [0.0 to 1.0, where 1.0 is identical meaning]
CONCLUSION: [REPETITIVE or NOT_REPETITIVE]
"""
        
        llm_response = self.model.chat([{"role": "user", "content": prompt_content}])
        
        # 解析LLM响应
        analysis_match = re.search(r'ANALYSIS:\s*(.+?)(?=MOST_SIMILAR:|$)', llm_response, re.DOTALL)
        similar_match = re.search(r'MOST_SIMILAR:\s*(.+?)(?=SIMILARITY_SCORE:|$)', llm_response, re.DOTALL)
        score_match = re.search(r'SIMILARITY_SCORE:\s*([0-9.]+)', llm_response)
        conclusion_match = re.search(r'CONCLUSION:\s*(REPETITIVE|NOT_REPETITIVE)', llm_response, re.IGNORECASE)
        
        analysis = analysis_match.group(1).strip() if analysis_match else "Analysis not found"
        most_similar = similar_match.group(1).strip() if similar_match else ""
        similarity_score = float(score_match.group(1)) if score_match else 0.0
        is_repetitive = conclusion_match.group(1).upper() == "REPETITIVE" if conclusion_match else False
        
        # 应用置信度阈值
        final_is_repetitive = is_repetitive and similarity_score >= threshold
        
        if self.verbose >= VERBOSE_FULL:
            print(f"\n[QualityGate] LLM重复性检测结果:")
            print(f"  - 分析: {analysis}")
            print(f"  - 相似度评分: {similarity_score}")
            print(f"  - LLM结论: {'重复' if is_repetitive else '不重复'}")
            print(f"  - 最终判断: {'重复' if final_is_repetitive else '不重复'} (阈值: {threshold})")
        
        return {
            "is_repetitive": final_is_repetitive,
            "similarity_score": similarity_score,
            "similar_content": most_similar if most_similar != "NONE" else "",
            "llm_analysis": analysis,
            "raw_llm_response": llm_response
        }
    
    # ===== 第二节点(BlueprintDesignNode)专用方法 =====
    
    def evaluate_blueprint_intent(self, response: str, context_info: str) -> str:
        """
        评估SolutionAgent的批准意图 - 专用于第二节点的模糊意图仲裁
        
        Args:
            response: SolutionAgent的回复内容
            context_info: 问题上下文信息
            
        Returns:
            "APPROVE" 或 "DISCUSS"
        """
        prompt_content = f"""### ROLE
You are an intent classification bot. Your task is to determine a speaker's core intent in a technical review.

### CONTEXT
An AI architect (`SolutionAgent`) is reviewing a code blueprint. The problem context is provided below for your reference. I need to know if the architect is giving final approval or if they still have reservations.

*   **Problem Context**: {context_info}

### THE REVIEW MESSAGE TO ANALYZE:
```
{response}
```

### YOUR TASK
Based on the message and the problem context, is the architect's primary intent to **APPROVE** the blueprint, or do they still want to **DISCUSS** it further?

- Answer **APPROVE** if the message expresses clear satisfaction and signals that the design work is complete according to the requirements.
- Answer **DISCUSS** if the message contains any hint of remaining issues, questions, or suggestions for further changes.

### OUTPUT FORMAT
Your response must be a single word: **APPROVE** or **DISCUSS**.
"""
        
        result = self.model.chat([{"role": "user", "content": prompt_content}])
        return result.strip().upper()
    
    def generate_timeout_intervention(self, dialogue_history: str, context_info: str) -> str:
        """
        生成超时干预消息 - 专用于第二节点的导演干预
        
        Args:
            dialogue_history: 完整的对话历史
            context_info: 问题上下文信息
            
        Returns:
            导演干预消息
        """
        prompt_content = f"""### ROLE
You are the Orchestrator, the director of a debugging session. A design discussion between two AIs has exceeded the time limit for this phase.

### PROBLEM CONTEXT
{context_info}

### FULL DIALOGUE HISTORY
{dialogue_history}

### YOUR TASK
Craft a brief, authoritative intervention message that forces the design phase to a conclusion.
Instruct the CodeAgent to produce a final "best effort" blueprint based on the entire discussion, and instruct the SolutionAgent to prepare for a final, decisive review of that blueprint.

Wrap your response in a single, complete `<ORCHESTRATOR_INTERVENTION>` tag pair.
"""
        
        result = self.model.chat([{"role": "user", "content": prompt_content}])
        
        # 提取干预内容
        match = re.search(r'<ORCHESTRATOR_INTERVENTION>(.*?)</ORCHESTRATOR_INTERVENTION>', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return result.strip()
    
    def generate_stagnation_intervention(self, dialogue_history: str, context_info: str) -> str:
        """
        生成停滞干预消息 - 专用于第二节点的导演干预
        
        Args:
            dialogue_history: 完整的对话历史
            context_info: 问题上下文信息
            
        Returns:
            导演干预消息
        """
        prompt_content = f"""### ROLE
You are the Orchestrator, the director of a debugging session. Two AIs, a SolutionAgent (architect) and a CodeAgent (developer), are stuck in a repetitive loop.

### PROBLEM CONTEXT
{context_info}

### DIALOGUE HISTORY
{dialogue_history}

### YOUR TASK
Craft a brief, authoritative intervention message. Your message should:
1. Acknowledge that the discussion is stalled on a specific point.
2. Propose a new angle or a compromise to break the deadlock. For example, suggest a completely different approach, or ask the SolutionAgent to accept a "good enough" solution for now.

Wrap your response in a single, complete `<ORCHESTRATOR_INTERVENTION>` tag pair.
"""
        
        result = self.model.chat([{"role": "user", "content": prompt_content}])
        
        # 提取干预内容
        match = re.search(r'<ORCHESTRATOR_INTERVENTION>(.*?)</ORCHESTRATOR_INTERVENTION>', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return result.strip()
    
    def build_solution_agent_meta_review_prompt(self, context_info: str, code_agent_meta_refine_report: str, latest_simulation_report: str) -> str:
        """
        构建 SolutionAgent 的中期回顾提示 - V2: 审查CodeAgent的诊断报告
        
        Args:
            context_info: 问题上下文信息
            code_agent_meta_refine_report: CodeAgent的<META_REFINE>报告
            latest_simulation_report: 最新的模拟失败报告，作为审查的客观证据
            
        Returns:
            审查提示内容
        """
        prompt_content = f"""### ROLE AND GOAL
You are SolutionAgent, the senior architect. A mid-term review has been triggered due to repeated failures. Your engineer, CodeAgent, has just completed a self-diagnosis. Your task is to act as the final arbiter: review their diagnosis, validate it against the ground truth, and issue the final, unified command for the next iteration.

### CRITICAL REVIEW MATERIALS

1.  **Ground Truth (The Objective Evidence)**: The latest simulation report showing the most recent failure. This is what actually happened.
    <GROUND_TRUTH_SIMULATION>
    {latest_simulation_report}
    </GROUND_TRUTH_SIMULATION>

2.  **Engineer's Diagnosis (The Analysis to Review)**: CodeAgent's self-assessment of the failure.
    <ENGINEER_DIAGNOSIS>
    {code_agent_meta_refine_report}
    </ENGINEER_DIAGNOSIS>

3.  **The Supreme Law (Reference)**:
    {context_info}

### YOUR ARCHITECTURAL REVIEW PROTOCOL
You must follow these steps to ensure a clear and decisive outcome.

1.  **Validate the Diagnosis**: First, compare the `Engineer's Diagnosis` against the `Ground Truth Simulation`. Is their assessment correct? Did they correctly identify the failure as a **Flawed Strategy** or a **Flawed Implementation**?

2.  **Assess the Proposed Plan**: Next, evaluate the "Next Action" or "Breakout Strategy" proposed in their diagnosis. Is it a logical and effective plan to solve the problem identified in the `Ground Truth`?

3.  **Issue a Final Verdict**: Based on your assessment, you will provide a single, authoritative refinement request. This is the only instruction CodeAgent will follow.

### YOUR TASK
Produce a final verdict in the `<REFINEMENT_REQUEST>` tag. Your response inside this tag will be the **only** guidance `CodeAgent` receives.

*   **If you fully agree with the Engineer's Diagnosis and Plan**: Your response should be a clear approval. Start by confirming their diagnosis is correct and instruct them to proceed with their proposed plan.
    *   *Example: "Your diagnosis of a 'Flawed Implementation' is accurate. The proposed fix to adjust the loop's starting condition is the correct path forward. Please proceed with generating the refined blueprint based on this plan."*

*   **If you partially agree but need to make corrections**: Your response must affirm the correct parts of their diagnosis but provide specific, overriding corrections for the flawed parts.
    *   *Example: "You correctly identified the failure as a 'Flawed Implementation', but your proposed fix is incomplete. In addition to correcting the loop, you must also ensure the initial array allocation is `n+2` to prevent future index errors. Refine your blueprint with this adjusted plan."*

*   **If you completely disagree**: Your response must be a clear override. State that their diagnosis was incorrect, provide your own analysis of the root cause, and issue a new, definitive strategic direction.
    *   *Example: "Your diagnosis of a 'Flawed Implementation' is incorrect. The evidence shows the core 'backwards computation' strategy itself is flawed. We will now pivot. Your new strategy is to use a direct iterative approach. Implement a blueprint that builds the sequence forwards from the base cases."*

### REQUIRED OUTPUT FORMAT
Your entire response must be a single `<REFINEMENT_REQUEST>` tag containing your final, unified instructions for CodeAgent.
```xml
<REFINEMENT_REQUEST>
[Your final verdict and actionable instructions here.]
</REFINEMENT_REQUEST>
```
"""
        return prompt_content
    
    def build_code_agent_meta_refine_prompt(self, context_problemdescription: str, approved_node_1_output: str, current_blueprint: str, solution_dialogue_recent: str) -> str:
        """
        构建 CodeAgent 的中期回顾提示 - 新版本根据用户需求重构
        
        Args:
            context_problemdescription: The Supreme Law (context.problemdescription)
            approved_node_1_output: The Initial Strategic Analysis (AttentionAnalysis) - 第一节点的内容
            current_blueprint: The "Safe Anchor" Blueprint - 当前蓝图
            solution_dialogue_recent: Your Learning History (Diagnostic Summaries) - solution的历史，只取最近两次
            
        Returns:
            中期回顾提示内容
        """
        prompt_content = f"""ROLE AND GOAL
You are CodeAgent, and you are now entering a Mid-term Strategic Review.
Your last blueprint (v_previous) has been designated as a "safe anchor". Your mission now is not to perform a small, incremental fix. Instead, your goal is to conduct a deep, reflective analysis of your entire journey so far and, based on your insights, propose a new, potentially superior, alternative blueprint.
This is your opportunity for a strategic leap. You are encouraged to question your core assumptions and explore a fundamentally different path if your analysis suggests one.

CONTEXT FOR YOUR STRATEGIC REVIEW
The Supreme Law: 
{context_problemdescription}
The Initial Strategic Analysis (AttentionAnalysis): 
{approved_node_1_output}

The "Safe Anchor" Blueprint:
{current_blueprint}

Your Learning History (Diagnostic Summaries):
{solution_dialogue_recent}

YOUR REFLECTIVE TASK
You MUST provide your response in two parts.

Part 1: The Retrospective Analysis
<RETROSPECTIVE_ANALYSIS>...</RETROSPECTIVE_ANALYSIS>
A. Identify the Failure Pattern: Review the Learning History summaries. Is there a recurring theme or a single, persistent root cause behind your previous failures? (e.g., "My repeated failures all stem from incorrect state management during the loop," or "I have consistently struggled with handling negative numbers correctly.").
B. Challenge Your "Safe Anchor": Look at your Safe Anchor blueprint. Even if it seems close to correct, does its core architecture still suffer from the Failure Pattern you just identified? Does it feel overly complex, or like a patch-work of fixes rather than an elegant solution?
C. Propose a "Breakout" Strategy: Based on your analysis, propose a new strategic approach. This is where you can be bold. Your new strategy should be designed to neutralize the core failure pattern at an architectural level.
A-Grade Example:
"The recurring failure pattern is off-by-one errors caused by complex index calculations. My 'Safe Anchor' tries to fix this with multiple conditional checks, which is fragile. My new breakout strategy is to abandon manual indexing entirely and switch to a two-pass approach: first, pre-compute all necessary values and store them in a hash map, and second, iterate through the original array and use the map to construct the result. This completely eliminates the source of the errors."

Part 2: The Alternative Blueprint
<ALTERNATIVE_BLUEPRINT>...</ALTERNATIVE_BLUEPRINT>
Action: Provide the full, complete pseudocode for a new blueprint that is a direct implementation of your Breakout Strategy.
Constraint: This blueprint should be a clean, fresh implementation based on your new strategy. Do not simply copy and paste from the Safe Anchor and make minor changes.
"""
        return prompt_content
    
    def generate_solution_agent_intervention(self, dialogue_history: str, context_info: str) -> str:
        """
        生成针对SolutionAgent重复的导演干预 - PROMPT_F_DIRECTOR_INTERVENTION_ON_SOLUTION
        
        Args:
            dialogue_history: 完整的对话历史
            context_info: 问题上下文信息
            
        Returns:
            导演干预消息
        """
        prompt_content = f"""### ROLE
You are the Orchestrator, the director of a debugging session. You have detected that the **SolutionAgent (the architect)** is stuck in a repetitive loop. It keeps making the same critique without providing a new, constructive path forward.

Your task is to intervene authoritatively to break this deadlock.

### FULL DIALOGUE HISTORY
{dialogue_history}

### YOUR TASK
Craft a brief, authoritative intervention message. Your message MUST achieve the following:
1.  State clearly that the **SolutionAgent's** review has become repetitive and is no longer productive.
2.  Override the SolutionAgent's last, repetitive refinement request.
3.  Provide a **new, concrete, and different** command to the **CodeAgent**. You have two strategic options for this command:

    *   **Option A (Force a different strategy)**: Instruct `CodeAgent` to completely abandon the current approach and try one of the other high-level strategies that was mentioned earlier but not yet fully explored (e.g., "backward iteration", "pre-calculation pass").
    *   **Option B (Demand simplification)**: Instruct `CodeAgent` to ignore the complexity for a moment and write a simplified version of the code that ONLY solves for the specific failing case (e.g., `n=3`), even if it's not a general solution.

Choose the option that seems most likely to break the current impasse.

Wrap your entire response in a single, complete `<ORCHESTRATOR_INTERVENTION>` tag !!pair!!.
"""
        
        result = self.model.chat([{"role": "user", "content": prompt_content}])
        
        # 提取干预内容
        match = re.search(r'<ORCHESTRATOR_INTERVENTION>(.*?)</ORCHESTRATOR_INTERVENTION>', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return result.strip()
    
    def generate_code_agent_intervention(self, dialogue_history: str, context_info: str) -> str:
        """
        生成针对CodeAgent重复的导演干预 - PROMPT_G_DIRECTOR_INTERVENTION_ON_CODE
        
        Args:
            dialogue_history: 完整的对话历史
            context_info: 问题上下文信息
            
        Returns:
            导演干预消息
        """
        prompt_content = f"""### ROLE
You are the Orchestrator, the director of a debugging session. You have detected that the **CodeAgent (the engineer)** is stuck. It keeps submitting blueprints that repeat the same fundamental flaws, failing to incorporate the architect's feedback.

Your task is to intervene to break this unproductive cycle by switching from "design" to "teaching" mode.

### FULL DIALOGUE HISTORY
{dialogue_history}

### YOUR TASK
Craft a brief, authoritative intervention message. Your message MUST command the **SolutionAgent** to change its role from a reviewer to a teacher.

The message must instruct the **SolutionAgent** to perform the following new task:
1.  Stop providing high-level refinement requests.
2.  Instead, provide a **highly detailed, step-by-step, annotated manual simulation** for the specific failing input (`n=3`), demonstrating *exactly* how a correct algorithm's logic should work.
3.  Conclude by instructing the `CodeAgent` to translate this detailed simulation directly into a new blueprint.

Wrap your entire response in a single, complete `<ORCHESTRATOR_INTERVENTION>` tag pair.
"""
        
        result = self.model.chat([{"role": "user", "content": prompt_content}])
        
        # 提取干预内容
        match = re.search(r'<ORCHESTRATOR_INTERVENTION>(.*?)</ORCHESTRATOR_INTERVENTION>', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return result.strip()
    
    def evaluate_blueprint_quality(self, code_agent_blueprint: str) -> str:
        """
        评估CodeAgent生成的蓝图质量 - 判断是具体算法还是模糊目标
        
        Args:
            code_agent_blueprint: CodeAgent生成的蓝图内容
            
        Returns:
            评估结果: "EXECUTABLE" 或 "AMBIGUOUS"
        """
        prompt_content = f"""### ROLE AND GOAL
You are a quality gate. Your task is to quickly determine if a blueprint is executable on its own.

### CONTEXT
Blueprint to review:
<BLUEPRINT_TO_REVIEW>
{code_agent_blueprint}
</BLUEPRINT_TO_REVIEW>

### YOUR TASK
Classify the blueprint as `EXECUTABLE` or `AMBIGUOUS` based on this single principle: **Is the blueprint self-contained?**

*   **EXECUTABLE**: Yes. All rules and formulas needed for execution are included within the blueprint itself. It does not rely on external knowledge.
*   **AMBIGUOUS**: No. It refers to a value or a goal without providing the steps to calculate it. It requires looking up information from outside the blueprint.

Provide your one-word decision in the specified format.

### REQUIRED OUTPUT FORMAT
```xml
<BLUEPRINT_CHECK>
[Your one-word decision: EXECUTABLE or AMBIGUOUS]
</BLUEPRINT_CHECK>
```
"""
        
        result = self.model.chat([{"role": "user", "content": prompt_content}])
        
        # 提取评估结果
        match = re.search(r'<BLUEPRINT_QUALITY_ASSESSMENT>(.*?)</BLUEPRINT_QUALITY_ASSESSMENT>', result, re.DOTALL)
        if match:
            assessment = match.group(1).strip().upper()
            if assessment in ["EXECUTABLE", "AMBIGUOUS"]:
                return assessment
        
        # 如果无法解析，默认返回AMBIGUOUS（保守策略）
        if self.verbose >= 2:
            print("⚠️ 无法解析蓝图质量评估结果，默认返回AMBIGUOUS")
        return "AMBIGUOUS"
    
    def generate_blueprint_refinement_feedback(self, ambiguous_blueprint: str, ambiguous_part: str = "") -> str:
        """
        生成蓝图改进反馈（当蓝图被判定为AMBIGUOUS时）
        
        Args:
            ambiguous_blueprint: 被拒绝的模糊蓝图
            ambiguous_part: 具体的模糊部分（可选）
            
        Returns:
            格式化的反馈消息
        """
        if not ambiguous_part:
            # 如果没有提供具体的模糊部分，使用通用反馈
            ambiguous_part = "contains goal-like statements rather than specific computational steps"
        
        feedback = f"""ROLE AND GOAL
You are CodeAgent. Your previous blueprint was rejected by the Orchestrator's Quality Gate because it was not a concrete algorithm.

REJECTED BLUEPRINT
{ambiguous_blueprint}

REASON FOR REJECTION
The blueprint describes a goal, not an executable algorithm. Specifically, the instruction "{ambiguous_part}" tells us WHAT to do, but not HOW to do it. Every step in a blueprint must be mechanically executable using only previously defined variables or direct calculations.

YOUR TASK
You must refine your blueprint to be a specific, step-by-step algorithm. Do not use high-level concepts without defining the exact computational steps to achieve them. Provide the new, complete blueprint in the <REFINED_BLUEPRINT> tag."""
        
        return feedback
    
    def verify_simulation_trace_accuracy(self, code_content: str, trace_content: str) -> Dict[str, str]:
        """
        验证模拟过程的准确性 - 检测过程是否正确
        
        Args:
            code_content: 被模拟的代码内容
            trace_content: 模拟过程的追踪内容
            
        Returns:
            {"status": "ACCURATE"/"INACCURATE", "response": "原始响应内容"}
        """
        prompt = f"""### ROLE AND GOAL
You are a Simulation Trace Auditor. You are a precise, machine-like verifier. Your sole and absolute purpose is to conduct a forensic audit of a simulation trace to ensure its **factual accuracy**. You do not judge if the code being simulated is correct; you only judge if the **simulation of that code** is correct.

### CONTEXT
You will be provided with two pieces of evidence:
1.  **The Code That Was Simulated**: This is the "instruction manual" detailing what *should* have happened.
2.  **The Simulation Trace to Audit**: This is the "eyewitness report" detailing what the simulator *claimed* happened.

### YOUR CORE AUDITING PROTOCOL
Your mission is to find any **inconsistency** between the code's instructions and the trace's reported outcomes. You must scrutinize every step of the trace.

For each significant operation reported in the trace (e.g., a variable assignment, a calculation, a function call result), you must:
1.  Locate the corresponding line of code in **The Code That Was Simulated**.
2.  Mentally re-execute that line of code with the variables' states as described in the trace.
3.  Compare your re-executed result with the outcome reported in the trace.
4.  If they do not match exactly, you have found an inaccuracy.

---
**Abstract Example of Inaccuracy Detection:**
*   **The Code Says**: `new_value = user_data['points'] + 10`
*   **The Trace Says**:
    > - Getting `user_data`, which is `{{'points': 50, 'level': 3}}`.
    > - Evaluating expression `user_data['points'] + 10`.
    > - The result is `65`.
    > - Assigning `65` to `new_value`.
*   **Your Verdict**: **INACCURATE**.
*   **Reasoning**: My re-execution shows `user_data['points']` is `50`. `50 + 10` is `60`, not the `65` reported in the trace. The trace contains a calculation error.
---

### INPUTS FOR YOUR AUDIT

2.  **The Simulation Trace to Audit**:
    ```xml
    <TRACE>
    {trace_content}
    </TRACE>
    ```

### YOUR TASK
Based on the protocol above, determine if the provided trace is a factually accuration

*   If the trace is a perfectly accurate, step-by-step reflection of math problems, variable assignments, and function calls as dictated by the code, the status is **ACCURATE**.
*   If you find even a single calculation error, incorrect value assignment, or any other deviation between the code's logic and the trace's report, the status is **INACCURATE**.

### REQUIRED OUTPUT FORMAT
Your response must be a single, complete XML tag. If the status is INACCURATE, you must provide a brief, factual reason.

for the trace:**

```xml
<TRACE_VERIFICATION>
    <REASON>[A brief, factual description of the first inconsistency or consistency you found. For example: "The trace reports the result of a calculation as 65, but the code's operation should have resulted in 60."]</REASON>
    <STATUS>ACCURATE or INACCURATE</STATUS>
</TRACE_VERIFICATION>
```
"""

        try:
            response = self.model.chat([{"role": "user", "content": prompt}])
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"[QualityGate] 模拟过程验证响应: {response}")
            
            # 提取STATUS标签
            status_match = re.search(r'<STATUS>\s*(ACCURATE|INACCURATE)\s*</STATUS>', response, re.IGNORECASE)
            if status_match:
                status = status_match.group(1).upper()
                return {"status": status, "response": response}
            
            # 如果没有找到STATUS标签，尝试直接在响应中查找
            cleaned_response = response.strip().upper()
            if "ACCURATE" in cleaned_response:
                return {"status": "ACCURATE", "response": response}
            elif "INACCURATE" in cleaned_response:
                return {"status": "INACCURATE", "response": response}
            else:
                # 如果无法解析，默认为INACCURATE
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"[QualityGate] 无法解析模拟过程验证响应: {response}")
                return {"status": "INACCURATE", "response": response}
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"[QualityGate] 模拟过程验证出错: {e}")
            return {"status": "INACCURATE", "response": f"Error occurred: {str(e)}"}

    def verify_simulation_conclusion(self, context_content: str, simulation_report: str) -> str:
        """
        验证模拟报告的结论是否正确
        
        Args:
            context_content: 上下文内容，包含期望值
            simulation_report: 完整的模拟报告内容
            
        Returns:
            "PASSED" 或 "FAILED"
        """
        prompt = f"""### ROLE AND GOAL
You are a Verification Gate. Your sole function is to audit a simulation report and verify if its final conclusion is correct by comparing the actual output with the expected value.

### CONTEXT
You will be given a `<SIMULATION_REPORT>` and context information containing expected values.



### YOUR TASK
Your task is to compare the `<FINAL_OUTPUT>` from the simulation report with the expected values and determine if they match.

To do this, follow this simple process:
1. Extract the `<FINAL_OUTPUT>` value from the simulation report
2. Extract the expected values from the context (if available)
3. Compare the final output with the expected value
4. Return PASSED if they are identical, FAILED if they are different

### SIMULATION REPORT TO AUDIT
{simulation_report}
### Expected Values from Context:
{context_content}
### REQUIRED OUTPUT FORMAT
<REASON>
Provide a brief explanation comparing the final output with the expected value.
</REASON>
<FINAL_DECISION>
PASSED or FAILED
</FINAL_DECISION>"""

        try:
            response = self.model.chat([{"role": "user", "content": prompt}])
            print(f"[QualityGate] 模拟结果验证响应: {response}")
            # 首先尝试提取FINAL_DECISION标签
            decision_match = re.search(r'<FINAL_DECISION>\s*(PASSED|FAILED)\s*</FINAL_DECISION>', response, re.IGNORECASE)
            if decision_match:
                return decision_match.group(1).upper()
            
            # 如果没有找到FINAL_DECISION标签，尝试直接在响应中查找
            cleaned_response = response.strip().upper()
            if "PASSED" in cleaned_response:
                return "PASSED"
            elif "FAILED" in cleaned_response:
                return "FAILED"
            else:
                # 如果无法解析，默认为FAILED
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"[QualityGate] 无法解析模拟结果验证响应: {response}")
                return "FAILED"
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"[QualityGate] 模拟结果验证出错: {e}")
            return "FAILED"
    
    def store_blueprint_history(self, current_blueprint: str, blueprint_history: List[str]) -> Dict[str, Any]:
        """
        存储蓝图历史机制
        
        Args:
            current_blueprint: 当前的蓝图内容
            blueprint_history: 历史蓝图列表
            
        Returns:
            存储结果 {"success": bool, "updated_history": List[str], "action": str}
        """
        # TODO: 实现具体的蓝图存储逻辑
        # 这里先返回基本结构，具体逻辑后续实现
        
        updated_history = blueprint_history.copy()
        updated_history.append(current_blueprint)
        
        return {
            "success": True,
            "updated_history": updated_history,
            "action": "stored"
        }
    
    def extract_blueprint_core(self, blueprint_content: str) -> Dict[str, Any]:
        """
        提炼蓝图核心机制
        
        Args:
            blueprint_content: 原始蓝图内容
            
        Returns:
            提炼结果 {"success": bool, "core_blueprint": str, "extracted_elements": Dict}
        """
        if not blueprint_content.strip():
            return {
                "success": False,
                "core_blueprint": "",
                "extracted_elements": {
                    "algorithm_steps": [],
                    "key_variables": [],
                    "core_logic": ""
                },
                "error": "Empty blueprint content"
            }
        
        # 使用Code Logic Distiller提示词提炼核心算法策略
        prompt_content = f"""### ROLE AND GOAL
You are a Code Logic Distiller. You are an expert computer scientist who can instantly see the core algorithmic idea behind any piece of code. Your task is to ignore implementation details and extract the fundamental strategy into a single, concise sentence.

### CONTEXT
You will be given a blueprint which can be pseudocode or Python code.
<BLUEPRINT_TO_ANALYZE>
{blueprint_content}
</BLUEPRINT_TO_ANALYZE>

### YOUR TASK
Read the blueprint and describe its **core algorithmic strategy** in one clear and concise sentence. Your description should focus on the unique "how" of the approach.

---
**Abstract Examples to Guide Your Distillation:**
*   **For a blueprint that iterates backwards and stops at the first success:** Your summary should be like -> "Iterate backwards from the end of the input, and exit immediately on the first valid finding."
*   **For a blueprint that finds the best result after checking all possibilities:** Your summary should be like -> "Iterate through all possible options, continuously updating a variable to store the optimal result, and decide after the loop concludes."
*   **For a blueprint that divides the problem:** Your summary should be like -> "Employ a recursive divide-and-conquer strategy to break the problem into smaller subproblems."
---

### REQUIRED OUTPUT FORMAT
Your entire response must be a single XML tag containing your one-sentence summary.
```xml
<LOGIC_FINGERPRINT>
[Your one-sentence summary of the core algorithmic strategy.]
</LOGIC_FINGERPRINT>
```"""
        
        try:
            response = self.model.chat([{"role": "user", "content": prompt_content}])
            
            if self.verbose >= VERBOSE_FULL:
                print(f"[QualityGate] 蓝图核心提炼响应: {response}")
            
            # 提取LOGIC_FINGERPRINT标签中的内容
            fingerprint_match = re.search(r'<LOGIC_FINGERPRINT>\s*(.*?)\s*</LOGIC_FINGERPRINT>', response, re.DOTALL)
            if fingerprint_match:
                core_logic = fingerprint_match.group(1).strip()
                
                return {
                    "success": True,
                    "core_blueprint": core_logic,  # 使用提炼出的核心逻辑作为核心蓝图
                    "extracted_elements": {
                        "algorithm_steps": [],  # 可以后续扩展
                        "key_variables": [],    # 可以后续扩展
                        "core_logic": core_logic
                    },
                    "raw_response": response
                }
            else:
                # 如果无法提取LOGIC_FINGERPRINT标签，尝试使用整个响应
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"[QualityGate Warning] 无法提取LOGIC_FINGERPRINT标签，使用整个响应")
                
                return {
                    "success": True,
                    "core_blueprint": response.strip(),
                    "extracted_elements": {
                        "algorithm_steps": [],
                        "key_variables": [],
                        "core_logic": response.strip()
                    },
                    "raw_response": response
                }
                
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"[QualityGate] 蓝图核心提炼出错: {e}")
            
            return {
                "success": False,
                "core_blueprint": "",
                "extracted_elements": {
                    "algorithm_steps": [],
                    "key_variables": [],
                    "core_logic": ""
                },
                "error": str(e)
            }
    
    def detect_blueprint_repetition(self, current_blueprint_core: str, blueprint_history_cores: List[str]) -> Dict[str, Any]:
        """
        检测蓝图重复机制
        
        Args:
            current_blueprint_core: 当前蓝图的核心内容
            blueprint_history_cores: 历史蓝图核心内容列表
            
        Returns:
            检测结果 {"is_repetitive": bool, "similarity_score": float, "matched_blueprint": str, "analysis": str}
        """
        # TODO: 实现具体的蓝图重复检测逻辑
        # 这里先返回基本结构，具体逻辑后续实现
        
        return {
            "is_repetitive": False,
            "similarity_score": 0.0,
            "matched_blueprint": "",
            "analysis": "检测逻辑待实现"
        }
    
    def extract_simulation_value_from_log(self, error_logs: str) -> str:
        """
        提取门控：从错误日志中提取函数调用与期望值
        使用LLM智能理解复杂的错误日志格式
        
        Args:
            error_logs: 错误日志内容
            context_content: 上下文内容，用于辅助理解
            
        Returns:
            JSON数组字符串: 格式为 [{"simulation_value": "func(params)", "expected_value": "value"}, ...]
            如果未找到则返回空字符串
        """
        try:
            # 构建LLM提示词
            prompt = f"""### ROLE AND GOAL
You are a **Precision Text Extractor**. Your only task is to find ALL valid `assert` statements in the provided logs and extract the function call and its expected value for each one **exactly as they are written**. You MUST NOT invent, infer, or modify any part of the function call or value.

### EXTRACTION PROTOCOL
1.  **Scan for `assert`**: Find the first line containing an `assert` statement.
2.  **Isolate the Call**: Identify the full function call expression, including the function name and all its arguments inside the parentheses.
3.  **Isolate the Value**: Identify the expected value from the `==` comparison.
4.  **Exact Copy**: Copy the function call and the expected value verbatim, without any changes.

### Error Logs to Analyze:
```
{error_logs}
```

### Your Task & Examples

**Example 1:**
-   **Log Input**: `Test failed: assert triples_sum_to_zero([1, 3, 5, 0]) == False`
-   **Your Extraction**:
    -   `simulation_value`: `triples_sum_to_zero([1, 3, 5, 0])`
    -   `expected_value`: `False`

**Example 2:**
-   **Log Input**: `AssertionError: fibonacci(5) expected 5 but got 8`
-   **Your Extraction**:
    -   `simulation_value`: `fibonacci(5)`
    -   `expected_value`: `5`

**Example 3:**
-   **Log Input**: `FAILED tests/test_parser.py::test_simple - assert parse_music('(AB) C') == ['A', 'B', 'C']`
-   **Your Extraction**:
    -   `simulation_value`: `parse_music('(AB) C')`
    -   `expected_value`: `['A', 'B', 'C']`

### REQUIRED OUTPUT FORMAT
-   If you find valid `assert` statements, return a JSON array containing all matches.
-   If you cannot find any `assert` statements, return exactly: `NO_VALUE_FOUND`

**JSON Output Format:**
```json
[
  {{"simulation_value": "[Exact function call]", "expected_value": "[Exact expected value]"}}
]
```
"""

            # 调用LLM获取提取结果
            if self.verbose >= 2:
                print(f"[QualityGate] 正在使用LLM从错误日志中提取期望值...")
                print(f"[QualityGate] 输入的错误日志: {error_logs[:200]}..." if len(error_logs) > 200 else f"[QualityGate] 输入的错误日志: {error_logs}")
                print(f"请求上下文:\n {prompt}\n\n")
            response = self.model.chat([{"role": "user", "content": prompt}])
            
            # 详细调试信息
            if self.verbose >= 2:
                print(f"[QualityGate] LLM原始响应: {response}")
                print(f"[QualityGate] 响应类型: {type(response)}")
                print(f"[QualityGate] 响应长度: {len(response) if response else 0}")
            
            # 清理响应
            function_map = response.strip()
            
            if self.verbose >= 2:
                print(f"[QualityGate] 清理后的响应: {function_map}")
            
            # 检查是否找到了值
            if function_map == "NO_VALUE_FOUND" or not function_map:
                if self.verbose >= 1:
                    print(f"[QualityGate] LLM未能从错误日志中提取到函数调用")
                return ""
            
            # 验证JSON格式并只保留第一个元素
            try:
                import json
                parsed_test = json.loads(function_map)
                if self.verbose >= 2:
                    print(f"[QualityGate] JSON格式验证成功: {parsed_test}")
                
                # 如果是数组且有多个元素，只保留第一个元素（但仍然返回数组格式）
                if isinstance(parsed_test, list) and len(parsed_test) > 1:
                    first_element = [parsed_test[0]]  # 保持数组格式，但只有第一个元素
                    function_map = json.dumps(first_element)
                    if self.verbose >= 2:
                        print(f"[QualityGate] 保留第一个元素: {function_map}")
                elif isinstance(parsed_test, list) and len(parsed_test) == 1:
                    # 如果只有一个元素，保持原样
                    function_map = json.dumps(parsed_test)
                    if self.verbose >= 2:
                        print(f"[QualityGate] 单个元素数组，保持原样: {function_map}")
                
            except json.JSONDecodeError as json_err:
                if self.verbose >= 1:
                    print(f"[QualityGate] JSON格式验证失败: {json_err}")
                    print(f"[QualityGate] 有问题的JSON字符串: {function_map}")
                # 尝试修复常见的JSON格式问题
                function_map = self._fix_json_format(function_map)
                if self.verbose >= 2:
                    print(f"[QualityGate] 尝试修复后的JSON: {function_map}")
                
                # 重新验证并处理修复后的JSON
                try:
                    parsed_fixed = json.loads(function_map)
                    if isinstance(parsed_fixed, list) and len(parsed_fixed) > 1:
                        first_element = [parsed_fixed[0]]  # 只保留第一个元素，保持数组格式
                        function_map = json.dumps(first_element)
                        if self.verbose >= 2:
                            print(f"[QualityGate] 修复后保留第一个元素: {function_map}")
                except json.JSONDecodeError:
                    if self.verbose >= 1:
                        print(f"[QualityGate] 修复后仍无法解析JSON，返回原始内容")
            
            if self.verbose >= 1:
                print(f"[QualityGate] LLM成功提取到函数调用与期望值: {function_map}")
            
            return function_map
            
        except Exception as e:
            if self.verbose >= 1:
                print(f"[QualityGate] 提取函数调用与期望值时发生错误: {e}")
                print(f"[QualityGate] 错误类型: {type(e)}")
                import traceback
                print(f"[QualityGate] 完整错误堆栈: {traceback.format_exc()}")
            
            return ""
    def extract_simulation_value_from_log_com(self, error_logs: str) -> str:
            """
            提取门控：从错误日志中提取函数调用与期望值
            使用LLM智能理解复杂的错误日志格式

            Args:
                error_logs: 错误日志内容
                context_content: 上下文内容，用于辅助理解

            Returns:
                JSON数组字符串: 格式为 [{"simulation_value": "func(params)", "expected_value": "value"}, ...]
                如果未找到则返回空字符串
            """
            try:
                # 构建LLM提示词
                prompt = f"""
You are a **Standard I/O Log Extractor**. Your only task is to parse the provided competitive programming execution logs and extract the **Input**, **Expected Output**, and **Actual Output** (or Error) exactly as they appear.

### EXTRACTION PROTOCOL
1.  **Locate Blocks**: You must identify three distinct blocks of text based on the headers:
    *   `Input:`
    *   `Expected Output:`
    *   `Your Output:` (or `Actual Output:`)
2.  **Extract Content**:
    *   **Input**: Capture all text *between* the `Input:` header and the `Expected Output:` header. Trim leading/trailing whitespace, but **preserve internal newlines** if the input is multiline.
    *   **Expected Output**: Capture all text *between* the `Expected Output:` header and the `Your Output:` header. Trim leading/trailing whitespace.
    *   **Actual Output**: Capture all text *after* the `Your Output:` header until the end of the log entry. This may include Python Tracebacks, error messages, or incorrect values.
3.  **Verbatim Copy**: Do not interpret the data (e.g., do not convert string `"[1,2]"` to a list object). Copy it exactly as text.

### Error Logs to Analyze:
```
{error_logs}
```

### Your Task & Examples

**Example 1 (Runtime Error / Traceback):**
-   **Log Input**:
    ```text
    Input:
    [1,3,4,3,4,1]
    Expected Output:
    750
    Your Output:
    Traceback (most recent call last):
      File "test.py", line 44, in <module>
    ValueError: invalid literal for int()
    ```
-   **Your Extraction**:
    -   `input`: `[1,3,4,3,4,1]`
    -   `expected`: `750`
    -   `actual`: `Traceback (most recent call last):\n  File "test.py", line 44, in <module>\nValueError: invalid literal for int()`

**Example 2 (Wrong Answer / Multiline Input):**
-   **Log Input**:
    ```text
    Input:
    3
    10 20 30
    Expected Output:
    60
    Your Output:
    102030
    ```
-   **Your Extraction**:
    -   `input`: `3\n10 20 30`
    -   `expected`: `60`
    -   `actual`: `102030`

**Example 3 (String Mismatch):**
-   **Log Input**:
    ```text
    Input: "hello world"
    Expected Output: "HELLO WORLD"
    Your Output: "hello world"
    ```
-   **Your Extraction**:
    -   `input`: `"hello world"`
    -   `expected`: `"HELLO WORLD"`
    -   `actual`: `"hello world"`

### REQUIRED OUTPUT FORMAT
-   Return a JSON array containing all parsed test cases.
-   If the log format does not match the `Input`/`Expected`/`Output` structure, return exactly: `NO_STRUCTURED_LOG_FOUND`

**JSON Output Format:**
```json
[
  {{
    "input": "[Exact input text]",
    "expected": "[Exact expected output]",
    "actual": "[Exact actual output or traceback]"
  }}
]
```
    """

               
                print(f"[QualityGate] 正在使用LLM从错误日志中提取期望值...")
                print(f"[QualityGate] 输入的错误日志: {error_logs[:200]}..." if len(error_logs) > 200 else f"[QualityGate] 输入的错误日志: {error_logs}")
                print(f"请求上下文:\n {prompt}\n\n")
                response = self.model.chat([{"role": "user", "content": prompt}])

                # 详细调试信息
               
                print(f"[QualityGate] LLM原始响应: {response}")
                print(f"[QualityGate] 响应类型: {type(response)}")
                print(f"[QualityGate] 响应长度: {len(response) if response else 0}")

                # 清理响应
                function_map = response.strip()

                if self.verbose >= 2:
                    print(f"[QualityGate] 清理后的响应: {function_map}")

                # 检查是否找到了值
                if function_map == "NO_VALUE_FOUND" or not function_map:
                    if self.verbose >= 1:
                        print(f"[QualityGate] LLM未能从错误日志中提取到函数调用")
                    return ""

                # 验证JSON格式并只保留第一个元素
                try:
                    import json
                    parsed_test = json.loads(function_map)
                    if self.verbose >= 2:
                        print(f"[QualityGate] JSON格式验证成功: {parsed_test}")

                    # 如果是数组且有多个元素，只保留第一个元素（但仍然返回数组格式）
                    if isinstance(parsed_test, list) and len(parsed_test) > 1:
                        first_element = [parsed_test[0]]  # 保持数组格式，但只有第一个元素
                        function_map = json.dumps(first_element)
                        if self.verbose >= 2:
                            print(f"[QualityGate] 保留第一个元素: {function_map}")
                    elif isinstance(parsed_test, list) and len(parsed_test) == 1:
                        # 如果只有一个元素，保持原样
                        function_map = json.dumps(parsed_test)
                        if self.verbose >= 2:
                            print(f"[QualityGate] 单个元素数组，保持原样: {function_map}")

                except json.JSONDecodeError as json_err:
                    if self.verbose >= 1:
                        print(f"[QualityGate] JSON格式验证失败: {json_err}")
                        print(f"[QualityGate] 有问题的JSON字符串: {function_map}")
                    # 尝试修复常见的JSON格式问题
                    function_map = self._fix_json_format(function_map)
                    if self.verbose >= 2:
                        print(f"[QualityGate] 尝试修复后的JSON: {function_map}")

                    # 重新验证并处理修复后的JSON
                    try:
                        parsed_fixed = json.loads(function_map)
                        if isinstance(parsed_fixed, list) and len(parsed_fixed) > 1:
                            first_element = [parsed_fixed[0]]  # 只保留第一个元素，保持数组格式
                            function_map = json.dumps(first_element)
                            if self.verbose >= 2:
                                print(f"[QualityGate] 修复后保留第一个元素: {function_map}")
                    except json.JSONDecodeError:
                        if self.verbose >= 1:
                            print(f"[QualityGate] 修复后仍无法解析JSON，返回原始内容")

                if self.verbose >= 1:
                    print(f"[QualityGate] LLM成功提取到函数调用与期望值: {function_map}")

                return function_map

            except Exception as e:
                if self.verbose >= 1:
                    print(f"[QualityGate] 提取函数调用与期望值时发生错误: {e}")
                    print(f"[QualityGate] 错误类型: {type(e)}")
                    import traceback
                    print(f"[QualityGate] 完整错误堆栈: {traceback.format_exc()}")

                return ""
    
    def _fix_json_format(self, json_str: str) -> str:
        """尝试修复常见的JSON格式问题"""
        try:
            # 移除可能的markdown代码块标记
            json_str = json_str.replace('```json', '').replace('```', '').strip()
            
            # 移除前后可能的多余文本
            start_idx = json_str.find('[')
            end_idx = json_str.rfind(']')
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx:end_idx+1]
            
            # 验证修复后的JSON
            import json
            json.loads(json_str)
            return json_str
        except:
            return json_str

    def triage_blueprint_selection(self, supreme_law: str, candidate1_simulation: str, candidate2_simulation: str) -> Dict[str, Any]:
        """
        分诊检查 - 在两个都失败的模拟报告中选择更有前景的一个
        
        Args:
            supreme_law: 问题描述
            candidate1_simulation: 候选1的模拟响应 (Safe Anchor)
            candidate2_simulation: 候选2的模拟响应 (Challenger)
            
        Returns:
            分诊结果 {
                chosen_candidate: int,  # 1或2
                justification: str,     # 选择理由
                full_response: str      # 完整响应
            }
        """
        if self.verbose >= 1:
            print(f"[QualityGate] 🏥 开始分诊检查 - 在两个失败的模拟报告中选择更有前景的")
        
        triage_prompt = f"""You are **TriageAgent**, a senior software architect acting as a diagnostician. Two proposed blueprints, a "Safe Anchor" and a "Challenger", have **both failed** simulation.

Your mission is to perform a **high-level comparative analysis** to determine which of these two failed blueprints represents a **more promising path forward**. You will first lay out your reasoning, and only then make a final, definitive choice.

---

### **INPUTS FOR YOUR TRIAGE**

1. **The Supreme Law**: The ultimate definition of "correct".
    
    {supreme_law}
    
2. **The "Safe Anchor" Simulation Report (Candidate 1)**: The previous, more conservative attempt and its failure.
    
    **Simulation Report**: {candidate1_simulation}
    
3. **The "Challenger" Simulation Report (Candidate 2)**: The new, more innovative attempt from the mid-term review and its failure.
    
    **Simulation Report**: {candidate2_simulation}
    

---

### **YOUR TRIAGE PROTOCOL**

You must make your decision based on the principle of **"Forward Progress"**. A blueprint is "more promising" if its failure indicates that it is closer to solving the core strategic challenge of the problem, even if it introduced new, simpler bugs.

Your thinking process:

1. **Analyze Failure Modes**: Briefly review both simulation reports. Do they fail in the same way, or in different ways?
    
2. **Compare Failure Depth**: Based on the simulation traces, which failure appears to be closer to a correct solution? Which failure suggests the underlying approach was more sound?
    
3. **Formulate Justification**: Based on the above, construct a clear and concise argument for why one simulation failure is a better learning opportunity than the other.
    

---

### **YOUR TASK**

You MUST provide your response in the following **two-part format, in this exact order**.

#### **Part 1: The Justification**

<TRIAGE_JUSTIFICATION>...</TRIAGE_JUSTIFICATION>

- **Action**: Provide a concise, strategic justification explaining which blueprint should be chosen for the next round of analysis.
    
- **Content**: Your justification **must** compare the two candidates and answer the core question: **Why is the failure of one blueprint a better or more instructive learning opportunity than the other?**
    
    - **A-Grade Example 1 (Choosing the Challenger)**:
        
        > "The 'Safe Anchor' (Candidate 1) failed due to the known issue of off-by-one errors, showing the same fundamental flaw as before. The 'Challenger' (Candidate 2), while also failing, did so with a different type of error - its trace shows it successfully avoided the indexing problem but failed on a hash map operation. This indicates forward progress: we've moved from a strategic flaw to what appears to be a simpler implementation bug. Analyzing the 'Challenger' represents forward progress."
        
    - **A-Grade Example 2 (Choosing the Safe Anchor)**:
        
        > "The 'Challenger' (Candidate 2) simulation shows a catastrophic failure - crashing immediately with a fundamental error that suggests deep architectural problems. The 'Safe Anchor' (Candidate 1), while flawed, shows a trace that gets much further in the execution and fails on a more contained, understandable issue. Continuing to debug the 'Safe Anchor' is the more pragmatic path forward."
        

#### **Part 2: The Final Choice**

<CHOSEN_CANDIDATE>...</CHOSEN_CANDIDATE>

- **Action**: Based **only** on the reasoning you provided in <TRIAGE_JUSTIFICATION>, state your final choice.
    
- **Format**: Your response inside this tag MUST be a single digit:
    
    - 1 (if you choose the "Safe Anchor" blueprint)
        
    - 2 (if you choose the "Challenger" blueprint)
"""

        try:
            # 调用LLM进行分诊评估
            response = self.model.chat([{"role": "user", "content": triage_prompt}])
            
            if self.verbose >= 2:
                print(f"[QualityGate] TriageAgent原始响应: {response}")
            
            # 解析响应
            justification = self._extract_triage_justification(response)
            chosen_candidate = self._extract_chosen_candidate(response)
            
            if self.verbose >= 1:
                print(f"[QualityGate] 🏥 分诊完成 - 选择候选蓝图: {chosen_candidate}")
                print(f"[QualityGate] 🏥 分诊理由: {justification[:100]}..." if len(justification) > 100 else f"[QualityGate] 🏥 分诊理由: {justification}")
            
            return {
                "chosen_candidate": chosen_candidate,
                "justification": justification,
                "full_response": response
            }
            
        except Exception as e:
            if self.verbose >= 1:
                print(f"[QualityGate] 分诊检查时发生错误: {e}")
            return {
                "chosen_candidate": 1,  # 默认选择候选1
                "justification": "分诊系统出错，默认选择候选1",
                "full_response": ""
            }

    def _extract_triage_justification(self, response: str) -> str:
        """
        从分诊响应中解析 TRIAGE_JUSTIFICATION 内容
        
        解析策略：
        1. 首先尝试解析双标签 <TRIAGE_JUSTIFICATION>...</TRIAGE_JUSTIFICATION>
        2. 如果没有找到闭合标签，就解析单标签 <TRIAGE_JUSTIFICATION> 后面的内容直到下一个标签或结尾
        
        Args:
            response: 分诊的响应内容
            
        Returns:
            解析出的 TRIAGE_JUSTIFICATION 内容，如果没有找到则返回空字符串
        """
        if not response:
            return ""
        
        if self.verbose >= 2:
            print(f"[QualityGate] 🔍 开始解析 TRIAGE_JUSTIFICATION 标签...")
        
        # 策略1: 尝试解析双标签 <TRIAGE_JUSTIFICATION>...</TRIAGE_JUSTIFICATION>
        double_tag_pattern = r'<TRIAGE_JUSTIFICATION>\s*(.*?)\s*</TRIAGE_JUSTIFICATION>'
        double_match = re.search(double_tag_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if double_match:
            if self.verbose >= 2:
                print(f"[QualityGate] ✅ 找到双标签 TRIAGE_JUSTIFICATION")
            return double_match.group(1).strip()
        
        # 策略2: 如果没有找到双标签，尝试解析单标签后面的内容直到下一个标签
        single_tag_pattern = r'<TRIAGE_JUSTIFICATION>\s*(.*?)(?=<\w+>|$)'
        single_match = re.search(single_tag_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if single_match:
            if self.verbose >= 2:
                print(f"[QualityGate] ✅ 找到单标签 TRIAGE_JUSTIFICATION，解析到下一个标签的内容")
            return single_match.group(1).strip()
        
        # 如果都没有找到，返回空字符串
        if self.verbose >= 1:
            print(f"[QualityGate] ⚠️ 未找到 TRIAGE_JUSTIFICATION 标签")
        return ""

    def _extract_chosen_candidate(self, response: str) -> int:
        """
        从分诊响应中解析 CHOSEN_CANDIDATE 内容
        
        Args:
            response: 分诊的响应内容
            
        Returns:
            选择的候选者 (1或2)，如果解析失败则返回1作为默认值
        """
        if not response:
            return 1
        
        if self.verbose >= 2:
            print(f"[QualityGate] 🔍 开始解析 CHOSEN_CANDIDATE 标签...")
        
        # 查找 CHOSEN_CANDIDATE 标签内容
        candidate_pattern = r'<CHOSEN_CANDIDATE>\s*(\d+)\s*</CHOSEN_CANDIDATE>'
        candidate_match = re.search(candidate_pattern, response, re.IGNORECASE)
        
        if candidate_match:
            candidate_num = int(candidate_match.group(1))
            if candidate_num in [1, 2]:
                if self.verbose >= 2:
                    print(f"[QualityGate] ✅ 解析到选择的候选者: {candidate_num}")
                return candidate_num
        
        # 如果没有找到有效的选择，返回默认值1
        if self.verbose >= 1:
            print(f"[QualityGate] ⚠️ 未找到有效的 CHOSEN_CANDIDATE，默认选择候选1")
        return 1
