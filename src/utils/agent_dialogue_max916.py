from typing import Dict, Any, List, Optional, Tuple
import time

from constants.verboseType import *
from agents.BaseAgent import BaseAgent

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
                "You are a CTO. Your job is to help the team's code programmer fix buggy code. "
            )},
            # Do NOT send context in prepare stage
            {"role": "user", "content": f"but this stage is prepare stage, you just reply 'ok' to this message.when you get the start message, you can start the discussion."}
        ]
        print(f"initiator_prep_message: {initiator_prep_message}\n")
        initiator_agent._call_model(initiator_prep_message, session_id=initiator_session_id, include_history=True)
        
        
        # Inform responder agent about the upcoming discussion
        responder_prep_message = [
            {"role": "system", "content": (
                "You are the team's coder. You will receive the CTO's guidance in the following discussion\n"
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
        initial_prompt: str,
        context: Dict[str, Any] = None,
        errors: List[str] = None,
        max_turns: int = None,
        dialogue_id: str = None,
        continue_dialogue: bool = False,
        output_prompt: str = None
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
            
        Returns:
            Dict with keys:
            - history: the dialogue history list
            - final_output: the last assistant message content (final turn output)
            - dialogue_id: the dialogue identifier
        """
        initiator_role = initiator_agent.agent_name
        responder_role = responder_agent.agent_name
        max_turns = max_turns or self.max_turns


        
        
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
                print(f"[Initial Prompt]: {initial_prompt}\n")
        
        # Get current dialogue turn
        current_turn = len(dialogue_history) // 2  # Each complete turn consists of two messages
        # control coder
        control_i = 0
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
                # CTO (initiator) speaks on even turns
                if turn == 0 and len(dialogue_history) == 0:
                    # Inject context only in the very first CTO message
                    ctx_block = f"\n\nContext:\n{context_str}" if context_str else ""
                    user_message = (
                        "Start analyzing the buggy code now (this is not the prepare stage). "
                        f"the context is\n\n{ctx_block}\n\n"
                        f"Attention the errors is\n\n{errors}\n\n"
                        f"Share your thoughts with {other_role}. Return ONLY the following blocks:\n"
                        "<BUG_LOCATION>...<BUG_LOCATION>\n<BUG_IDENTIFICATION>...<BUG_IDENTIFICATION>\n<REPAIRED_CODE>according the <BUG_LOCATION> and <BUG_IDENTIFICATION>,write the correct code here<REPAIRED_CODE>\n"
                        "Reminder (every turn): digest coder <REASON>; do not repeat; provide a minimal patch; mentally simulate failing Sample I/O;"
                        
                    )
                else:
                    last_content = dialogue_history[-1]["content"] if dialogue_history else ""
                    user_message = (
                        f"review the original problem :\n{problem_description}\n\n"
                        "Reminder (every turn): digest coder <REASON>; do not repeat; provide a minimal patch; mentally simulate failing Sample I/O; "
                        f"{other_role}: {last_content}\n\n"
                        "Read the coder's <REASON> Including 'Why previous failed' carefully . Do not repeat the same approach. "
                        " Return ONLY:\n"
                        "<THOUGHT>according to the <REASON> and the original problem,write your fixed thought here<THOUGHT>\n\n<REPAIRED_CODE>according to the <THOUGHT>,write the correct code here,do not repeat the previous code<REPAIRED_CODE>\n\n"
                        
                    )
               
            else:
                control_i += 1
                # Coder (responder) speaks on odd turns
                last_content = dialogue_history[-1]["content"] if dialogue_history else ""
                # Extract only the <REPAIR_CODE> block from the previous CTO reply
                repair_code_text = ""
                if last_content:
                    import re
                    m = re.search(r"<REPAIRED_CODE>(.*?)</REPAIRED_CODE>", last_content, re.DOTALL | re.IGNORECASE)
                    if not m:
                        m = re.search(r"<REPAIRED_CODE>(.*?)<REPAIRED_CODE>", last_content, re.DOTALL | re.IGNORECASE)
                    if m:
                        repair_code_text = m.group(1).strip()
                if turn == 1 and context_str:
                    example_block = (
                        "\nExample (analysis style in <REASON>):\n"
                        "Buggy code with inline step-by-step comments (for assert sum3(1,2,3)==6):\\n"
                        "def sum3(a: int, b: int, c: int) -> int:\\n"
                        "    temp = a + b      # a=1, b=2 -> temp=3\\n"
                        "    re = temp - c     # c=3 -> re=0  (Problem: should be +c)\\n"
                        "    return re         # returns 0, expected 6\\n"
                    )
                    user_message = (
                        f"Context:\n{context_str}\n\n"
                        f"CTO provided <REPAIR_CODE> only:\n<REPAIR_CODE>\n{repair_code_text}\n</REPAIR_CODE>\n\n"
                        "You received <REPAIR_CODE>. Step by step, verify whether the proposed fix will pass the failing Sample I/O in the context. "
                        "Annotate each checked line with its run result and the problem if any inside <REASON>. "
                        "The analysis way MUST follow the example block, such as:\n" + example_block + "\n"
                        "Return ONLY one of the following:\n"
                        "if Case fail:<IS_PASS_SAMPLE>false</IS_PASS_SAMPLE> \n<REASON>...your multi-line analysis follow the example block...</REASON>\n"
                        "if Case pass: <IS_PASS_SAMPLE>true</IS_PASS_SAMPLE>\n<FINAL_CODE>\nbefore full corrected code,you must analyze the code is correct  AND NOT OTHERS LIKE <REASON> or <REPAIRED_CODE> TAGS\n<FINAL_CODE>\n"
                        "Reminder (every turn): analyze CTO <REPAIRED_CODE> step-by-step on failing Sample I/O; if any step fails, provide a rigorous multi-line <REASON> with inline checks; only include <FINAL_CODE>.\n"
                    )
                else:

                    user_message =[]
                    if control_i == 3:
                        user_message.append(f"review the original problem :\n{problem_description}\n\n")
                        control_i = 0  
                    example_block = (
                        "\nExample (analysis style in <REASON>):\n"
                        "Buggy code with inline step-by-step comments (for assert sum3(1,2,3)==6):\\n"
                        "def sum3(a: int, b: int, c: int) -> int:\\n"
                        "    temp = a + b      # a=1, b=2 -> temp=3\\n"
                        "    re = temp - c     # c=3 -> re=0  (Problem: should be +c)\\n"
                        "    return re         # returns 0, expected 6\\n"
                    )
                    user_message.extend(
                        f"CTO provided <REPAIR_CODE> only:\n<REPAIR_CODE>\n{repair_code_text}\n</REPAIR_CODE>\n\n"
                        "You received <REPAIR_CODE>. Step by step, verify whether the proposed fix will pass the failing Sample I/O in the context. "
                        "Annotate each checked line with its run result and the problem if any inside <REASON>. "
                        "The analysis way MUST follow the example block, such as:\n" + example_block + "\n"
                        "Return ONLY one of the following:\n"
                        "if Case fail:<IS_PASS_SAMPLE>false</IS_PASS_SAMPLE> \n<REASON>...your multi-line analysis follow the example block...</REASON>\n"
                        "if Case pass: <IS_PASS_SAMPLE>true</IS_PASS_SAMPLE>\n<FINAL_CODE>\nbefore full corrected code,you must analyze the code is correct or not,and write the correct code only here AND NOT OTHERS LIKE <REASON> or <REPAIRED_CODE> TAGS\n<FINAL_CODE>\n"
                        "Reminder (every turn): analyze CTO <REPAIRED_CODE> step-by-step on failing Sample I/O; if any step fails, provide a rigorous multi-line <REASON> with inline checks; only include <FINAL_CODE>.\n"
                    )

                    user_message = "".join(user_message)
                

      
       

            # Send system + user role messages
            messages = [
                {"role": "system", "content": "don't reply the same answer in every turn,please analyze The other party's reply,especially for the cto"},
                {"role": "system", "content": " do not modify helper functions,because it's must be correct"},
                {"role": "user", "content": user_message}
            ]
            # Call current agent to generate response
            start_time = time.time()
            response = current_agent._call_model(messages, session_id=session_id, include_history=True)
            elapsed_time = time.time() - start_time
            
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