from typing import Dict, Any, List, Optional

from ..BaseAgent import BaseAgent
from constants.verboseType import *

class CodeAgent(BaseAgent):
    """
    Code Generation Agent, responsible for generating code based on problem description, test cases, and technical plan
    """
    
    def __init__(
        self,
        model,
        agent_name: str = "CodeAgent",
        verbose: int = VERBOSE_MINIMAL,
    ):
        """
        Initialize the Code Generation Agent
        
        Args:
            model: Model to use
            agent_name: Agent name
            verbose: Verbosity level
        """
        super().__init__(
            model=model,
            agent_name=agent_name,
            verbose=verbose,
            prompt_module_path="core.code"
        )
    
    def _generate_prompt(
        self,
        problem_description: str,
        test_cases: Dict[str, Any],
        technical_plan: Dict[str, Any],
        language: str = "Python3",
        problem_sample_io: str = None,
        attention_analysis: Dict[str, Any] = None,
        error_code: str = None,
        error_info: str = None
    ) -> List[Dict[str, str]]:
        """
        Generate code generation prompt
        
        Args:
            problem_description: Problem description
            test_cases: Test cases
            technical_plan: Technical plan
            language: Programming language
            problem_sample_io: Sample input/output examples
            
        Returns:
            Message list
        """
        return self.prompt_module.get_messages(
            problem_description=problem_description,
            test_cases=test_cases,
            technical_plan=technical_plan,
            language=language,
            problem_sample_io=problem_sample_io,
            attention_analysis=attention_analysis,
            error_code=error_code,
            error_info=error_info
        )
    
    def _generate_init_prompt(
        self,
        problem_description: str,
        test_cases: Dict[str, Any],
        language: str = "Python3",
 
    ) -> List[Dict[str, str]]:
        """
        Generate code generation prompt
        
        Args:
            problem_description: Problem description
            test_cases: Test cases
            technical_plan: Technical plan
            language: Programming language
            problem_sample_io: Sample input/output examples
            
        Returns:
            Message list
        """
        return self.prompt_module.get_messages_1(
            problem_description=problem_description,
            test_cases=test_cases,
        )

    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        Process model response, extract code and explanation.
        Handles nested code blocks within <INFO> tags.
        
        Args:
            response: Model response
            
        Returns:
            Processed result containing code and explanation
        """
        import re
        
        code = ""
        explanation = response
        #-------
        code_block_pattern = r'(```(?:[a-z]+)?\s*(.*?)```)'
        code_block_match = re.search(code_block_pattern, response, re.DOTALL)

        if code_block_match:
            # 如果找到了Markdown代码块，就以此为准
            full_block = code_block_match.group(0)  # 获取完整的 ```...``` 块
            code = code_block_match.group(2).strip() # 获取内部的代码

            # 解释 = 原始响应 - 完整的代码块
            explanation = response.replace(full_block, "").strip()

            # (可选但推荐的优化) 如果解释部分只剩下空的<INFO>标签，则清空它
            if explanation == "<INFO></INFO>" or explanation == "<INFO>\n</INFO>":
                explanation = ""
            
            # 成功提取，直接返回结果，不再执行后面的旧逻辑
            return {
                "code": code,
                "explanation": explanation.strip(),
                "raw_response": response
            }


        #-------
        info_pattern = r'<INFO>(.*?)</INFO>'
        info_match = re.search(info_pattern, response, re.DOTALL)
        
        target_text = response
        if info_match:
            target_text = info_match.group(1).strip()
            explanation = response.replace(info_match.group(0), "").strip()

        # Try to extract code from markdown code blocks
        code_pattern = r'```(?:python|java|cpp|c\+\+|c|javascript|js|typescript|ts|go|rust|php|ruby|csharp|c#)?\s*(.*?)```'
        code_matches = re.findall(code_pattern, target_text, re.DOTALL)
        
        if code_matches:
            code = code_matches[0].strip()
            # Refine explanation by removing the code part from it
            if not info_match:
                explanation = response
                for match in re.findall(r'```(?:.|\n)*?```', response, re.DOTALL):
                    explanation = explanation.replace(match, "").strip()
        elif info_match:
            # If inside <INFO> but no markdown, the whole content is code
            code = target_text
        else:
            # Fallback for when there are no <INFO> tags and no markdown blocks
            lines = response.split('\n')
            code_lines = []
            in_code = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_code = not in_code
                    continue
                if in_code or not (line.startswith('#') or line.startswith('>')):
                    code_lines.append(line)
            code = '\n'.join(code_lines).strip()

        return {
            "code": code,
            "explanation": explanation.strip(),
            "raw_response": response
        }
    
    def generate_code(
        self,
        problem_description: str,
        test_cases: Dict[str, Any],
        technical_plan: Dict[str, Any],
        language: str = "Python3",
        problem_sample_io: str = None,
        attention_analysis: Dict[str, Any] = None,
        error_code: str = None,
        error_info: str = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate code based on problem description, test cases, and technical plan
        
        Args:
            problem_description: Problem description
            test_cases: Test cases
            technical_plan: Technical plan
            language: Programming language
            problem_sample_io: Sample input/output examples
            
        Returns:
            Generated code and explanation
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} is generating code...")
        
        # Start a new session for code generation
        session_id = self.start_new_session()
        
        messages = self._generate_prompt(
            problem_description=problem_description,
            test_cases=test_cases,
            technical_plan=technical_plan,
            language=language,
            problem_sample_io=problem_sample_io,
            attention_analysis=attention_analysis,
            error_code=error_code,
            error_info=error_info
        )
        
        # Call model with session_id to maintain conversation history
        response = self._call_model(messages, session_id=session_id)
        result = self._process_response(response)
        # sanitize code prefix
        try:
            from utils.code_sanitizer import sanitize_code_prefix
            if "code" in result and isinstance(result["code"], str):
                result["code"] = sanitize_code_prefix(result["code"]) 
        except Exception:
            pass
        
        # Store session_id in the result for future reference
        result["session_id"] = session_id
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} has generated code, length: {len(result.get('code', ''))}")
            if self.verbose >= VERBOSE_FULL:
                print("\nGenerated code:")
                print(result.get("code", ""))
        
        return result
    

    def generate_init_code(
        self,
        problem_description: str,
        language: str = "Python3",
        problem_sample_io: str = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate code based on problem description, test cases, and technical plan
        
        Args:
            problem_description: Problem description
            test_cases: Test cases
            technical_plan: Technical plan
            language: Programming language
            problem_sample_io: Sample input/output examples
            
        Returns:
            Generated code and explanation
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} is generating code...")
        
        # Start a new session for code generation
        session_id = self.start_new_session()
        
        messages = self._generate_init_prompt(
            problem_description=problem_description,
            test_cases=problem_sample_io,
            language=language,
        )
        
        # Call model with session_id to maintain conversation history
        response = self._call_model(messages, session_id=session_id)
        result = self._process_response(response)
        # sanitize code prefix
        try:
            from utils.code_sanitizer import sanitize_code_prefix
            if "code" in result and isinstance(result["code"], str):
                result["code"] = sanitize_code_prefix(result["code"]) 
        except Exception:
            pass
        
        # Store session_id in the result for future reference
        result["session_id"] = session_id
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} has generated code, length: {len(result.get('code', ''))}")
            if self.verbose >= VERBOSE_FULL:
                print("\nGenerated code:")
                print(result.get("code", ""))
        
        return result
    
    def fix_code(
        self,
        code: str,
        debug_feedback: Dict[str, Any],
        problem_description: str = "",
        language: str = "Python3",
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Fix code based on debug feedback
        
        Args:
            code: Original code with errors
            debug_feedback: Debug feedback containing error information
            problem_description: Problem description for context
            language: Programming language
            session_id: Session ID for continuing conversation
            
        Returns:
            Fixed code and explanation
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} is fixing code...")
        
        # Use provided session_id or create a new one
        if session_id is None:
            session_id = self.start_new_session()
        else:
            self.set_active_session(session_id)
        
        # Get fix messages
        fix_prompt = self.prompt_module.get_fix_code_prompt(
            code=code,
            debug_feedback=debug_feedback,
            problem_description=problem_description,
            language=language
        )
        
        # Create a simple message with just the fix prompt
        messages = [{"role": "user", "content": fix_prompt}]
        
        # Call model with session_id and include_history=True to use conversation history
        response = self._call_model(messages, session_id=session_id, include_history=True)
        result = self._process_response(response)
        # sanitize code prefix
        try:
            from utils.code_sanitizer import sanitize_code_prefix
            if "code" in result and isinstance(result["code"], str):
                result["code"] = sanitize_code_prefix(result["code"]) 
        except Exception:
            pass
        
        # Store session_id in the result for future reference
        result["session_id"] = session_id
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} has fixed code, length: {len(result.get('code', ''))}")
            if self.verbose >= VERBOSE_FULL:
                print("\nFixed code:")
                print(result.get("code", ""))
        
        return result