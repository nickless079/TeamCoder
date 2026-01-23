"""
状态机调试系统使用示例

展示如何使用新的状态机驱动的三角色协作调试系统
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from models.AlibabaModel import AlibabaModel
from models import OllamaModel
from agents.planning.SolutionPlanningAgent import SolutionPlanningAgent
from agents.core.CodeAgent import CodeAgent
from agents.core.CTOAgent import CTOAgent
from utils.dialogue import StateMachineOrchestrator

def create_test_example():
    """创建一个测试示例"""
    
    # 初始化模型（需要根据实际情况配置）
    # model = AlibabaModel(
    #     model_name="qwen3-4b",
    #     api_key="sk-e44cea2110114dc38b9e20fc2e5e4c40",  # 需要替换为实际的API密钥，或通过环境变量ALIBABA_API_KEY设置
    #     verbose=2
    # )

    model = OllamaModel(
        model_name="qwen3:4b-fp16",
    
    )
    
    # 初始化智能体并开始各自的session
    solution_agent = SolutionPlanningAgent(
        model=model, 
        verbose=2
    )
    solution_agent.start_new_session()  # 开始SolutionAgent的session
    
    code_agent = CodeAgent(
        model=model, 
        verbose=2
    )
    code_agent.start_new_session()  # 开始CodeAgent的session
    
    # 初始化SimulationAgent（使用CTOAgent担任）
    simulation_agent = CTOAgent(
        model=model,
        verbose=2
    )
    simulation_agent.start_new_session()  # 开始SimulationAgent的session
    
    print(f"✅ SolutionAgent Session ID: {getattr(solution_agent, 'session_id', 'Not Set')}")
    print(f"✅ CodeAgent Session ID: {getattr(code_agent, 'session_id', 'Not Set')}")
    print(f"✅ SimulationAgent Session ID: {getattr(simulation_agent, 'session_id', 'Not Set')}")
    
    # 初始化状态机协调器
    orchestrator = StateMachineOrchestrator(
        solution_agent=solution_agent,
        code_agent=code_agent,
        simulation_agent=simulation_agent,  # 添加新的SimulationAgent
        quality_model=model,  # 使用同一个模型进行质量评估
        verbose=2
    )
    
    # 测试问题示例
    problem_description = """
def poly(xs: list, x: float):
    \"\"\"
    Evaluates polynomial with coefficients xs at point x.
    return xs[0] + xs[1] * x + xs[1] * x^2 + .... xs[n] * x^n
    \"\"\"
    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])

def find_zero(xs: list):
    \"\"\"
    Find a zero point x such that poly(x) = 0.
    Returns only one zero point, even if multiple exist.
    Only takes list xs with even number of coefficients.
    Guarantees a solution if the largest non-zero coefficient is present.
    >>> round(find_zero([1, 2]), 2) # f(x) = 1 + 2x
    -0.5
    >>> round(find_zero([-6, 11, -6, 1]), 2) # (x - 1) * (x - 2) * (x - 3) = -6 + 11x - 6x^2 + x^3
    1.0
    \"\"\"
"""
    
    # 错误代码示例
    current_code = """
import math

def poly(xs: list, x: float):
    \"\"\"
    Evaluates polynomial with coefficients xs at point x.
    return xs[0] + xs[1] * x + xs[1] * x^2 + .... xs[n] * x^n
    \"\"\"
    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])

def find_zero(xs: list):
    \"\"\"
    Find a zero point x such that poly(x) = 0.
    Returns only one zero point, even if multiple exist.
    Only takes list xs with even number of coefficients.
    Guarantees a solution if the largest non-zero coefficient is present.
    \"\"\"
    if len(xs) % 2 != 0:
        raise ValueError('Input list must have an even number of coefficients.')
    max_coeff = max((coeff for coeff in xs if coeff != 0), default=0)
    if max_coeff == 0:
        return 0.0
    even_index = 0
    odd_index = 1
    while even_index < len(xs) and xs[even_index] == 0:
        even_index += 2
    while odd_index < len(xs) and xs[odd_index] == 0:
        odd_index += 2
    if even_index >= len(xs) or odd_index >= len(xs):
        return 0.0
    return -xs[even_index] / xs[odd_index]
"""
    
    # 测试用例
    test_cases = [
        "assert round(find_zero([1, 2]), 2) == -0.5",
        "assert round(find_zero([-6, 11, -6, 1]), 2) == 1.0"
    ]
    
    # 错误日志
    error_logs = f"""
Debug Agent: Code failed 1 sample I/O tests
Test log: Test 1 passed: assert round(find_zero([1, 2]), 2) == -0.5
Test 2 failed: assert round(find_zero([-6, 11, -6, 1]), 2) == 1.0
Error: assert round(find_zero([-6, 11, -6, 1]), 2) == 1.0 is wrong, current output is 0.55
"""
    attention_analysis = {'fatal_points': {'Rules': 'The function find_zero takes a list of polynomial coefficients with an even number of elements and returns a single zero point x such that poly(x) = 0. It guarantees a solution if the largest non-zero coefficient is present, and returns only one zero point even if multiple exist.', 'Traps': '{\n  "Primary_Trap": {\n    "trap_statement": "Failing to ensure the list of coefficients has an even number of elements results in an invalid input, as the function is designed to only operate on polynomials with an even number of coefficients.",\n    "violating_logic_example": "Calling find_zero with a list of odd length, such as [1, 2, 3], would violate the core principle and result in an error or incorrect behavior."\n  },\n  "Secondary_Trap": {\n    "trap_statement": "Not guaranteeing a solution when the largest non-zero coefficient is present can lead to incorrect or missing zero points, as the function is designed to guarantee a solution under this condition.",\n    "violating_logic_example": "A polynomial like [0, 0, 1] (which is x^2) would have a largest non-zero coefficient, but the function might fail to find a solution if not properly implemented."\n  }\n}'}}
    
    
    
    return {
        "problem_description": problem_description,
        "current_code": current_code,
        "test_cases": test_cases,
        "error_logs": error_logs,
        "orchestrator": orchestrator,
        "attention_analysis": attention_analysis  # 示例attention分析结果
    }

def run_debug_example():
    """运行调试示例"""
    
    # 设置日志文件路径
    log_file_path = os.path.join(os.path.dirname(__file__), "debug_session_log.txt")
    
    print("🚀 状态机调试系统示例")
    print("=" * 50)
    print(f"📄 日志文件: {log_file_path}")
    
    try:
        # 创建测试示例
        example = create_test_example()
        orchestrator = example.pop("orchestrator")
        
        # 重定向print输出到文件
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            # 保存原始stdout
            original_stdout = sys.stdout
            
            # 创建一个同时输出到控制台和文件的类
            class TeeOutput:
                def __init__(self, console, file):
                    self.console = console
                    self.file = file
                
                def write(self, message):
                    self.console.write(message)
                    self.file.write(message)
                    self.file.flush()
                
                def flush(self):
                    self.console.flush()
                    self.file.flush()
            
            # 设置输出重定向
            sys.stdout = TeeOutput(original_stdout, log_file)
            
            try:
                print("=" * 80)
                print("🚀 状态机调试系统执行日志")
                print(f"⏰ 开始时间: {os.popen('date').read().strip()}")
                print("=" * 80)
                print()
                
                # 记录输入信息
                print("📋 输入信息:")
                print("-" * 40)
                print(f"问题描述:\n{example['problem_description']}")
                print(f"当前代码:\n{example['current_code']}")
                print(f"测试用例: {example['test_cases']}")
                print(f"错误日志: {example['error_logs']}")
                print()
                
                # 提高详细级别以获取更多日志
                orchestrator.verbose = 2
                
                # 执行调试
                result = orchestrator.debug_problem(**example)
            
            finally:
                # 恢复原始stdout
                sys.stdout = original_stdout
        
        # 输出结果到控制台和文件
        print("\n" + "=" * 50)
        print("🎯 调试结果")
        print("=" * 50)
        
        if result["success"]:
            print("✅ 调试成功!")
            print(f"⏱️  总耗时: {result['execution_time']:.2f} 秒")
            print(f"🔄 重启次数: {result['restart_count']}")
            print("\n📝 最终代码:")
            print(result["final_code"])
        else:
            print("❌ 调试失败!")
            print(f"💀 错误信息: {result['error']}")
            print(f"⏱️  总耗时: {result['execution_time']:.2f} 秒")
            print(f"🔄 重启次数: {result['restart_count']}")
        
        # 显示执行历史
        print("\n📊 执行历史:")
        for i, history_item in enumerate(result["execution_history"], 1):
            status = "✅" if history_item["success"] else "❌"
            print(f"{i}. {status} {history_item['node']} ({history_item['execution_time']:.2f}s)")
            if not history_item["success"] and history_item.get("error"):
                print(f"   💀 {history_item['error']}")
        
        print(f"\n📄 完整日志已保存到: {log_file_path}")
        
    except Exception as e:
        print(f"💥 示例执行失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行示例
    run_debug_example()
