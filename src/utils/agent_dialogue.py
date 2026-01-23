from typing import Dict, Any, List, Optional, Tuple
import time

from constants.verboseType import *
from agents.BaseAgent import BaseAgent
from utils.content_checker import ContentChecker

class AgentDialogue:
    """
    Agent Dialogue Tool for facilitating structured conversations between two agents
    
    This is a tool, not an agent. It provides a framework for two different agents to engage in structured dialogue.
    The tool itself doesn't generate content, but rather calls the provided agents to generate dialogue content.
    """
    def __init__(
        self,
        verbose: int = 1,
        max_turns: int = 5
    ):
        """
        Initialize the Agent Dialogue Tool
        
        Args:
            verbose: Level of output detail
            max_turns: Maximum number of dialogue turns
        """
        self.verbose = verbose
        self.max_turns = max_turns
        self.dialogue_sessions = {}  # Store session IDs for different dialogues
        self.content_checker = ContentChecker(verbose=verbose)  # 内容检查器
    
    def prepare_agents(
        self,
        initiator_agent: BaseAgent,
        responder_agent: BaseAgent,
        discussion_topic: str,
        context: Dict[str, Any] = None,
        dialogue_id: str = None,
        max_turns: int = None
    ) -> Tuple[str, str, str]:
        """
        Prepare agents for dialogue by informing them about the upcoming discussion
        
        Args:
            initiator_agent: Agent initiating the discussion
            responder_agent: Agent responding to the discussion
            discussion_topic: Topic of discussion
            context: Dialogue context information
            dialogue_id: Dialogue ID (optional, will be generated if None)
            max_turns: Maximum number of dialogue turns
            
        Returns:
            Tuple of (dialogue_id, initiator_session_id, responder_session_id)
        """
        initiator_role = initiator_agent.agent_name
        responder_role = responder_agent.agent_name
        max_turns = max_turns or self.max_turns
        total_exchanges = max_turns   # Calculate actual back-and-forth exchanges
        
        # Handle dialogue ID
        if dialogue_id is None:
            import uuid
            dialogue_id = str(uuid.uuid4())


        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print(f"Prepare is starting...")


        # Create new sessions for each agent
        initiator_session_id = initiator_agent.start_new_session()
        responder_session_id = responder_agent.start_new_session()
        
        # Prepare dialogue history
        dialogue_history = []
        
        # Save session information
        self.dialogue_sessions[dialogue_id] = (initiator_session_id, responder_session_id, dialogue_history)
        
        # Prepare context message (will be injected at first dialogue turn, not in prepare stage)
        context_msg = ""
        if context:
            context_msg = "Here is the relevant context information:\n\n"
            for key, value in context.items():
                context_msg += f"## {key}\n{value}\n\n"
        
        # Inform initiator agent about the upcoming discussion
        initiator_prep_message = [
            {"role": "system", "content": (
                "You are a professional Solution Planning Expert. Your job is to help the team's code programmer fix buggy code with your professional knowledge. "
            )},
            # Do NOT send context in prepare stage
            {"role": "user", "content": f"but this stage is prepare stage, you just reply 'ok' to this message.when you get the start message, you can start the discussion."}
        ]
        print(f"initiator_prep_message: {initiator_prep_message}\n")
        initiator_agent._call_model(initiator_prep_message, session_id=initiator_session_id, include_history=True)
        
        
        # Inform responder agent about the upcoming discussion
        responder_prep_message = [
            {"role": "system", "content": (
                "You are the team's coder. You will receive the plannner's guidance in the following discussion\n"
            )},
            # Do NOT send context in prepare stage
            {"role": "user", "content": f"but this stage is prepare stage, you just reply 'ok' to this message.when you get the start message, you can start the discussion."}
        ]
        print(f"responder_prep_message: {responder_prep_message}\n")
        responder_agent._call_model(responder_prep_message, session_id=responder_session_id, include_history=True)
        
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"Preparing {initiator_role} and {responder_role} for dialogue (ID: {dialogue_id})")
            print(f"Topic: {discussion_topic}")
            print(f"Maximum exchanges: {total_exchanges}")
            print(f"{'='*50}\n")
            print(f"{'='*50}\n")
        
        return dialogue_id, initiator_session_id, responder_session_id
    
    def conduct_dialogue(
        self,
        initiator_agent: BaseAgent,
        responder_agent: BaseAgent,
        discussion_topic: str,
        context: Dict[str, Any] = None,
        max_turns: int = None,
        dialogue_id: str = None,
        continue_dialogue: bool = False,
        test_cases: List[Dict[str, Any]] = None,
        errors: Any = None,
        attention_analysis: Dict[str, Any] = None,
        thought_content : Dict[str, Any] = None,
        validation_threshold: float = 1.0
    ) -> Dict[str, Any]:
        """
        Facilitate dialogue between two agents
        
        This method doesn't generate any content itself, but calls the provided agents to generate dialogue content.
        It provides a structured framework for agents to take turns speaking and maintains a shared dialogue history.
        
        Args:
            initiator_agent: Agent initiating the discussion
            responder_agent: Agent responding to the discussion
            discussion_topic: Topic of discussion
            initial_prompt: Initial prompt to start the discussion
            context: Dialogue context information
            max_turns: Maximum number of dialogue turns (uses instance's max_turns if None)
            dialogue_id: Dialogue ID for continuing a previous dialogue
            continue_dialogue: Whether to continue a previous dialogue
            output_prompt: Optional explicit output instruction to be followed on the final turn
            errors: Optional errors info to show CTO
            test_case: Optional test cases summary to show CTO
            
        Returns:
            Dict with keys:
            - history: the dialogue history list
            - final_output: the last assistant message content (final turn output)
            - dialogue_id: the dialogue identifier
        """
        initiator_role = initiator_agent.agent_name
        responder_role = responder_agent.agent_name
        max_turns = max_turns or self.max_turns
        
        # Normalize errors and test_case into strings for prompt rendering
        try:
            if isinstance(errors, list):
                errors = "\n".join([str(e) for e in errors])
            else:
                errors = str(errors) if errors is not None else ""
        except Exception:
            errors = str(errors) if errors is not None else ""

        init_wrong_code = context.get("Current Wrong Code")
        problem_description=context.get("Problem Description")
        sample_io=context.get("Sample I/O")
        
        # Check if continuing a previous dialogue
        if continue_dialogue and dialogue_id in self.dialogue_sessions:
            initiator_session_id, responder_session_id, dialogue_history = self.dialogue_sessions[dialogue_id]
            
            # Set active sessions for agents
            initiator_agent.set_active_session(initiator_session_id)
            responder_agent.set_active_session(responder_session_id)
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{'='*50}")
                print(f"Continuing dialogue between {initiator_role} and {responder_role} (ID: {dialogue_id})")
                print(f"Topic: {discussion_topic}")
                print(f"Maximum turns: {max_turns}")
                print(f"{'='*50}\n")
        else:
            # Prepare agents and create new sessions
            dialogue_id, initiator_session_id, responder_session_id = self.prepare_agents(
                initiator_agent, responder_agent, discussion_topic, context, dialogue_id, max_turns
            )
            
            # Get dialogue history (should be empty for new dialogues)
            _, _, dialogue_history = self.dialogue_sessions[dialogue_id]
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{'='*50}")
                print(f"Starting dialogue between {initiator_role} and {responder_role} (ID: {dialogue_id})")
                print(f"Topic: {discussion_topic}")
                print(f"Maximum turns: {max_turns}")
                print(f"{'='*50}\n")
        
        # Get current dialogue turn
        current_turn = len(dialogue_history) // 2  # Each complete turn consists of two messages
        laststeprun=" "
        failed_codes = []  # 错误代码合集
        # Dialogue loop
        is_pass_sample = False


        for turn in range(current_turn, max_turns):
            # Determine current speaker and listener
            if turn % 2 == 0:  # Even turns, initiator speaks
                current_agent = initiator_agent
                current_role = initiator_role
                other_role = responder_role
                session_id = initiator_session_id
            else:  # Odd turns, responder speaks
                current_agent = responder_agent
                current_role = responder_role
                other_role = initiator_role
                session_id = responder_session_id
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n--- Turn {turn+1}/{max_turns} ---")
                print(f"Current speaker: {current_role}")
            
            # Prepare the message for the current agent
            # Build turn-specific user messages
            # Prefer using only the Problem Description from context if available
            if context:
                if isinstance(context, dict) and context.get("Problem Description"):
                    problem_description = str(context.get("Problem Description"))
                context_str = str(context)
            else:
                context_str = ""
            if turn % 2 == 0:
                
                example_block = (
    "\nYour trace must be a **goal-oriented simulation** aimed at pinpointing the **exact cause of the error** reported in the `Failure Log`. You MUST choose one of the two analysis styles below, based on the code's structure.\n\n"
    "**--- Analysis Style 1: Sequential Logic (for `if/elif`, loops) ---**\n"
    "*Use this to find the exact line where logic goes wrong.*\n"
    "**Abstract Example (Goal: Find why input `X` produced output `Y` instead of `Z`):**\n"
    "Input: `value = X`\n"
    "- Step 1: Code checks `if value > 100`. Result: NO.\n"
    "- Step 2: Code checks `elif value > 50`. Result: YES.\n"
    "- Step 3: Code enters this block and **incorrectly** returns `Y`.\n"
    "- **Conclusion from Trace**: The trace proves the failure is caused by the **incorrect order** of checks, which led to a **premature exit** before the correct condition for `Z` could be evaluated.\n\n"
    
    "**--- Analysis Style 2: Recursive / Dependency Logic ---**\n"
    "*Use this to find the faulty base case or the exact point of a crash.*\n"
    "**Abstract Example (Goal: Find the cause of an `IndexError` for input `N`):**\n"
    "Input: `n = N`\n"
    "- To calculate `f(N)`, the code attempts to access `results[N-1]`.\n"
    "- At this point, the `results` list is `[item0, item1]`. Its length is 2.\n"
    "- The required index `N-1` is `3-1=2`.\n"
    "- Accessing `results[2]` on a list of length 2 causes an **IndexError**.\n"
    "- **Conclusion from Trace**: The trace proves the crash is caused by the **data structure (`results`) not being correctly populated** before it is accessed by the recursive logic."
)
                # CTO (initiator) speaks on even turns
                #if turn == 0 and len(dialogue_history) == 0:
                if turn  == 0:
                    # Inject context only in the very first CTO message
                    ctx_block = f"\n\nContext:\n{context_str}" if context_str else ""
                    user_message = (
        f"Debug the buggy code from first principles. Your response is the **first and potentially only chance** to solve the problem. You must be rigorous. Provide your response using ONLY the following **three** tags in order:\n\n"
        f"### **CONTEXT FOR YOUR ANALYSIS**\n"
        f"1. **The Supreme Law (Ground Truth)**: \n{problem_description}\n{sample_io}\n"
        f"2. **The Flawed Code Under Scrutiny**: \n{init_wrong_code}\n"
        f"3. **The Specific Failure Log**: \n{errors}\n"
        f"4. **Preliminary Analyst Notes (A clue, may be flawed)**: \n{attention_analysis}\n\n"
        
        f"--- \n"
        
        f"### **YOUR TASKS**\n"
        f"1. `<EXECUTION_TRACE>`: Provide a detailed, step-by-step trace of the `Flawed Code` with the failing input from the `Failure Log`. Your trace's goal is to **reproduce and explain the exact error**. {example_block}\n\n"
        f"2. `<ROOT_CAUSE_ANALYSIS>`: Based on your trace, you must perform a **definitive root cause analysis**.\n"
        f"   a. **Identify the Flaw**: Pinpoint the exact line of code and the specific logical or calculation error that your trace revealed is the direct cause of the failure.\n"
        f"   b. **Establish the 'Rule of Truth'**: **Now, you MUST go back to the Supreme Law.** What is the single, correct, and literal 'Rule of Truth' that the flawed code violated? You must explicitly resolve any contradictions from the `Analyst Notes`.\n"
        f"   c. **Identify the Correct Algorithmic Pattern (if necessary)**: If the 'Rule of Truth' involves a complex pattern (like Memoization/DP), you must identify it.\n\n"
        f"3. `<FINAL_CORRECTION_BLUEPRINT>`: **This is your final, actionable plan.** Based on the **'Rule of Truth'** and the **Correct Algorithmic Pattern**, provide a clear, step-by-step, **high-level pseudocode** algorithm for the Coder.\n"
    )
                else:
                    # 后续发言的处理 (turn > 0)
                    last_content = dialogue_history[-1]["content"] if dialogue_history else ""
                    user_message = (
        f"## CRITICAL FAILURE: Your previous Correction Blueprint has failed.\n\n"
        f"The Coder's implementation of your plan still fails. This means your previous analysis was **fundamentally flawed**. You MUST abandon your previous line of reasoning and find a new, superior approach.\n\n"
        f"### **NEW CONTEXT FOR YOUR RE-ANALYSIS**\n"
        f"1. **The Supreme Law (Ground Truth remains the same)**: \n{problem_description}\n{sample_io}\n"
        f"2. **The NEW Flawed Code (Based on YOUR last blueprint)**: \n{last_content}\n"
        f"3. **The NEW Specific Failure Log**: \n{errors}\n"
        f"4. **Original Analyst Notes (for historical context)**: \n{attention_analysis}\n\n"
        
        f"--- \n"
        
        f"### **YOUR NEW MISSION: A Deeper, Contrarian Analysis**\n\n"
        f"You MUST provide a new, more precise analysis. Return ONLY the three tags: `<EXECUTION_TRACE>`, `<ROOT_CAUSE_ANALYSIS>`, and a **new, more detailed `<FINAL_CORRECTION_BLUEPRINT>`**.\n"
        f"Your new trace MUST pinpoint the new error, and your new blueprint MUST propose a **fundamentally different** approach."
    )
               
            else:
                
                # Coder (responder) speaks on odd turns
                last_content = dialogue_history[-1]["content"] if dialogue_history else ""
                # Directly pass full previous planenr message without parsing
                
                if turn %2 == 1 :
                    user_message = (
    f"## Your Mission: Translate the Blueprint into Production-Ready Code\n\n"
    f"You have received a `<CORRECTION_BLUEPRINT>` from the Solution Planning Expert. Your task is to translate this blueprint into clean, executable python code. **You must always produce a full code implementation.**\n\n"
    f"### 1. The Blueprint (Your Primary Directive)\n{last_content}\n\n"
    f"### 2. The Supreme Law (Your Ultimate Reference for Disambiguation)\n"
    f"**If any part of the blueprint is vague or seems contradictory, you MUST use the `Problem Description` and `Sample I/O` to deduce the correct implementation detail.**\n"
    f"Original Problem: {problem_description}\n"
    f"Sample I/O: {sample_io}\n"
    f"Analyst's Notes: {attention_analysis}\n\n"
    f"### 3. Last Known Failure (Context for what to fix)\n"
    f"Errors: {errors}\n\n"
    
    f"## Output (exactly three parts in order)\n\n"
    f"<thought>\n"
    "My thinking process is a **Blueprint-to-Code Mapping with Critical Implementation Choices**. I will not refuse to code.\n"
    "1.  **Overall Blueprint Review**: I will first read the entire blueprint to understand the high-level plan.\n"
    "2.  **Step-by-Step Translation & Critical Thinking**: For EACH step in the blueprint, I will:\n"
    "    a.  Translate the step into a concrete code snippet.\n"
    "    b.  **Critically consider the implementation details.** *(Abstract Example of the required thinking: 'The blueprint says 'check for X'. The `Problem Description` gives an example where X must be handled in a specific way. Therefore, my code for this step MUST implement that specific way, not a naive alternative.')*\n"
    "3.  **Final Assembly**: I will assemble the critically-thought-out code snippets into the final, complete function.\n"
    "</thought>\n"
    
    f"<recheck>\n"
    "I have double-checked my code. It is a robust and faithful implementation of the blueprint, with all ambiguous details resolved by referencing the `Problem Description` and `Sample I/O` as the supreme law. The code is complete and ready.\n"
    "</recheck>\n"
    
    f"<CODE>\n"
    "your new, corrected code (must be a full and runnable function)\n"
    "</CODE>\n"
)
                
               

            # Send system + user role messages
            messages = [
                {"role": "system", "content": "don't reply the same answer in every turn,please analyze The other party's reply,especially for the planner"},
                {"role": "system", "content": " do not modify helper functions,because it's must be correct"},
                {"role": "user", "content": user_message}
            ]
            # Call current agent to generate response
            start_time = time.time()
            response = current_agent._call_model(messages, session_id=session_id, include_history=True)
            elapsed_time = time.time() - start_time
            
            # 过滤响应内容 - 移除thought和recheck标签
            response = self._filter_response_content(response, current_role)
            
            # 内容重复检查 - 在记录到历史之前进行检查
            if turn >= 1:
                # 找到当前agent上一次的发言内容
                if turn == 1:
                    # 首轮：从context中提取代码作为previous_content
                    if context and "Current Wrong Code" in context:
                        previous_content = context["Current Wrong Code"]
                    else:
                        previous_content = ""
                else:
                    previous_content = self._find_previous_content_by_agent(dialogue_history, current_role)
                if previous_content:
                    response = self._check_and_retry_if_duplicate(
                        current_agent, response, previous_content, messages, session_id, current_role, turn
                    )
            
            # Record response to shared dialogue history
            dialogue_history.append({
                "role": "assistant",
                "content": response,
                "agent": current_role,
                "time": elapsed_time,
                "turn": turn + 1
            })
            
            # Update session information
            self.dialogue_sessions[dialogue_id] = (initiator_session_id, responder_session_id, dialogue_history)
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n[{current_role}]: {response}")
                print(f"(Time: {elapsed_time:.2f} seconds)")

            # If coder just responded and provided <CODE>, validate against Sample I/O
            if turn %2 == 1:
                print(f"\n\n=====>start to validate the code<=====\n\n")

                try:
                    import re
                    # Extract <CODE>
                    m_code = re.search(r"<CODE>\s*(.*?)\s*</CODE>", response, re.DOTALL | re.IGNORECASE)
                    if not m_code:
                        m_code = re.search(r"<CODE>\s*(.*?)\s*<CODE>", response, re.DOTALL | re.IGNORECASE)
                    if m_code:
                        candidate_code = m_code.group(1).strip()
                        # Optional sanitize
                        try:
                            from utils.code_sanitizer import sanitize_code_prefix
                            candidate_code = sanitize_code_prefix(candidate_code)
                        except Exception:
                            pass
                        # Sample I/O from context
                        sample_io_list = test_cases
                        
                        if sample_io_list:
                            if self.verbose >= VERBOSE_MINIMAL:
                                print("\nInline validation: testing <CODE> against Sample I/O...")
                            # Run DebugAgent test
                            try:
                                from agents.core.DebugAgent import DebugAgent
                                dbg = DebugAgent(verbose=self.verbose)
                                inline_test = dbg.test_with_sample_io(code=candidate_code, sample_io=sample_io_list, timeout=10)
                                
                                # 使用validation_threshold计算通过率
                                total_tests = len(sample_io_list)
                                failed_tests_count = len(inline_test.get('failed_tests', []))
                                passed_tests = total_tests - failed_tests_count
                                pass_rate = passed_tests / total_tests if total_tests > 0 else 0
                                validation_passed = pass_rate >= validation_threshold
                                
                                if self.verbose >= VERBOSE_MINIMAL:
                                    print(f"Inline validation: {passed_tests}/{total_tests} passed (通过率: {pass_rate:.2%}, 阈值: {validation_threshold:.0%})")
                                
                                if validation_passed:
                                    if self.verbose >= VERBOSE_MINIMAL:
                                        print("Inline validation passed. Ending dialogue.")
                                    is_pass_sample = True
                                    # Overwrite last content to ensure upstream can extract <CODE>
                                    dialogue_history[-1]["content"] = response
                                    break
                                else:
                                    # 将失败的代码添加到错误代码合集中
                                    failed_codes.append(candidate_code)
                                    if self.verbose >= VERBOSE_MINIMAL:
                                        print(f"Added failed code to collection. Total failed codes: {len(failed_codes)}")
                                    
                                    # Update errors string for next CTO turn (do not mutate context)
                                    failed_tests = inline_test.get("failed_tests", [])
                                    parts = []
                                    for ft in failed_tests:
                                        parts.append(f"Assertion: {ft.get('test')}")
                                        parts.append(f"Error: {ft.get('error')}")
                                    errors = "\n".join(parts)
                                    if self.verbose >= VERBOSE_MINIMAL:
                                        print("Inline validation failed. Updated errors for next turn.")
                            except Exception as e:
                                if self.verbose >= VERBOSE_MINIMAL:
                                    print(f"Inline validation error: {e}")
                except Exception:
                    pass
            
            # If even turn, extract and process <STEP_RUN> tag
            elif turn % 2 == 0:
                print(f"\n\n=====>start to process STEP_RUN<=====\n\n")
                
                try:
                    import re
                    # Extract <STEP_RUN>
                    m_step = re.search(r"<STEP_RUN>\s*(.*?)\s*</STEP_RUN>", response, re.DOTALL | re.IGNORECASE)
                    if m_step:
                        step_content = m_step.group(1).strip()
                        laststeprun = step_content  # 将解析的内容存储到laststeprun中
                        
                    else:
                        laststeprun = ""  # 如果没有找到STEP_RUN标签，清空laststeprun
                        if self.verbose >= VERBOSE_MINIMAL:
                            print("No STEP_RUN tag found in response.")
                except Exception as e:
                    laststeprun = ""  # 发生错误时清空laststeprun
                    if self.verbose >= VERBOSE_MINIMAL:
                        print(f"STEP_RUN processing error: {e}")

            # Check if response declares success via IS_PASS_SAMPLE tag
            try:
                import re
                if re.search(r"<IS_PASS_SAMPLE>\s*true\s*</IS_PASS_SAMPLE>", response, re.IGNORECASE):
                    is_pass_sample = True
                    break
            except Exception:
                pass
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print(f"Dialogue between {initiator_role} and {responder_role} completed (ID: {dialogue_id})")
            print(f"{'='*50}\n")
        
        final_output = dialogue_history[-1]["content"] if dialogue_history else ""
        return {"history": dialogue_history, "final_output": final_output, "dialogue_id": dialogue_id, "is_pass_sample": is_pass_sample}
    
    def get_dialogue_session(self, dialogue_id: str) -> Tuple[str, str, List[Dict[str, str]]]:
        """
        获取对话会话信息
        
        Args:
            dialogue_id: 对话ID
            
        Returns:
            (发起者会话ID, 响应者会话ID, 对话历史)
        """
        if dialogue_id in self.dialogue_sessions:
            return self.dialogue_sessions[dialogue_id]
        else:
            return None, None, []
    
    def clear_dialogue_session(self, dialogue_id: str) -> bool:
        """
        清除对话会话
        
        Args:
            dialogue_id: 对话ID
            
        Returns:
            是否成功清除
        """
        if dialogue_id in self.dialogue_sessions:
            del self.dialogue_sessions[dialogue_id]
            return True
        else:
            return False
    
    def summarize_dialogue(
        self,
        dialogue_history: List[Dict[str, str]],
        summarizer_agent: BaseAgent,
        summary_prompt: str = None,
        topic: str = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        使用指定的智能体总结对话内容
        
        这个方法本身不会生成任何内容，而是通过调用提供的summarizer_agent来生成总结。
        
        Args:
            dialogue_history: 对话历史记录
            summarizer_agent: 用于总结的智能体
            summary_prompt: 总结提示，如果为None，则使用默认提示
            topic: 对话主题，用于生成更具体的总结提示
            session_id: 会话ID，如果为None则创建新会话
            
        Returns:
            对话总结，包含原始总结文本和结构化信息
        """
        if not summary_prompt:
            summary_prompt = f"""Please summarize the following conversation about "{topic or 'this topic'}"

Please analyze the conversation content, extract the following information:
1. Main discussion points and key viewpoints
2. Consensus reached by both parties
3. Existence of disagreements or unresolved issues
4. Proposed solutions or suggestions
5. Finalized technical approach and implementation strategy

Please organize your summary in a structured way and ensure it is concise, comprehensive, and objective.

Conversation History:
{{dialogue_text}}
"""
        
        # 构建对话文本
        dialogue_text = ""
        for msg in dialogue_history:
            if "agent" in msg:
                turn_info = f"(Turn {msg.get('turn', '?')})" if "turn" in msg else ""
                dialogue_text += f"[{msg['agent']} {turn_info}]: {msg['content']}\n\n"
            elif "role" in msg and msg["role"] != "system":
                dialogue_text += f"[{msg['role']}]: {msg['content']}\n\n"
        
        # 构建总结提示
        messages = [
            {"role": "system", "content": "You are a professional dialogue summarizer, skilled at extracting key information, consensus, and disagreements from dialogue."},
            {"role": "user", "content": summary_prompt.format(dialogue_text=dialogue_text)}
        ]
        
        # 调用总结智能体
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print(f"Generating dialogue summary...")
            
        # 创建新会话或使用指定会话
        if session_id is None:
            session_id = summarizer_agent.start_new_session()
        else:
            summarizer_agent.set_active_session(session_id)
            
        summary = summarizer_agent._call_model(messages, session_id=session_id, include_history=False)
        
        # 尝试提取结构化信息
        import re
        import json
        
        # 寻找JSON格式的内容
        json_match = re.search(r'```json\s*(.*?)\s*```', summary, re.DOTALL)
        structured_data = None
        
        if json_match:
            try:
                json_str = json_match.group(1)
                structured_data = json.loads(json_str)
            except (json.JSONDecodeError, IndexError):
                pass
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\nDialogue Summary:")
            print(f"{summary[:500]}..." if len(summary) > 500 else summary)
            print(f"{'='*50}\n")
            
        return {
            "summary": summary,
            "structured_data": structured_data,
            "topic": topic,
            "session_id": session_id
        }
    
    def _check_and_retry_if_duplicate(
        self, 
        current_agent: BaseAgent, 
        response: str, 
        previous_content: str, 
        original_messages: List[Dict[str, str]], 
        session_id: str, 
        current_role: str,
        turn_number: int = 1,
        max_retries: int = 1
    ) -> str:
        """
        检查内容是否重复，如果重复则要求重新生成
        
        Args:
            current_agent: 当前发言的agent
            response: 当前响应
            previous_content: 前一次的内容
            original_messages: 原始消息
            session_id: 会话ID
            current_role: 当前角色名
            max_retries: 最大重试次数
            
        Returns:
            最终的响应内容
        """
        if self.verbose >= 1:
            print(f"\n[ContentChecker] 检查 {current_role} 的响应是否重复...")
        
        # 使用ContentChecker检查相似性
        check_result = self.content_checker.check_content_similarity(
            current_response=response,
            previous_content=previous_content,
            model=current_agent.model,
            turn_number=turn_number
        )
        
        # 如果不相似，直接返回原响应
        if not check_result["is_similar"]:
            if self.verbose >= 1:
                print(f"[ContentChecker] {current_role} 的响应通过检查")
            return response
        
        # 如果相似，要求重新生成
        if self.verbose >= 1:
            print(f"[ContentChecker] {current_role} 的响应被检测为重复，要求重新生成...")
            print(f"[ContentChecker] 反馈: {check_result['feedback']}")
        
        # 进行重试
        for retry_count in range(max_retries):
            if self.verbose >= 1:
                print(f"[ContentChecker] 第 {retry_count + 1}/{max_retries} 次重试...")
            
            # 生成重试消息
            retry_message = self.content_checker.generate_retry_message(
                original_message=original_messages[-1]["content"],
                feedback=check_result["feedback"]
            )
            
            # 构建重试的消息
            retry_messages = [
                {"role": "system", "content": "You are being asked to provide a different response because your previous response was too similar to earlier content."},
                {"role": "user", "content": retry_message}
            ]
            
            # 重新生成响应
            try:
                start_time = time.time()
                new_response = current_agent._call_model(retry_messages, session_id=session_id, include_history=True)
                elapsed_time = time.time() - start_time
                
                # 过滤重新生成的响应
                new_response = self._filter_response_content(new_response, current_role)
                
                if self.verbose >= 1:
                    print(f"[ContentChecker] {current_role} 重新生成响应 (耗时: {elapsed_time:.2f}秒)")
                
                # 再次检查新响应是否仍然重复
                new_check_result = self.content_checker.check_content_similarity(
                    current_response=new_response,
                    previous_content=previous_content,
                    model=current_agent.model,
                    turn_number=turn_number
                )
                
                if not new_check_result["is_similar"]:
                    if self.verbose >= 1:
                        print(f"[ContentChecker] {current_role} 重新生成的响应通过检查")
                    return new_response
                else:
                    if self.verbose >= 1:
                        print(f"[ContentChecker] {current_role} 重新生成的响应仍然重复")
                    check_result = new_check_result  # 更新反馈信息
                    
            except Exception as e:
                if self.verbose >= 1:
                    print(f"[ContentChecker] 重新生成响应时出错: {e}")
                break
        
        # 如果所有重试都失败，返回最后一次的响应并警告
        if self.verbose >= 1:
            print(f"[ContentChecker] 警告: {current_role} 在 {max_retries} 次重试后仍然生成重复内容，使用最后一次响应")
        
        return new_response if 'new_response' in locals() else response
    
    def _find_previous_content_by_agent(self, dialogue_history: List[Dict[str, Any]], current_role: str) -> Optional[str]:
        """
        找到当前agent上一次的发言内容
        
        Args:
            dialogue_history: 对话历史
            current_role: 当前agent的角色名
            
        Returns:
            上一次该agent的发言内容，如果没有则返回None
        """
        # 从最新的记录开始往前查找
        for i in range(len(dialogue_history) - 1, -1, -1):
            if dialogue_history[i].get("agent") == current_role:
                if self.verbose >= 2:
                    print(f"[ContentChecker] 找到 {current_role} 上一次发言位置: {i}")
                return dialogue_history[i]["content"]
        
        if self.verbose >= 2:
            print(f"[ContentChecker] 未找到 {current_role} 的历史发言")
        return None
    
    def _filter_response_content(self, response: str, current_role: str) -> str:
        """
        过滤响应内容，移除指定的标签
        
        Args:
            response: 原始响应内容
            current_role: 当前agent角色
            
        Returns:
            过滤后的响应内容
        """
        import re
        
        # 只对CodeAgent的响应进行过滤
        if "CodeAgent" not in current_role and "code" not in current_role.lower():
            return response
        
        if self.verbose >= 2:
            print(f"[Filter] 开始过滤 {current_role} 的响应内容...")
        
        filtered_response = response
        
        # 移除 <thought> 或 <tought> 标签及其内容
        filtered_response = re.sub(r'<tought>.*?</tought>', '', filtered_response, flags=re.DOTALL | re.IGNORECASE)
        filtered_response = re.sub(r'<thought>.*?</thought>', '', filtered_response, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除 <recheck> 标签及其内容
        filtered_response = re.sub(r'<recheck>.*?</recheck>', '', filtered_response, flags=re.DOTALL | re.IGNORECASE)
        
        # 清理多余的空白行
        filtered_response = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered_response)
        filtered_response = filtered_response.strip()
        
        if self.verbose >= 2:
            if filtered_response != response:
                print(f"[Filter] {current_role} 的响应已过滤，原长度: {len(response)}, 过滤后长度: {len(filtered_response)}")
            else:
                print(f"[Filter] {current_role} 的响应无需过滤")
        
        return filtered_response 