import re
import time
from typing import Dict, Any, List, Tuple
from .BaseWorkflow import BaseWorkflow
from agents.core.CodeAgent import CodeAgent
from datasets.APPSDataset import APPSDataset
from datasets.XCodeDataset import XCodeDataset
from constants.verboseType import *
import evaluations.pass_at_k as pass_at_k


class CodeSIMWorkflow(BaseWorkflow):
    """
    CodeSIM 策略工作流
    
    核心流程：
    1. Planning Phase (规划阶段): 生成详细的解题计划
    2. Simulation Phase (模拟阶段): 验证计划的正确性
    3. Plan Refinement Phase (计划优化阶段): 如果模拟失败则修正计划
    4. Code Generation Phase (代码生成阶段): 根据计划生成代码
    5. Testing Phase (测试阶段): 测试代码
    6. Debugging Phase (调试阶段): 如果测试失败则调试代码
    
    特点：
    - 双重循环：外层max_plan_try次（重新规划），内层max_debug_try次（调试代码）
    - 条件性计划优化：只有当模拟阶段判断需要修改时才进行
    """
    
    def __init__(
        self,
        model,
        dataset,
        language: str = "Python3",
        pass_at_k: int = 1,
        results = None,
        verbose: int = VERBOSE_MINIMAL,
        web_search: bool = True,
        docker_execution: bool = True,
        start_index: int = 0,
        max_plan_try: int = 5,
        max_debug_try: int = 5,
        additional_info_run: int = 0,
        prompt_module_path: str = "code",
    ):
        """
        初始化 CodeSIM 工作流
        
        Args:
            model: 模型实例
            dataset: 数据集实例
            language: 编程语言
            pass_at_k: 评估时的pass@k值
            results: 结果记录器实例
            verbose: 输出详细程度
            web_search: 是否启用网络搜索
            docker_execution: 是否使用Docker执行验证
            start_index: 开始处理的数据集索引
            max_plan_try: 最大规划尝试次数
            max_debug_try: 最大调试尝试次数
            additional_info_run: 额外IO生成次数（暂未实现）
            prompt_module_path: 提示词模块路径
        """
        super().__init__(
            model=model,
            dataset=dataset,
            language=language,
            pass_at_k=pass_at_k,
            results=results,
            verbose=verbose,
            web_search=web_search,
            docker_execution=docker_execution,
            start_index=start_index
        )
        
        self.max_plan_try = max_plan_try
        self.max_debug_try = max_debug_try
        self.additional_info_run = additional_info_run
        self.prompt_module_path = prompt_module_path
        
        # 判断是否为竞赛类数据集
        self.is_competitive = isinstance(dataset, (APPSDataset, XCodeDataset))
        
        # 初始化 agents
        self._init_agents()
        
        if self.verbose >= VERBOSE_FULL:
            print("\n" + "_" * 70)
            print(f"Running CodeSIM with max_plan_try={self.max_plan_try}, max_debug_try={self.max_debug_try}")
            print()
    
    def _init_agents(self):
        """初始化所需的 agents"""
        self.code_agent = CodeAgent(
            model=self.model,
            agent_name="CodeSIMAgent",
            verbose=self.verbose
        )
    
    @staticmethod
    def parse_code(response: str) -> str:
        """
        从响应中解析代码（使用 CodeAgent 的 _process_response 更简洁）
        保留此方法以兼容 CodeSIM 的特殊需求
        
        Args:
            response: 模型响应
            
        Returns:
            解析出的代码
        """
        if '<think>' in response and '</think>' in response:
            response = response.split('</think>')[1]
        
        if response is None:
            return ''
        
        if "```" not in response:
            return response
        
        # 尝试多种语言标记
        patterns = [
            (r'```[Pp]ython3?(.*?)```', re.DOTALL),
            (r'```[Cc]\+\+(.*?)```', re.DOTALL),
            (r'```[Cc]pp(.*?)```', re.DOTALL),
            (r'```[Jj]ava(.*?)```', re.DOTALL),
            (r'```[Nn]ode(.*?)```', re.DOTALL),
            (r'```[Rr]ust(.*?)```', re.DOTALL),
            (r'```[Pp]hp(.*?)```', re.DOTALL),
            (r'```[Gg]o(.*?)```', re.DOTALL),
            (r'```[Rr]uby(.*?)```', re.DOTALL),
            (r'```[Cc]#?(.*?)```', re.DOTALL),
            (r'```[Cc]sharp(.*?)```', re.DOTALL),
            (r'```[Cc](.*?)```', re.DOTALL),
            (r'```(.*?)```', re.DOTALL),  # 通用模式
        ]
        
        for pattern, flags in patterns:
            matches = re.findall(pattern, response, flags)
            if matches:
                code_str = matches[-1]
                if isinstance(code_str, tuple):
                    code_str = "\n".join(code_str)
                return code_str.strip()
        
        return response.strip()
    
    @staticmethod
    def process_test_log(test_logs: str) -> str:
        """
        处理测试日志，只保留失败的测试用例
        
        Args:
            test_logs: 测试日志
            
        Returns:
            格式化的失败测试用例信息
        """
        passed_test_cases = []
        failed_test_cases = []
        for test_log in test_logs.splitlines():
            if test_log.startswith("Passed"):
                passed_test_cases.append(test_log[test_log.index("assert"):])
            if test_log.startswith("Failed"):
                failed_test_cases.append(test_log[test_log.index("assert"):])
        
        failed_test_cases_str = "\n".join(failed_test_cases)
        return f"### Test Cases where the generated code failed to generate the expected output:\n{failed_test_cases_str}"
    
    def check(
        self,
        data_row: Dict[str, Any],
        additional_io: List[str],
        code: str
    ) -> Tuple[bool, str]:
        """
        检查代码是否通过 sample_io 和 additional_io（CodeSIM 反馈循环用）
        
        Args:
            data_row: 数据项
            additional_io: 生成的额外测试用例
            code: 生成的代码
            
        Returns:
            (是否通过, 测试日志)
        """
        # 评估 sample_io
        passed_sample, test_log_sample = self.dataset.evaluate_sample_io(
            data_row,
            code,
            self.language
        )
        
        # 评估 additional_io
        passed_additional, test_log_additional = self.dataset.evaluate_additional_io(
            data_row[self.dataset.id_key],
            additional_io,
            code,
            self.language
        )
        
        # 根据是否竞赛题处理测试日志
        if self.is_competitive:
            # 对于 APPS/XCode 等竞赛数据集，提取失败测试部分
            failed_marker = "## Tests failed:"
            idx = test_log_sample.find(failed_marker)
            if idx != -1:
                test_log_sample = test_log_sample[idx:]
            # 如果没有找到标记，保留完整日志
            test_log = test_log_sample + test_log_additional
        else:
            # 对于 HumanEval/MBPP，处理成结构化格式
            test_log = self.process_test_log(test_log_sample + test_log_additional)
        
        # 两者都通过才算通过
        return passed_sample & passed_additional, test_log
    
    def _evaluate_code(self, item: Dict[str, Any], code: str) -> Tuple[bool, float, str]:
        """
        使用完整测试集评估代码（用于最终结果统计）
        
        Args:
            item: 数据项
            code: 生成的代码
            
        Returns:
            (是否通过, 通过率, 错误信息)
        """
        # 获取数据集类型
        dataset_type = self.dataset.__class__.__name__.lower()
        
        # APPS/XCode 竞赛数据集：使用 ExecEval 评估完整的隐藏测试用例
        if "apps" in dataset_type or "xcode" in dataset_type:
            try:
                dataset_name = "APPS" if "apps" in dataset_type else "XCode"
                
                if self.verbose >= VERBOSE_FULL:
                    print(f"\n=== 使用 {dataset_name} ExecEval 测试完整隐藏测试集 ===")
                
                passed = self.dataset.evaluate(
                    item=item,
                    code=code,
                    language=self.language
                )
                
                # 竞赛数据集的 evaluate 方法返回布尔值
                pass_rate = 1.0 if passed else 0.0
                error_msg = "" if passed else f"{dataset_name} ExecEval 测试失败"
                
                if self.verbose >= VERBOSE_FULL:
                    test_count = len(item.get("test_list", []))
                    print(f"评估结果: {'✅ 通过' if passed else '❌ 失败'}")
                    print(f"测试用例数量: {test_count}")
                    print(f"通过率: {pass_rate:.2%}")
                
                return passed, pass_rate, error_msg
                
            except Exception as e:
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"⚠️ {dataset_name if 'dataset_name' in locals() else '竞赛数据集'} 评估出错: {e}")
                return False, 0.0, str(e)
        
        # HumanEval 和 MBPP：使用 pass@k 评估
        from evaluations.pass_at_k import evaluate_humaneval_problem, evaluate_mbpp_problem
        
        # 选择合适的评估函数
        if "humaneval" in dataset_type:
            evaluate_fn = evaluate_humaneval_problem
        elif "mbpp" in dataset_type:
            evaluate_fn = evaluate_mbpp_problem
        else:
            # 默认使用HumanEval评估函数
            evaluate_fn = evaluate_humaneval_problem
        
        try:
            # 使用pass@k评估（k=1）
            eval_result = evaluate_fn(
                problem=item,
                solutions=[code],
                timeout=5
            )
            
            # 解析结果
            is_correct = len(eval_result.get("correct", [])) > 0
            pass_rate = eval_result.get("pass_rate", 0.0)
            
            # 获取错误信息
            error_msg = ""
            errors = eval_result.get("errors", [])
            if errors:
                error_msg = str(errors[0][1]) if len(errors[0]) > 1 else str(errors[0])
        
            return is_correct, pass_rate, error_msg
            
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"⚠️ 评估出错: {e}")
            return False, 0.0, str(e)
    
    def process_item(self, item: Dict[str, Any], imp_id: int = 0) -> Dict[str, Any]:
        """
        处理单个数据项
        
        Args:
            item: 数据项
            imp_id: 实现ID（用于多次采样）
            
        Returns:
            处理结果（标准格式）
        """
        import time
        start_time = time.time()
        
        # 开始 token 计数
        self.model.start_token_count()
        
        problem_id = item.get(self.dataset.id_key, "unknown")
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*70}")
            print(f"Processing item: {problem_id}")
            print(f"{'='*70}")
        
        # 获取问题描述
        problem = self.dataset.get_prompt(item)
        
        # 设置标准输入提示（针对竞赛类问题）
        std_input_prompt = ""
        if self.is_competitive:
            std_input_prompt = """- Strictly follow the sample input and output format. 
    - The input should be taken from Standard input and output should be given to standard output. If you are writing a function then after the function definition take the input using `input()` function then call the function with specified parameters and finally print the output of the function. 
    - For array input parse the array then pass it to the function. Parsing technique is given in the sample input output format section.
    - Do not add extra print statement otherwise it will failed the test cases."""
            
            # 移除原有的 Important Note 部分
            if "-------\nImportant Note:" in problem:
                problem = problem[:problem.find("-------\nImportant Note:")]
        
        # 额外IO（暂未实现，保留接口）
        additional_io = []
        
        # 加载提示词模块
        from strategies.prompt_loader import prompt_loader
        codesim_prompts = prompt_loader.get_prompt_module(self.prompt_module_path)
        
        # 初始化结果
        final_code = ""
        passed = False
        pass_rate = 0.0
        plan_iterations_used = 0
        debug_iterations_used = 0
        
        # 主循环：规划 + 编码 + 调试
        for plan_no in range(1, self.max_plan_try + 1):
            plan_iterations_used = plan_no
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{'='*70}")
                print(f"Plan Iteration {plan_no}/{self.max_plan_try}")
                print(f"{'='*70}")
            
            # ===== 1. Planning Phase (规划阶段) =====
            planning_messages = codesim_prompts.get_planning_messages(
                problem=problem,
                language=self.language
            )
            
            if self.verbose >= VERBOSE_FULL:
                print("\n" + "_" * 70)
                print(f"Input for Planning: {plan_no}\n")
                print(planning_messages[0]['content'])
            
            planning_response = self.code_agent._call_model(
                planning_messages,
                include_history=False
            )
            
            if self.verbose >= VERBOSE_FULL:
                print("\n" + "_" * 70)
                print(f"Response from Planning: {plan_no}\n")
                print(planning_response)
            
            # 提取计划
            if "### Plan" not in planning_response:
                plan = f"### Plan\n\n{planning_response}"
            else:
                plan = planning_response[planning_response.rfind("### Plan"):]
            
            problem_with_planning = f"## Problem:\n{problem}\n\n{plan}"
            
            # ===== 2. Simulation Phase (模拟阶段) =====
            simulation_messages = codesim_prompts.get_simulation_messages(
                problem_with_planning=problem_with_planning,
                language=self.language
            )
            
            if self.verbose >= VERBOSE_FULL:
                print("\n" + "_" * 70)
                print(f"Input for Simulation: {plan_no}\n")
                print(simulation_messages[0]['content'])
            
            simulation_response = self.code_agent._call_model(
                simulation_messages,
                include_history=False
            )
            
            if self.verbose >= VERBOSE_FULL:
                print("\n" + "_" * 70)
                print(f"Response from Simulation: {plan_no}\n")
                print(simulation_response)
            
            # ===== 3. Plan Refinement Phase (计划优化阶段 - 条件性执行) =====
            if "Plan Modification Needed" in simulation_response and \
               "No Plan Modification Needed" not in simulation_response:
                
                if self.verbose >= VERBOSE_MINIMAL:
                    print("\n" + "_" * 70)
                    print("**Plan Modification Needed.**")
                
                plan_refinement_messages = codesim_prompts.get_plan_refinement_messages(
                    problem_with_planning=problem_with_planning,
                    critique=simulation_response,
                    language=self.language
                )
                
                if self.verbose >= VERBOSE_FULL:
                    print("\n" + "_" * 70)
                    print(f"Input for Plan Refinement: {plan_no}\n")
                    print(plan_refinement_messages[0]['content'])
                
                plan = self.code_agent._call_model(
                    plan_refinement_messages,
                    include_history=False
                )
                
                if self.verbose >= VERBOSE_FULL:
                    print("\n" + "_" * 70)
                    print(f"Response from Plan Refinement: {plan_no}\n")
                    print(plan)
                
                problem_with_planning = f"## Problem:\n{problem}\n\n{plan}"
            
            # ===== 4. Code Generation Phase (代码生成阶段) =====
            code_generation_messages = codesim_prompts.get_code_generation_messages(
                problem_with_planning=problem_with_planning,
                language=self.language,
                std_input_prompt=std_input_prompt
            )
            
            if self.verbose >= VERBOSE_FULL:
                print("\n" + "_" * 70)
                print("Input for final code generation:\n")
                print(code_generation_messages[0]['content'])
            
            code_response = self.code_agent._call_model(
                code_generation_messages,
                include_history=False
            )
            
            if self.verbose >= VERBOSE_FULL:
                print("\n" + "_" * 70)
                print("Response from final code generation:\n")
                print(code_response)
            
            # 解析代码
            code = self.parse_code(code_response)
            final_code = code
            
            # ===== 5. Testing Phase (测试阶段) - 使用 sample_io 评估 =====
            passed, test_log = self.check(item, additional_io, code)
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\nCode Testing Result: {'PASSED' if passed else 'FAILED'}")
                if not passed and test_log and self.verbose >= VERBOSE_FULL:
                    print(f"Test Log:\n{test_log}")
            
            # 如果通过测试，跳出规划循环
            if passed:
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"\n✓ Code passed all tests in plan iteration {plan_no}")
                debug_iterations_used = 0
                break
            
            # ===== 6. Debugging Phase (调试阶段) =====
            for debug_no in range(1, self.max_debug_try + 1):
                debug_iterations_used = debug_no
                
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"\n{'-'*70}")
                    print(f"Debug Iteration {debug_no}/{self.max_debug_try} (Plan {plan_no})")
                    print(f"{'-'*70}")
                
                # 使用测试日志（从 check 方法获得）
                debugging_messages = codesim_prompts.get_debugging_messages(
                    problem_with_planning=problem_with_planning,
                    code=code,
                    test_log=test_log,
                    language=self.language,
                    std_input_prompt=std_input_prompt
                )
                
                if self.verbose >= VERBOSE_FULL:
                    print("\n" + "_" * 70)
                    print(f"Input for Debugging: {plan_no}, {debug_no}\n")
                    print(debugging_messages[0]['content'])
                
                debug_response = self.code_agent._call_model(
                    debugging_messages,
                    include_history=False
                )
                
                if self.verbose >= VERBOSE_FULL:
                    print("\n" + "_" * 70)
                    print(f"Response from Debugging: {plan_no}, {debug_no}\n")
                    print(debug_response)
                
                # 解析调试后的代码
                code = self.parse_code(debug_response)
                final_code = code
                
                # 再次测试 - 使用 sample_io 评估
                passed, test_log = self.check(item, additional_io, code)
                
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"Debug Testing Result: {'PASSED' if passed else 'FAILED'}")
                    if not passed and test_log and self.verbose >= VERBOSE_FULL:
                        print(f"Test Log:\n{test_log}")
                
                # 如果通过测试，跳出调试循环
                if passed:
                    if self.verbose >= VERBOSE_MINIMAL:
                        print(f"\n✓ Code passed all tests after debug iteration {debug_no}")
                    break
            
            # 如果调试后通过测试，跳出规划循环
            if passed:
                break
        
        if self.verbose >= VERBOSE_FULL:
            print("\n" + "_" * 70)
        
        # ===== 最终评估（使用完整测试集）=====
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*70}")
            print("Final Evaluation with Complete Test Suite")
            print(f"{'='*70}")
        
        final_passed, final_pass_rate, final_error_msg = self._evaluate_code(item, final_code)
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"Final Result: {'PASSED' if final_passed else 'FAILED'} (pass_rate: {final_pass_rate:.2%})")
            if not final_passed and final_error_msg and self.verbose >= VERBOSE_FULL:
                print(f"Error: {final_error_msg}")
        
        # 构建结果（标准格式，与 TeamCoderWorkflowV1 一致）
        end_time = time.time()
        total_time = end_time - start_time
        tokens_used = self.model.end_token_count()
        
        result_dict = {
            "problem_id": problem_id,
            "passed": final_passed,
            "pass_rate": final_pass_rate,
            "code": final_code,
            "total_time": total_time,
            "tokens_used": tokens_used
        }
        
        return result_dict
