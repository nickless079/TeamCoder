from typing import Dict, Any, List
import json
import re

from ..BaseAgent import BaseAgent
from models.Base import BaseModel
from constants.verboseType import *

class TestAgent(BaseAgent):
    """
    Comprehensive Test Agent, responsible for generating high-quality test cases
    using various testing methodologies including equivalence class partitioning
    and boundary value analysis.
    """
    def __init__(
        self,
        model: BaseModel,
        verbose: int = 1,
        enabled: bool = True,
    ):
        """
        Initialize the Test Agent
        
        Args:
            model: Model instance
            verbose: Verbosity level
            enabled: Whether this agent is enabled
        """
        super().__init__(
            model=model,
            verbose=verbose,
            enabled=enabled,
            agent_name="TestAgent",
            prompt_module_path="testing.test_agent"
        )

    def _generate_prompt(self, task_name: str, problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None, sample_io: List[str] = None, attention_analysis: Dict[str, Any] = None, assertion: str = "") -> List[Dict[str, str]]:
        """
        Generate test case prompt
        """


        return self.prompt_module.get_messages(task_name, problem_description, language, function_signature, function_name, sample_io, attention_analysis, assertion)
    
    def _fix_json_syntax(self, json_str: str) -> str:
        """
        修复常见的JSON语法错误
        """
        import re
        
        # 修复缺少引号的情况，如 == [], -> == []",
        json_str = re.sub(r'== \[\],\s*"', r'== []", "', json_str)
        
        # 修复其他常见的末尾逗号问题
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # 修复双引号不匹配的问题
        # 寻找 "assertion": "...== [], "description" 这种模式
        json_str = re.sub(r'"assertion":\s*"([^"]*== \[\]),\s*"description"', r'"assertion": "\1", "description"', json_str)
        
        return json_str
    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        Process model response, extract both thought and test cases in minimal format
        Expected two-part output from prompt: <thought>...</thought> and a JSON array/object
        """
        print("\noriginal response",response,"\n\n")

            # Priority 1: The "perfect" match. A complete, closed tag.
        # This regex is robust against spaces inside the tags.
        propose_double_match = re.search(r'<\s*PROPOSED_INPUT\s*>(.*?)<\/\s*PROPOSED_INPUT\s*>', response, re.DOTALL | re.IGNORECASE)
        if propose_double_match:
            return {
                "type": "proposed_input",
                "input": propose_double_match.group(1).strip(),
                "raw_response": response
            }
    
        # Priority 2: Fallback for a missing closing tag.
        # Matches from the opening tag to the end of the string.
        propose_single_open_match = re.search(r'<\s*PROPOSED_INPUT\s*>(.*)', response, re.DOTALL | re.IGNORECASE)
        if propose_single_open_match:
            return {
                "type": "proposed_input",
                "input": propose_single_open_match.group(1).strip(),
                "raw_response": response
            }
    
        # Priority 3: Fallback for a missing opening tag (less common, but robust).
        # This is a bit ambiguous, so we only match if it's at the start of the string.
        propose_single_close_match = re.search(r'^(.*?)<\/\s*PROPOSED_INPUT\s*>', response, re.DOTALL | re.IGNORECASE)
        if propose_single_close_match:
            return {
                "type": "proposed_input",
                "input": propose_single_close_match.group(1).strip(),
                "raw_response": response
            }
    
        # --- SolverAgent (`<SOLVED_EXAMPLE>`) Parser ---
    
        # Priority 1: The "perfect" match.
        solved_double_match = re.search(r'<\s*SOLVED_EXAMPLE\s*>(.*?)<\/\s*SOLVED_EXAMPLE\s*>', response, re.DOTALL | re.IGNORECASE)
        if solved_double_match:
            return {
                "type": "solved_example",
                "assertion": solved_double_match.group(1).strip(),
                "raw_response": response
            }
    
        # Priority 2: Fallback for a missing closing tag.
        solved_single_open_match = re.search(r'<\s*SOLVED_EXAMPLE\s*>(.*)', response, re.DOTALL | re.IGNORECASE)
        if solved_single_open_match:
            return {
                "type": "solved_example",
                "assertion": solved_single_open_match.group(1).strip(),
                "raw_response": response
            }
        
        # Priority 3: Fallback for a missing opening tag.
        # Only match if it's at the start of the string.
        solved_single_close_match = re.search(r'^(.*?)<\/\s*SOLVED_EXAMPLE\s*>', response, re.DOTALL | re.IGNORECASE)
        if solved_single_close_match:
            return {
                "type": "solved_example",
                "assertion": solved_single_close_match.group(1).strip(),
                "raw_response": response
            }

        return {
            "type": "unknown",
            "content": response
        }
        
    def generate_test_cases(self, problem_description: str, language: str = "Python", function_signature: str = None, function_name: str = None, sample_io: List[str] = None, session_id: str = None) -> Dict[str, Any]:
        if not function_signature or not function_name:
            func_info = self.extract_function_info(problem_description, language)
            function_name = function_name or func_info.get("function_name")
            function_signature = function_signature or func_info.get("function_signature")
        result = self.execute(
            task_name="generate_comprehensive_tests",
            session_id=session_id,
            problem_description=problem_description,
            language=language,
            function_signature=function_signature,
            function_name=function_name,
            sample_io=sample_io,
        )
        return result["result"]

    def evaluate_single_test(self, problem_description: str, assertion: str, sample_io: List[str] = [], language: str = "Python", attention_analysis: Dict[str, any] = None) -> Dict[str, Any]:

        result = self.execute(
            task_name="evaluate_single_test",
            session_id=None,
            problem_description=problem_description,
            language=language,
            sample_io=sample_io,
            assertion=assertion,
            attention_analysis=attention_analysis
        )
        return result["result"]
    
    def extract_function_info(self, problem_description: str, language: str = "Python") -> Dict[str, str]:
        if language.lower() == "python":
            function_match = re.search(r'def\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', problem_description)
        elif language.lower() in ["javascript", "typescript"]:
            function_match = re.search(r'function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', problem_description)
        elif language.lower() == "java":
            function_match = re.search(r'(?:public|private|protected)?\s+\w+\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', problem_description)
        else:
            function_match = re.search(r'(?:function|def|func)\s+([a-zA-Z0-9_]+)\s*\((.*?)\)', problem_description)
        if function_match:
            function_name = function_match.group(1)
            params = function_match.group(2)
            if language.lower() == "python":
                signature = f"def {function_name}({params})"
            elif language.lower() in ["javascript", "typescript"]:
                signature = f"function {function_name}({params})"
            elif language.lower() == "java":
                signature = f"public returnType {function_name}({params})"
            else:
                signature = f"{function_name}({params})"
            return {"function_name": function_name, "function_signature": signature}
        return {"function_name": None, "function_signature": None} 