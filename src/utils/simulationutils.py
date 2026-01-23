"""
代码模拟执行工具
使用 snoop 包进行真实的代码执行追踪，替代 SimulationAgent

这个模块提供了以下功能：
1. 使用 snoop 包对 Python 代码进行真实的执行追踪
2. 生成标准化的模拟报告，与原有的 SimulationAgent 输出格式兼容
3. 解析 assert 语句，提取测试用例
4. 支持错误处理和异常情况

主要类：
- CodeSimulator: 核心的代码执行和追踪器
- TestCaseParser: 解析测试用例

主要函数：
- simulate_code_execution: 一站式模拟函数
"""

try:
    import pysnooper
except ImportError:
    # 如果 pysnooper 没有安装，提供一个简单的替代方案
    import io
    import sys
    
    class SimpleTracer:
        def __init__(self, output):
            self.output = output
            
        def __call__(self, func):
            def wrapper(*args, **kwargs):
                self.output.write(f"Calling {func.__name__} with args={args}, kwargs={kwargs}\n")
                result = func(*args, **kwargs)
                self.output.write(f"{func.__name__} returned: {result}\n")
                return result
            return wrapper
    
    class MockPySnoop:
        def __call__(self, output=None):
            return SimpleTracer(output or sys.stdout)
    
    pysnooper = MockPySnoop()
    print("Warning: pysnooper package not found, using simple tracer")

import io
import sys
import traceback
import contextlib
import re
from typing import Dict, Any, Optional, Tuple, List
import tempfile
import os


class CodeSimulator:
    """代码模拟执行器"""
    
    def __init__(self):
        self.trace_output = io.StringIO()
        self.execution_output = io.StringIO() 
        self.error_output = io.StringIO()
    
    def simulate_code_execution(self, code: str, test_input: Any = None, 
                               function_name: str = None, function_call_code: str = None) -> Dict[str, Any]:
        """
        模拟代码执行
        
        Args:
            code: 要执行的代码
            test_input: 测试输入
            function_name: 要调用的函数名
            
        Returns:
            包含执行结果的字典
        """
        # 重置输出缓冲区
        self.trace_output = io.StringIO()
        self.execution_output = io.StringIO() 
        self.error_output = io.StringIO()
        
        try:
            # 准备执行环境 - 使用同一个字典作为 globals 和 locals
            execution_namespace = {'__builtins__': __builtins__}
            
            # 解析代码，寻找函数定义
            functions_to_trace = self._extract_functions_from_code(code)
            
            # 如果代码中有函数定义，给它们添加 pysnooper 装饰器
            instrumented_code = self._instrument_code_with_pysnooper(code, functions_to_trace)
            
            # 创建一个专门的 simulation-log.py 文件来存储代码，这样可以显示源码
            # 统一写在项目根目录的 results 文件夹下
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            results_dir = os.path.join(project_root, 'results')
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
            simulation_file_path = os.path.join(results_dir, 'simulation-log.py')
            
            try:
                # 写入代码到 simulation-log.py 文件
                with open(simulation_file_path, 'w', encoding='utf-8') as f:
                    f.write(instrumented_code)
                
                # 强制刷新文件系统缓存并等待文件同步
                self._ensure_file_sync(simulation_file_path, instrumented_code)
                
                # 执行代码并捕获所有输出
                with contextlib.redirect_stdout(self.execution_output), \
                     contextlib.redirect_stderr(self.trace_output):
                    
                    # 从 simulation-log.py 文件执行代码，这样 pysnooper 就能显示完整源码
                    with open(simulation_file_path, 'r', encoding='utf-8') as f:
                        exec(compile(f.read(), simulation_file_path, 'exec'), execution_namespace, execution_namespace)
            except Exception as file_error:
                # 如果文件操作失败，回退到临时文件方案
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(instrumented_code)
                    temp_file_path = temp_file.name
                
                # 确保临时文件也完全同步
                self._ensure_file_sync(temp_file_path, instrumented_code)
                
                try:
                    with contextlib.redirect_stdout(self.execution_output), \
                         contextlib.redirect_stderr(self.trace_output):
                        with open(temp_file_path, 'r', encoding='utf-8') as f:
                            exec(compile(f.read(), temp_file_path, 'exec'), execution_namespace, execution_namespace)
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                
            # 如果指定了函数名和测试输入，调用函数
            if function_name and function_name in execution_namespace:
                if function_call_code:
                    # 如果有完整的函数调用代码，直接执行
                    result = eval(function_call_code, execution_namespace, execution_namespace)
                elif test_input is not None and test_input != "EXECUTE_FUNCTION_CALL":
                    if isinstance(test_input, (list, tuple)) and len(test_input) > 0:
                        # 如果 test_input 是参数列表，使用 * 解包
                        result = execution_namespace[function_name](*test_input)
                    else:
                        # 如果 test_input 是单个值，直接传递
                        result = execution_namespace[function_name](test_input)
                else:
                    # 如果没有输入，尝试调用无参数函数
                    result = execution_namespace[function_name]()
            else:
                # 如果没有指定函数，直接获取执行结果
                result = execution_namespace.get('result', execution_namespace)
            
            # 获取追踪信息
            trace_content = self.trace_output.getvalue()
            execution_content = self.execution_output.getvalue()
            error_content = self.error_output.getvalue()
            
            return {
                "success": True,
                "trace": trace_content,
                "output": execution_content,
                "error": error_content,
                "result": result,
                "globals": {k: v for k, v in execution_namespace.items() if not k.startswith('__')},
                "locals": {k: v for k, v in execution_namespace.items() if not k.startswith('__')}
            }
            
        except Exception as e:
            error_trace = traceback.format_exc()
            return {
                "success": False,
                "trace": self.trace_output.getvalue(),
                "output": self.execution_output.getvalue(),
                "error": str(e),
                "error_trace": error_trace,
                "result": None,
                "globals": {},
                "locals": {}
            }
    
    def _extract_functions_from_code(self, code: str) -> List[str]:
        """从代码中提取函数名"""
        function_pattern = r'def\s+(\w+)\s*\('
        functions = re.findall(function_pattern, code)
        return functions
    
    def _instrument_code_with_pysnooper(self, code: str, functions_to_trace: List[str]) -> str:
        """
        给代码中的函数添加 pysnooper 装饰器
        
        智能装饰策略：
        1. 如果有函数调用的上下文（function_name），优先装饰该函数
        2. 如果没有明确的调用目标，装饰所有顶层函数
        3. 避免装饰嵌套函数（可能导致作用域问题）
        """
        if not functions_to_trace:
            return code
        
        lines = code.split('\n')
        instrumented_lines = []
        
        # 添加必要的导入
        instrumented_lines.append("import pysnooper")
        instrumented_lines.append("import sys")
        instrumented_lines.append("")
        
        # 分析代码结构：识别顶层函数和嵌套函数
        function_info = self._analyze_function_structure(code)
        
        # 确定装饰策略
        target_functions = self._determine_decoration_targets(function_info, functions_to_trace)
        
        # 处理每一行
        for line in lines:
            # 计算当前行的缩进级别
            current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
            
            # 检查是否是函数定义
            if line.strip().startswith('def '):
                # 提取函数名
                match = re.match(r'\s*def\s+(\w+)\s*\(', line)
                if match:
                    func_name = match.group(1)
                    # 只对目标函数且为顶层函数添加装饰器
                    if func_name in target_functions and current_indent == 0:
                        decorator = '@pysnooper.snoop(output=sys.stderr, prefix="TRACE: ")'
                        instrumented_lines.append(decorator)
            
            instrumented_lines.append(line)
        
        return '\n'.join(instrumented_lines)
    
    def _analyze_function_structure(self, code: str) -> Dict[str, Dict]:
        """分析代码中的函数结构"""
        lines = code.split('\n')
        functions = {}
        current_function = None
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                match = re.match(r'(\s*)def\s+(\w+)\s*\(', line)
                if match:
                    indent = len(match.group(1))
                    func_name = match.group(2)
                    
                    functions[func_name] = {
                        'line_number': i + 1,
                        'indent_level': indent,
                        'is_top_level': indent == 0,
                        'is_nested': indent > 0
                    }
        
        return functions
    
    def _determine_decoration_targets(self, function_info: Dict, functions_to_trace: List[str]) -> List[str]:
        """
        确定应该装饰哪些函数
        
        策略优先级：
        1. 如果存在明确的调用目标且为顶层函数，只装饰该函数
        2. 如果所有函数都是顶层函数，装饰所有函数
        3. 如果混合了顶层和嵌套函数，只装饰顶层函数
        4. 特殊情况：如果只有一个顶层函数，装饰它
        """
        # 获取顶层函数
        top_level_functions = [name for name, info in function_info.items() 
                             if info['is_top_level'] and name in functions_to_trace]
        
        # 如果只有一个顶层函数，装饰它
        if len(top_level_functions) == 1:
            return top_level_functions
        
        # 如果有多个顶层函数，优先装饰主要的函数
        # 通常主要函数名会出现在文档字符串或示例中
        main_candidates = []
        for func_name in top_level_functions:
            # 检查函数名是否在其他函数的文档字符串中被调用
            if self._is_main_function(func_name, function_info.keys()):
                main_candidates.append(func_name)
        
        if main_candidates:
            return main_candidates
        
        # 默认：装饰所有顶层函数
        return top_level_functions
    
    def _is_main_function(self, func_name: str, all_functions: List[str]) -> bool:
        """判断是否为主要函数（通常是被调用的函数）"""
        # 简单策略：函数名较长的通常是主要函数
        # 或者函数名包含问题关键词的
        main_keywords = ['make', 'find', 'get', 'calculate', 'solve', 'process']
        
        if any(keyword in func_name.lower() for keyword in main_keywords):
            return True
        
        # 如果函数名比其他函数长，可能是主要函数
        avg_length = sum(len(name) for name in all_functions) / len(all_functions)
        return len(func_name) > avg_length
        
        return False
    
    def format_simulation_report(self, simulation_result: Dict[str, Any], expected_output: Any = None) -> str:
        """
        格式化模拟结果为标准的模拟报告格式
        
        Args:
            simulation_result: simulate_code_execution 的返回结果
            expected_output: 期望的输出结果
            
        Returns:
            格式化的模拟报告字符串
        """
        if not simulation_result["success"]:
            # 执行失败的情况
            return f"""<SIMULATION_REPORT>
    <TRACE>
    Execution failed with error: {simulation_result["error"]}
    
    Error details:
    {simulation_result.get("error_trace", "")}
    
    Partial trace (if any):
    {simulation_result.get("trace", "No trace available")}
    </TRACE>
    <FINAL_OUTPUT>
    EXECUTION_ERROR
    </FINAL_OUTPUT>
    <COMPARISON>
    Cannot compare due to execution error.
    Expected: {expected_output}
    Actual: EXECUTION_ERROR
    </COMPARISON>
    <CONCLUSION>
    FAILED
    </CONCLUSION>
</SIMULATION_REPORT>"""
        
        # 执行成功的情况
        trace = simulation_result.get("trace", "No detailed trace available")
        result = simulation_result.get("result", "No result")
        output = simulation_result.get("output", "")
        
        # 格式化追踪信息
        if trace and trace != "No detailed trace available":
            formatted_trace = self._format_trace_content(trace)
        else:
            formatted_trace = "No detailed execution trace available"
        
        # 比较结果
        if expected_output is not None:
            if result == expected_output:
                comparison = f"✅ MATCH\nExpected: {expected_output}\nActual: {result}"
                conclusion = "PASSED"
            else:
                comparison = f"❌ MISMATCH\nExpected: {expected_output}\nActual: {result}"
                conclusion = "FAILED"
        else:
            comparison = f"No expected output provided for comparison.\nActual result: {result}"
            conclusion = "UNKNOWN"
        
        return f"""<SIMULATION_REPORT>
    <TRACE>
    {formatted_trace}
    
    Program output (if any):
    {output if output else "No program output"}
    </TRACE>
    <FINAL_OUTPUT>
    {result}
    </FINAL_OUTPUT>
    <COMPARISON>
    {comparison}
    </COMPARISON>
    <CONCLUSION>
    {conclusion}
    </CONCLUSION>
</SIMULATION_REPORT>"""
    
    def _format_trace_content(self, trace: str) -> str:
        """格式化追踪内容，使其更易读"""
        if not trace:
            return "No trace content"
        
        lines = trace.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # 移除 pysnooper 的前缀和时间戳，但保留代码内容
                cleaned_line = re.sub(r'^TRACE:\s*', '', line)  # 移除 TRACE: 前缀
                cleaned_line = re.sub(r'^\d+:\d+:\d+\.\d+\s*', '', cleaned_line)  # 移除时间戳
                
                # 保留所有重要信息，包括源码行
                if cleaned_line and not cleaned_line.startswith('Source path'):
                    formatted_lines.append(cleaned_line)
        
        return '\n'.join(formatted_lines)
    
    def _ensure_file_sync(self, file_path: str, expected_content: str, max_retries: int = 5, 
                          wait_interval: float = 0.1) -> None:
        """
        确保文件已完全写入并同步到磁盘
        
        Args:
            file_path: 文件路径
            expected_content: 预期的文件内容
            max_retries: 最大重试次数
            wait_interval: 每次重试的等待间隔（秒）
        """
        import time
        import os
        
        for attempt in range(max_retries):
            try:
                # 强制刷新操作系统缓存
                if hasattr(os, 'fsync'):
                    # Unix/Linux 系统
                    with open(file_path, 'r+', encoding='utf-8') as f:
                        os.fsync(f.fileno())
                elif hasattr(os, 'sync'):
                    # 某些 Unix 系统
                    os.sync()
                
                # 验证文件内容是否完整
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        actual_content = f.read()
                    
                    # 检查内容是否匹配且行数正确
                    expected_lines = expected_content.strip().split('\n')
                    actual_lines = actual_content.strip().split('\n')
                    
                    if (len(actual_lines) == len(expected_lines) and 
                        actual_content.strip() == expected_content.strip()):
                        # 文件内容完整，同步成功
                        return
                
                # 如果验证失败，等待后重试
                time.sleep(wait_interval)
                
            except (IOError, OSError) as e:
                if attempt == max_retries - 1:
                    # 最后一次重试失败，记录错误但不抛出异常
                    print(f"Warning: File sync failed after {max_retries} attempts: {e}")
                    return
                time.sleep(wait_interval)
        
        # 如果所有重试都失败，增加一个额外的等待
        time.sleep(wait_interval * 2)



def simulate_code_execution(code: str, test_input: Any = None, 
                           function_name: str = None, expected_output: Any = None,
                           assert_statement: str = None) -> str:
    """
    一站式函数：执行代码并生成模拟报告
    
    Args:
        code: 要执行的 Python 代码
        test_input: 测试输入
        function_name: 要调用的函数名
        expected_output: 期望的输出结果
        assert_statement: assert 语句（可选），如果提供则会自动解析参数
        
    Returns:
        格式化的模拟报告字符串
    """
    # 如果提供了 assert 语句，优先从中解析测试用例
    if assert_statement:
        parsed_test = TestCaseParser.parse_assert_statement(assert_statement)
        if parsed_test["function_name"]:
            function_name = parsed_test["function_name"]
            function_call_code = parsed_test["function_call_code"]
            expected_output = parsed_test["expected_output"]
            # 对于 assert 语句，我们使用动态执行的方式
            test_input = "EXECUTE_FUNCTION_CALL"
        elif test_input is None:
            # 如果没有从 assert 中解析到函数，但有其他参数，保持原有逻辑
            pass
    
    if not code:
        return f"""<SIMULATION_REPORT>
    <TRACE>
    No code provided for execution.
    </TRACE>
    <FINAL_OUTPUT>
    NO_CODE_PROVIDED
    </FINAL_OUTPUT>
    <COMPARISON>
    Cannot execute simulation without code.
    </COMPARISON>
    <CONCLUSION>
    FAILED
    </CONCLUSION>
</SIMULATION_REPORT>"""
    
    # 执行模拟
    simulator = CodeSimulator()
    
    # 传递函数调用代码（如果有的话）
    if 'function_call_code' in locals():
        simulation_result = simulator.simulate_code_execution(
            code=code,
            test_input=test_input,
            function_name=function_name,
            function_call_code=function_call_code
        )
    else:
        simulation_result = simulator.simulate_code_execution(
            code=code,
            test_input=test_input,
            function_name=function_name
        )
    
    # 生成报告
    return simulator.format_simulation_report(simulation_result, expected_output)


def simulate_code_for_node(context, current_code: str) -> str:
    """
    专门为 BlueprintDesignNode 设计的模拟函数
    
    Args:
        context: DebugContext 对象，包含问题描述和测试数据
        current_code: 当前的代码
        
    Returns:
        模拟报告字符串
    """
    # 从 context 中提取测试信息
    test_input = getattr(context, 'test_input', None)
    expected_output = getattr(context, 'expected_output', None)
    function_name = getattr(context, 'function_name', None)
    
    # 尝试从错误日志中解析测试用例
    error_logs = getattr(context, 'error_logs', '')
    assert_statement = None
    if error_logs and not test_input and not function_name:
        # 查找 assert 语句
        assert_pattern = r'assert\s+[^=]+==\s*[^\n]+'
        assert_matches = re.findall(assert_pattern, error_logs, re.MULTILINE)
        
        if assert_matches:
            # 使用第一个找到的 assert 语句
            first_assert = assert_matches[0]
            assert_statement = first_assert
            parsed_test = TestCaseParser.parse_assert_statement(first_assert)
            
            if parsed_test["function_name"]:
                function_name = parsed_test["function_name"]
                expected_output = parsed_test["expected_output"]
    
    # 如果还没有函数名，尝试从问题描述中推断
    if not function_name:
        problem_desc = getattr(context, 'problem_description', '')
        func_match = re.search(r'(\w+)\s*\(', problem_desc)
        if func_match:
            function_name = func_match.group(1)
    
    # 构建 assert 语句用于更好的解析
    if not assert_statement:
        if hasattr(context, 'test_output') and context.test_output:
            assert_statement = context.test_output
        elif hasattr(context, 'tests') and context.tests:
            assert_statement = context.tests
        elif test_input is not None and expected_output is not None and function_name:
            # 如果有单独的参数，构建 assert 语句
            assert_statement = f"assert {function_name}({test_input}) == {expected_output}"
    
    print(f"[DEBUG] 传递给 simulate_code_execution 的参数:")
    print(f"  - code: {len(current_code) if current_code else 0} 字符")
    print(f"  - assert_statement: {assert_statement}")
    print(f"  - function_name: {function_name}")
    print(f"  - test_input: {test_input}")
    print(f"  - expected_output: {expected_output}")
    
    return simulate_code_execution(
        code=current_code,
        assert_statement=assert_statement,
        test_input=test_input,
        function_name=function_name,
        expected_output=expected_output
    )


class TestCaseParser:
    """解析测试用例的工具类"""
    
    @staticmethod
    def parse_assert_statement(assert_statement: str) -> Dict[str, Any]:
        """
        解析 assert 语句，提取函数调用、参数和期望结果
        
        Args:
            assert_statement: assert 语句，如 "assert numerical_letter_grade([4.0, 3, 1.7, 2, 3.5]) == ['A+', 'B', 'C-', 'C', 'A-']"
            
        Returns:
            解析结果字典，包含 function_name, arguments, expected_output
        """
        if not assert_statement:
            return {"function_name": None, "arguments": None, "expected_output": None}
        
        # 移除 assert 关键字
        statement = assert_statement.strip()
        if statement.startswith('assert '):
            statement = statement[7:].strip()
        
        # 查找 == 分隔符
        if ' == ' in statement:
            left_part, right_part = statement.split(' == ', 1)
            expected_output = TestCaseParser._parse_python_literal(right_part.strip())
        else:
            left_part = statement
            expected_output = None
        
        # 解析左边的函数调用
        func_call_info = TestCaseParser._parse_function_call(left_part.strip())
        
        return {
            "function_name": func_call_info.get("function_name"),
            "function_call_code": func_call_info.get("function_call_code"),
            "expected_output": expected_output
        }
    
    @staticmethod
    def _parse_function_call(func_call_str: str) -> Dict[str, Any]:
        """
        解析函数调用字符串
        
        Args:
            func_call_str: 函数调用字符串，如 "numerical_letter_grade([4.0, 3, 1.7, 2, 3.5])"
            
        Returns:
            包含 function_name 和 function_call_code 的字典
        """
        # 使用正则表达式匹配函数名
        pattern = r'(\w+)\s*\('
        match = re.match(pattern, func_call_str.strip())
        
        if not match:
            return {"function_name": None, "function_call_code": None}
        
        function_name = match.group(1)
        
        return {
            "function_name": function_name, 
            "function_call_code": func_call_str.strip()
        }
    
    @staticmethod
    def _parse_python_literal(literal_str: str) -> Any:
        """
        安全地解析 Python 字面量
        
        Args:
            literal_str: Python 字面量字符串
            
        Returns:
            解析后的 Python 对象
        """
        literal_str = literal_str.strip()
        
        try:
            # 使用 ast.literal_eval 进行安全解析
            import ast
            return ast.literal_eval(literal_str)
        except:
            # 如果解析失败，尝试一些简单的模式匹配
            if literal_str.lower() == 'true':
                return True
            elif literal_str.lower() == 'false':
                return False
            elif literal_str.lower() == 'none':
                return None
            elif literal_str.startswith('"') and literal_str.endswith('"'):
                return literal_str[1:-1]
            elif literal_str.startswith("'") and literal_str.endswith("'"):
                return literal_str[1:-1]
            else:
                # 尝试解析为数字
                try:
                    if '.' in literal_str:
                        return float(literal_str)
                    else:
                        return int(literal_str)
                except:
                    # 最后兜底，返回原始字符串
                    return literal_str



# 使用示例
if __name__ == "__main__":
    # 测试1: 基础代码执行
    print("=== 测试1: 基础代码执行 ===")
    sample_code = """
def triangular_number(n):
    if n <= 0:
        return []
    
    result = []
    for i in range(1, n + 1):
        if i == 1:
            result.append(1)
        elif i % 2 == 0:
            result.append(1 + i // 2)
        else:
            result.append(result[i-2] + result[i-1] + i)
    
    return result
"""
    
    report = simulate_code_execution(
        code=sample_code,
        test_input=4,
        function_name="triangular_number",
        expected_output=[1, 3, 2, 8]
    )
    
    print("模拟报告:")
    print(report)
    print()
    
    # 测试2: assert 语句解析
    print("=== 测试2: Assert 语句解析 ===")
    
    # 测试解析功能
    test_assert = "assert numerical_letter_grade([4.0, 3, 1.7, 2, 3.5]) == ['A+', 'B', 'C-', 'C', 'A-']"
    parsed = TestCaseParser.parse_assert_statement(test_assert)
    
    print(f"原始 assert: {test_assert}")
    print(f"解析结果:")
    print(f"  函数名: {parsed['function_name']}")
    print(f"  参数: {parsed['arguments']}")
    print(f"  期望输出: {parsed['expected_output']}")
    print()
    
    # 测试3: 使用 assert 语句进行模拟
    print("=== 测试3: 使用 Assert 语句模拟 ===")
    
    grade_code = """
def numerical_letter_grade(grades):
    result = []
    for grade in grades:
        if grade >= 4.0:
            result.append('A+')
        elif grade >= 3.7:
            result.append('A')
        elif grade >= 3.3:
            result.append('A-')
        elif grade >= 3.0:
            result.append('B+')
        elif grade >= 2.7:
            result.append('B')
        elif grade >= 2.3:
            result.append('B-')
        elif grade >= 2.0:
            result.append('C+')
        elif grade >= 1.7:
            result.append('C')
        elif grade >= 1.3:
            result.append('C-')
        elif grade >= 1.0:
            result.append('D+')
        elif grade >= 0.7:
            result.append('D')
        elif grade >= 0.0:
            result.append('D-')
        else:
            result.append('E')
    return result
"""
    
    report_with_assert = simulate_code_execution(
        code=grade_code,
        assert_statement=test_assert
    )
    
    print("使用 assert 语句的模拟报告:")
    print(report_with_assert)
