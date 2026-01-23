from typing import Dict, Any, List, Optional
import subprocess
import tempfile
import os
import sys
import traceback

from ..BaseAgent import BaseAgent
from constants.verboseType import *
from evaluations.func_evaluate import evaluate_io

class DebugAgent(BaseAgent):
    """
    Debug Agent, responsible for executing code and providing error information
    """
    
    def __init__(
        self,
        agent_name: str = "Debug Agent",
        verbose: int = VERBOSE_MINIMAL,
    ):
        """
        Initialize the Debug Agent
        
        Args:
            agent_name: Agent name
            verbose: Verbosity level
        """
        # Debug agent doesn't need a model, it just executes code
        super().__init__(
            model=None,
            agent_name=agent_name,
            verbose=verbose
        )
    
    def _call_model(self, messages, session_id=None, include_history=True):
        """
        Override _call_model as Debug Agent doesn't use a model
        """
        return "Debug Agent doesn't use a model"
    
    def execute_code(self, code: str, language: str = "Python3", timeout: int = 10) -> Dict[str, Any]:
        """
        Execute the given code and return the result or error
        
        Args:
            code: Code to execute
            language: Programming language
            timeout: Execution timeout in seconds
            
        Returns:
            Dictionary containing execution result or error
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} is executing code...")
        
        result = {
            "success": False,
            "output": "",
            "error": "",
            "error_type": None
        }
        
        # Currently only support Python
        if language.lower() not in ["python", "python3"]:
            result["error"] = f"Language {language} is not supported yet"
            result["error_type"] = "UnsupportedLanguage"
            return result
        
        # Create a temporary file to store the code
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_filename = temp_file.name
            temp_file.write(code.encode('utf-8'))
        
        try:
            # Execute the code
            process = subprocess.Popen(
                [sys.executable, temp_filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                
                result["output"] = stdout
                if stderr:
                    result["error"] = stderr
                    result["error_type"] = "RuntimeError"
                else:
                    result["success"] = True
                    
            except subprocess.TimeoutExpired:
                process.kill()
                result["error"] = f"Execution timed out after {timeout} seconds"
                result["error_type"] = "TimeoutError"
                
        except Exception as e:
            result["error"] = str(e) + "\n" + traceback.format_exc()
            result["error_type"] = type(e).__name__
            
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_filename)
            except:
                pass
        
        if self.verbose >= VERBOSE_MINIMAL:
            if result["success"]:
                print(f"\n{self.agent_name}: Code executed successfully")
            else:
                print(f"\n{self.agent_name}: Code execution failed")
                print(f"Error: {result['error']}")
        
        return result
    
    def test_with_sample_io(self, code: str, sample_io: List[str], timeout: int = 10) -> Dict[str, Any]:
        """
        Test the code with sample input/output assertions
        
        Args:
            code: Code to test
            sample_io: List of sample I/O assertions
            timeout: Execution timeout in seconds
            
        Returns:
            Dictionary containing test results
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} is testing code with sample I/O...")
        
        if not sample_io:
            return {
                "success": True,
                "output": "No sample I/O tests provided.",
                "error": "",
                "error_type": None,
                "failed_tests": []
            }
        
        # 过滤无效的测试断言
        valid_assertions = []
        for assertion in sample_io:
            # 确保它是一个字符串
            if not isinstance(assertion, str):
                continue
                
            # 跳过可能是task_id的断言
            if "/" in assertion and not assertion.startswith("assert"):
                continue
                
            # 确保它是一个断言语句
            if assertion.strip().startswith("assert"):
                valid_assertions.append(assertion)
        
        if not valid_assertions:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{self.agent_name}: No valid assertions found in sample I/O")
            return {
                "success": True,
                "output": "No valid assertions found in sample I/O.",
                "error": "",
                "error_type": None,
                "failed_tests": []
            }
        
        all_passed = True
        test_log = ""
        failed_tests = []
        
        # Test each sample I/O assertion
        for i, assertion in enumerate(valid_assertions):
            try:
                # Add typing import if needed
                code_to_test = \
                    code + "\n" + assertion + "\n"
                
                # Execute the code with the assertion
                with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                    temp_filename = temp_file.name
                    temp_file.write(code_to_test.encode('utf-8'))
                
                try:
                    process = subprocess.Popen(
                        [sys.executable, temp_filename],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    stdout, stderr = process.communicate(timeout=timeout)
                    
                    if stderr:
                        all_passed = False
                        # Rerun by replacing 'assert ... == ...' with a print of actual value
                        import re
                        def to_print_block(assert_line: str, idx: int) -> str:
                            m = re.match(r"\s*assert\s+(.+?)\s*==\s*(.+?)\s*$", assert_line)
                            if m:
                                lhs, rhs = m.group(1), m.group(2)
                                return (
                                    f"try:\n"
                                    f"    __tc_actual_{idx} = ({lhs})\n"
                                    f"    __tc_expected_{idx} = ({rhs})\n"
                                    f"    if __tc_actual_{idx} == __tc_expected_{idx}:\n"
                                    f"        pass\n"
                                    f"    else:\n"
                                    f"        print(\"assert {lhs} == {rhs} is not get, current output is\", repr(__tc_actual_{idx}))\n"
                                    f"except Exception as e:\n"
                                    f'    print("assert {lhs} == {rhs} raised", type(e).__name__, ":", str(e))\n'
                                )
                            # Fallback for non '==' asserts
                            expr = assert_line.strip()[len("assert "):].strip() if assert_line.strip().startswith("assert") else assert_line.strip()
                            return (
                                f"try:\n"
                                f"    assert {expr}\n"
                                f"    print(\"assert {expr} passed\")\n"
                                f"except AssertionError:\n"
                                f"    print(\"assert {expr} is not get\")\n"
                                f"except Exception as e:\n"
                                f'    print("assert {expr} raised", type(e).__name__, ":", str(e))\n'
                            )

                        enhanced_block = to_print_block(assertion, i + 1)
                        code_enhanced =  code + "\n" + enhanced_block + "\n"
                        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file2:
                            temp_filename2 = temp_file2.name
                            temp_file2.write(code_enhanced.encode('utf-8'))
                        try:
                            p2 = subprocess.Popen(
                                [sys.executable, temp_filename2],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            out2, err2 = p2.communicate(timeout=timeout)
                        except subprocess.TimeoutExpired:
                            p2.kill()
                            out2, err2 = "", "Execution timed out"
                        finally:
                            try:
                                os.unlink(temp_filename2)
                            except:
                                pass
                        # Prefer the enhanced stdout as error detail
                        enhanced_msg = out2.strip() if out2.strip() else stderr
                        error_msg = f"Test {i+1} failed: {assertion}\nError: {enhanced_msg}"
                        test_log += error_msg + "\n"
                        failed_tests.append({
                            "test": assertion,
                            "error": enhanced_msg
                        })
                    else:
                        test_log += f"Test {i+1} passed: {assertion}\n"
                        
                except subprocess.TimeoutExpired:
                    process.kill()
                    all_passed = False
                    error_msg = f"Test {i+1} timed out: {assertion}"
                    test_log += error_msg + "\n"
                    failed_tests.append({
                        "test": assertion,
                        "error": "Execution timed out"
                    })
                    
                finally:
                    try:
                        os.unlink(temp_filename)
                    except:
                        pass
                        
            except Exception as e:
                all_passed = False
                error_msg = f"Test {i+1} failed: {assertion}\nError: {str(e)}"
                test_log += error_msg + "\n"
                failed_tests.append({
                    "test": assertion,
                    "error": str(e)
                })
        
        result = {
            "success": all_passed,
            "output": test_log,
            "error": "" if all_passed else test_log,
            "error_type": None if all_passed else "AssertionError",
            "failed_tests": failed_tests
        }
        
        if self.verbose >= VERBOSE_MINIMAL:
            if result["success"]:
                print(f"\n{self.agent_name}: Code passed all sample I/O tests")
            else:
                print(f"\n{self.agent_name}: Code failed {len(failed_tests)} sample I/O tests")
                print(f"Test log: {test_log}")
        
        return result
    
    def debug_code(self, code: str, problem_description: str = "", language: str = "Python3", sample_io: List[str] = None) -> Dict[str, Any]:
        """
        Debug the given code and provide feedback
        
        Args:
            code: Code to debug
            problem_description: Problem description for context
            language: Programming language
            sample_io: Sample input/output assertions
            
        Returns:
            Dictionary containing debug result
        """
        # First, check if the code has syntax errors by executing it
        execution_result = self.execute_code(code, language)
        
        # If code has syntax errors, return the execution result
        if not execution_result["success"]:
            return self._prepare_debug_feedback(execution_result)
        
        # If sample_io is provided, test the code with it
        if sample_io:
            sample_io_result = self.test_with_sample_io(code, sample_io)
            
            # If sample I/O tests fail, return the sample I/O result
            if not sample_io_result["success"]:
                return self._prepare_debug_feedback(sample_io_result)
        
        # If everything passes, return success
        return {
            "success": True,
            "output": execution_result.get("output", ""),
            "error": "",
            "error_type": None,
            "feedback": "The code executed successfully and passed all sample I/O tests."
        }
    
    def _prepare_debug_feedback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare debug feedback based on execution or test result
        
        Args:
            result: Execution or test result
            
        Returns:
            Dictionary containing debug feedback
        """
        debug_feedback = {
            "success": result["success"],
            "output": result.get("output", ""),
            "error": result.get("error", ""),
            "error_type": result.get("error_type", None),
            "feedback": ""
        }
        
        # Generate feedback based on result
        if result["success"]:
            debug_feedback["feedback"] = "The code executed successfully without errors."
        else:
            error_type = result.get("error_type")
            error_message = result.get("error", "")
            
            if error_type == "SyntaxError":
                debug_feedback["feedback"] = f"Syntax Error: {error_message}\nPlease check your code syntax."
            elif error_type == "TimeoutError":
                debug_feedback["feedback"] = "The code execution timed out. This might be due to an infinite loop or inefficient algorithm."
            elif error_type == "UnsupportedLanguage":
                debug_feedback["feedback"] = error_message
            elif error_type == "AssertionError":
                debug_feedback["feedback"] = f"Assertion Error: The code failed to pass sample I/O tests.\n{error_message}"
            else:
                debug_feedback["feedback"] = f"Runtime Error ({error_type}): {error_message}\nPlease fix the error and try again."
        
        return debug_feedback 

    def run_generated_tests(self, code: str, test_cases: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        """
        Run generated test cases as print statements instead of assertions
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} is running generated test cases...")
        
        # Extract test cases from different possible structures
        structured_tests = []
        
        # Check if test_cases has CTO's structured format
        if isinstance(test_cases, dict) and test_cases.get("structured_data") and "test_cases" in test_cases["structured_data"]:
            # CTO's summarized test cases format
            for test in test_cases["structured_data"]["test_cases"]:
                if "assertion" in test and test["assertion"]:
                    structured_tests.append({
                        "code": test["assertion"],
                        "description": test.get("description", "")
                    })
                elif "code" in test and test["code"]:
                    structured_tests.append(test)
        
        # Check for individual testing agent formats
        elif isinstance(test_cases, dict) and "test_cases" in test_cases:
            # Direct test_cases array
            for test in test_cases["test_cases"]:
                if isinstance(test, str):
                    structured_tests.append({"code": test})
                elif isinstance(test, dict):
                    if "assertion" in test and test["assertion"]:
                        structured_tests.append({
                            "code": test["assertion"],
                            "description": test.get("description", "")
                        })
                    elif "code" in test:
                        structured_tests.append(test)
        
        # Check for raw test cases array
        elif isinstance(test_cases, list):
            for test in test_cases:
                if isinstance(test, str):
                    structured_tests.append({"code": test})
                elif isinstance(test, dict) and "code" in test:
                    structured_tests.append(test)
                elif isinstance(test, dict) and "test_cases" in test:
                    # Handle nested test_cases
                    for nested_test in test["test_cases"]:
                        if isinstance(nested_test, str):
                            structured_tests.append({"code": nested_test})
                        elif isinstance(nested_test, dict):
                            if "assertion" in nested_test and nested_test["assertion"]:
                                structured_tests.append({
                                    "code": nested_test["assertion"],
                                    "description": nested_test.get("description", "")
                                })
                            elif "code" in nested_test:
                                structured_tests.append(nested_test)
        
        if not structured_tests:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{self.agent_name}: No valid test cases found in the provided structure.")
                print(f"Test cases structure: {type(test_cases)}")
                if isinstance(test_cases, dict):
                    print(f"Keys: {list(test_cases.keys())}")
            
            return {
                "success": True,
                "output": "No structured test cases available.",
                "error": "",
                "error_type": None,
                "failed_tests": []
            }
        
        # Convert assertions to print statements
        print_statements = []
        for test in structured_tests:
            if "code" in test:
                assertion_code = test["code"]
                description = test.get("description", "")
                
                if isinstance(assertion_code, str) and assertion_code.strip().startswith("assert"):
                    expression = assertion_code.strip()[6:].strip()
                    if expression.endswith(", "):
                        expression = expression[:-2]
                    test_desc = f" ({description})" if description else ""
                    print_statement = f'print("Test{test_desc}: {expression} =", {expression})'
                    print_statements.append(print_statement)
        
        if not print_statements:
            return {
                "success": True,
                "output": "No valid test assertions found in generated test cases.",
                "error": "",
                "error_type": None,
                "failed_tests": []
            }
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\nFound {len(print_statements)} test assertions to run as print statements:")
            for i, statement in enumerate(print_statements):
                print(f"  Print {i+1}: {statement}")
        
        # Combine code with print statements
        code_with_tests = code + "\n\n# Generated Test Cases\nprint('\\n=== Running Generated Test Cases ===')\n" + "\n".join(print_statements)
        
        # Execute the code with print statements
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_filename = temp_file.name
            temp_file.write(code_with_tests.encode('utf-8'))
        
        try:
            process = subprocess.Popen(
                [sys.executable, temp_filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            
            result = {
                "success": not stderr,
                "output": stdout,
                "error": stderr,
                "error_type": "RuntimeError" if stderr else None,
                "test_results": stdout
            }
        except subprocess.TimeoutExpired:
            process.kill()
            result = {
                "success": False,
                "output": "",
                "error": f"Execution timed out after {timeout} seconds",
                "error_type": "TimeoutError",
                "test_results": ""
            }
        except Exception as e:
            result = {
                "success": False,
                "output": "",
                "error": str(e) + "\n" + traceback.format_exc(),
                "error_type": type(e).__name__,
                "test_results": ""
            }
        finally:
            try:
                os.unlink(temp_filename)
            except:
                pass
        
        if self.verbose >= VERBOSE_MINIMAL:
            if result["success"]:
                print(f"\n{self.agent_name}: Generated tests executed successfully")
                print("Test results:")
                print(result["output"])
            else:
                print(f"\n{self.agent_name}: Error executing generated tests")
                print(f"Error: {result['error']}")
        
        return result 