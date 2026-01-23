from typing import List, Tuple, Any, Dict
import contextlib
import signal
import time
import traceback

class TimeoutException(Exception):
    """超时异常"""
    pass

def timeout_handler(signum, frame):
    """超时处理函数"""
    raise TimeoutException("代码执行超时")

def _create_safe_namespace():
    """
    创建一个安全的命名空间，包含必要的内置函数
    
    Returns:
        一个干净的命名空间字典
    """
    import builtins
    
    # 创建一个新的命名空间，包含所有内置函数
    namespace = {
        '__builtins__': builtins,
    }
    
    return namespace

def function_with_timeout(func, args=(), kwargs={}, timeout=5):
    """
    带超时的函数执行
    
    Args:
        func: 要执行的函数
        args: 位置参数
        kwargs: 关键字参数
        timeout: 超时时间(秒)
        
    Returns:
        函数执行结果
        
    Raises:
        TimeoutException: 如果函数执行超时
    """
    # 设置信号处理器
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        result = func(*args, **kwargs)
        signal.alarm(0)  # 取消闹钟
        return result
    except TimeoutException:
        raise
    finally:
        signal.alarm(0)  # 确保取消闹钟

def evaluate_io(
    sample_io: List[str],
    completion: str,
    timeout: int = 5,
    stop_early: bool = False,
) -> Tuple[bool, str]:
    """
    使用样例输入输出评估代码
    
    Args:
        sample_io: 样例输入输出列表
        completion: 生成的代码
        timeout: 超时时间(秒)
        stop_early: 是否在第一个失败的测试用例处停止
        
    Returns:
        (是否通过, 测试日志)
    """
    if not sample_io:
        return True, ""
    
    test_log = ""
    passed = True
    
    for io in sample_io:
        try:
            # 为每个测试用例创建独立的命名空间
            namespace = _create_safe_namespace()
            
            # 添加typing导入（如果需要）
            code = ("from typing import *\n" if "from typing import *" not in completion else "") + \
                completion + "\n" + io + "\n"
            
            function_with_timeout(
                exec,
                (code, namespace),  # 使用独立的命名空间
                timeout=timeout
            )
            test_log += f"通过测试用例: {io}\n"
        except TimeoutException:
            if stop_early:
                return False, f"测试用例执行超时: {io}\n"
            passed = False
            test_log += f"测试用例执行超时: {io}\n"
        except Exception as e:
            if stop_early:
                return False, f"测试用例失败: {io}\n错误: {str(e)}\n{traceback.format_exc()}\n"
            passed = False
            test_log += f"测试用例失败: {io}\n错误: {str(e)}\n"
    
    return passed, test_log

def evaluate_functional_correctness(
    test: str,
    entry_point: str,
    completion: str,
    timeout: int = 5,
) -> str:
    """
    评估代码的功能正确性
    
    Args:
        test: 测试代码
        entry_point: 入口点函数名
        completion: 生成的代码
        timeout: 超时时间(秒)
        
    Returns:
        "passed" 或错误信息
    """
    try:
        # 创建独立的命名空间
        namespace = _create_safe_namespace()
        
        # 添加typing导入（如果需要）
        code = \
            completion + "\n" + test + \
            "\n" + f"check({entry_point})"
        
        function_with_timeout(
            exec,
            (code, namespace),  # 使用独立的命名空间
            timeout=timeout
        )
        return "passed"
    except TimeoutException:
        return f"failed: 执行超时 ({timeout}秒)"
    except Exception as e:
        return f"failed: {str(e)}"

def evaluate_mbpp_functional_correctness(
    test: str,
    entry_point: str,
    completion: str,
    timeout: int = 5,
) -> str:
    """
    评估MBPP代码的功能正确性
    
    Args:
        test: 测试代码（包含test_check()调用）
        entry_point: 入口点函数名（用于验证）
        completion: 生成的代码
        timeout: 超时时间(秒)
        
    Returns:
        "passed" 或错误信息
    """
    try:
        # 创建独立的命名空间
        namespace = _create_safe_namespace()
        
        # 添加typing导入（如果需要）
        code = ("from typing import *\n" if "from typing import *" not in completion else "") + \
            completion + "\n" + test
        
        # MBPP的test代码已经包含了test_check()调用，不需要额外添加
        function_with_timeout(
            exec,
            (code, namespace),  # 使用独立的命名空间
            timeout=timeout
        )
        return "passed"
    except TimeoutException:
        return f"failed: 执行超时 ({timeout}秒)"
    except Exception as e:
        return f"failed: {str(e)}"

def evaluate_mbpp_sample_io(
    sample_io: List[str],
    completion: str,
    entry_point: str,
    timeout: int = 5,
    stop_early: bool = False,
) -> Tuple[bool, str]:
    """
    使用样例输入输出评估MBPP代码
    
    Args:
        sample_io: 样例输入输出列表（直接调用函数的断言）
        completion: 生成的代码
        entry_point: 入口点函数名
        timeout: 超时时间(秒)
        stop_early: 是否在第一个失败的测试用例处停止
        
    Returns:
        (是否通过, 测试日志)
    """
    if not sample_io:
        return True, ""
    
    test_log = ""
    passed = True
    
    for io in sample_io:
        try:
            # 为每个测试用例创建独立的命名空间
            namespace = _create_safe_namespace()
            
            # 添加typing导入和生成的代码
            code = ("from typing import *\n" if "from typing import *" not in completion else "") + \
                completion + "\n" + io + "\n"
            
            function_with_timeout(
                exec,
                (code, namespace),  # 使用独立的命名空间
                timeout=timeout
            )
            test_log += f"通过测试用例: {io}\n"
        except TimeoutException:
            if stop_early:
                return False, f"测试用例执行超时: {io}\n"
            passed = False
            test_log += f"测试用例执行超时: {io}\n"
        except Exception as e:
            if stop_early:
                return False, f"测试用例失败: {io}\n错误: {str(e)}\n{traceback.format_exc()}\n"
            passed = False
            test_log += f"测试用例失败: {io}\n错误: {str(e)}\n"
    
    return passed, test_log

def execute_code_in_env(
    code: str,
    timeout: int = 5,
) -> Tuple[bool, str, Any]:
    """
    在隔离环境中执行代码
    
    Args:
        code: 要执行的代码
        timeout: 超时时间(秒)
        
    Returns:
        (是否成功, 输出或错误信息, 最后一个表达式的值)
    """
    # 创建一个新的全局命名空间
    namespace = {}
    
    # 捕获标准输出和标准错误
    from io import StringIO
    import sys
    
    stdout = StringIO()
    stderr = StringIO()
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    sys.stdout = stdout
    sys.stderr = stderr
    
    result = None
    success = False
    
    try:
        # 执行代码
        function_with_timeout(
            exec,
            (code, namespace),
            timeout=timeout
        )
        success = True
    except TimeoutException:
        output = f"执行超时 ({timeout}秒)"
    except Exception as e:
        output = f"执行错误: {str(e)}\n{traceback.format_exc()}"
    else:
        output = stdout.getvalue() + stderr.getvalue()
        # 尝试获取最后一个表达式的值
        if "_" in namespace:
            result = namespace["_"]
    finally:
        # 恢复标准输出和标准错误
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    return success, output, result 