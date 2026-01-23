from typing import Dict, Any, List, Optional, Tuple
import time
import json
import os
import re

from .BaseWorkflow import BaseWorkflow
from models.Base import BaseModel
from datasets.Dataset import Dataset
from datasets.APPSDataset import APPSDataset
from utils.results import Results
from utils.grammarcheck import GrammarChecker
from constants.verboseType import *


from agents.testing.EquivalenceClassAgent import EquivalenceClassAgent
from agents.testing.BoundaryValueAgent import BoundaryValueAgent
from agents.testing.DecisionTableAgent import DecisionTableAgent
from agents.testing.CauseEffectAgent import CauseEffectAgent
from agents.testing.OrthogonalTestAgent import OrthogonalTestAgent

# from agents.planning.WebSearchAgent import WebSearchAgent
# from agents.planning.SolutionSynthesisAgent import SolutionSynthesisAgent

# from agents.core.CodingAgent import CodingAgent
# from agents.core.CTOAgent import CTOAgent

# from agents.execution.DockerExecutor import DockerExecutor

class TeamCoderWorkflowV1(BaseWorkflow):
    """
    TeamCoder工作流实现，CTO监督下的多智能体协作代码生成
    """
    def __init__(
        self,
        model: BaseModel,
        dataset: Dataset,
        language: str,
        pass_at_k: int = 1,
        results: Optional[Results] = None,
        verbose: int = 1,
        web_search: bool = True,
        docker_execution: bool = True,
        max_test_time: int = 600,  # 10分钟
        max_planning_time: int = 600,  # 10分钟
        max_coding_time: int = 300,  # 5分钟
        max_execution_time: int = 180,  # 3分钟
        start_index: int = 0,  # 添加start_index参数
    ):
        """
        初始化TeamCoder工作流
        
        Args:
            model: 模型实例
            dataset: 数据集实例
            language: 编程语言
            pass_at_k: 评估时的pass@k值
            results: 结果记录器实例
            verbose: 输出详细程度
            web_search: 是否启用网络搜索
            docker_execution: 是否使用Docker执行验证
            max_test_time: 测试阶段最大时间(秒)
            max_planning_time: 规划阶段最大时间(秒)
            max_coding_time: 编码阶段最大时间(秒)
            max_execution_time: 执行阶段最大时间(秒)
            start_index: 开始处理的数据集索引，默认为0
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
            start_index=start_index,  # 传递start_index参数
        )
        
        self.max_test_time = max_test_time
        self.max_planning_time = max_planning_time
        self.max_coding_time = max_coding_time
        self.max_execution_time = max_execution_time
        
        # 判断是否为竞赛型数据集（APPS 使用 input/output 格式，不是 assert 语句）
        self.is_competitive = isinstance(self.dataset, APPSDataset)
        
        if self.verbose >= VERBOSE_MINIMAL and self.is_competitive:
            print(f"✓ 检测到竞赛型数据集 (APPS)，将使用 ExecEval 进行代码评估")
        
        # 初始化智能体
        self._init_agents()
        
    def _init_agents(self):
        """
        初始化所有智能体
        """
        from agents.core.CTOAgent import CTOAgent
        from agents.core.CodeAgent import CodeAgent
        from agents.core.DebugAgent import DebugAgent
        from agents.core.AttentionAgent import AttentionAgent
        from agents.core.ArbiterAgent import ArbiterAgent
        from agents.planning.SolutionPlanningAgent import SolutionPlanningAgent
        from agents.testing.TestAgent import TestAgent
        
        # 注意力智能体 - 阶段0：重点分析
        self.attention_agent = AttentionAgent(
            model=self.model,
            verbose=self.verbose
        )
        
        # CTO智能体
        self.cto_agent = CTOAgent(
            model=self.model,
            verbose=self.verbose
        )
        
        # 解决方案规划智能体
        self.solution_planning_agent = SolutionPlanningAgent(
            model=self.model,
            verbose=self.verbose
        )
        
        # 代码生成智能体
        self.code_agent = CodeAgent(
            model=self.model,
            verbose=self.verbose
        )
        
        # 调试智能体
        self.debug_agent = DebugAgent(
            verbose=self.verbose
        )
        
        # 测试智能体 - 使用单一的综合测试智能体
        self.test_agent = TestAgent(
            model=self.model,
            verbose=self.verbose
        )
        
        # 仲裁智能体 - 生成最终正确的测试套件
        self.arbiter_agent = ArbiterAgent(
            model=self.model,
            verbose=self.verbose
        )
        
        # 记录阶段0的session_id，用于后续testcase分析
        self.stage0_attention_session_id = None

        # 语法检查器，使用代码智能体作为修复代理
        self.grammar_checker = GrammarChecker(
            fixer_agent=self.code_agent,
            verbose=self.verbose,
            max_fix_attempts=2,
        )
    
    def _extract_sample_io_from_test_cases(self, test_cases: list) -> list:
        """
        从test_cases中提取assertion字段作为sample_io
        
        Args:
            test_cases: 测试用例列表，每个元素包含assertion字段
            
        Returns:
            sample_io列表，直接使用assertion的原始内容，最多取前3个
        """
        sample_io = []
        
        if not test_cases:
            return sample_io
            
        for test_case in test_cases:
            assertion = test_case.get("assertion", "")
            if assertion:
                # 直接使用assertion的原始内容作为sample_io
                sample_io.append(assertion.strip())
                
        # 如果生成的测试用例长度大于3，只取前3个
        if len(sample_io) > 3:
            sample_io = sample_io[:3]
                
        return sample_io
    
    def _extract_assertions_from_test_cases(self, test_cases: list) -> list:
        """
        从test_cases中提取assertion内容，返回纯粹的assertion列表
        
        Args:
            test_cases: 测试用例列表，每个元素包含assertion字段
            
        Returns:
            纯粹的assertion列表，如["assert func() == value", ...]
        """
        assertions = []
        
        if not test_cases:
            return assertions
            
        for test_case in test_cases:
            assertion = test_case.get("assertion", "")
            if assertion:
                # 直接使用assertion的原始内容
                assertions.append(assertion.strip())
                
        return assertions
    
   
        
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个问题项
        
        Args:
            item: 问题项
            
        Returns:
            处理结果
        """
        import time
        start_time = time.time()
        self.model.start_token_count()
        problem_id = item[self.dataset.id_key]
        problem_description = self.dataset.get_prompt(item)
        problem_sample_io = item["sample_io"]
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}\n处理问题 {problem_id}\n{'='*50}")
            print(f"问题描述:\n{problem_description}\n")
        
        code_result = {}
        #if use_direct: 
        code_result = self._generate_init_code(problem_description, problem_sample_io=problem_sample_io, item=item)
        generated_code = "" # code_result.get("success", False) is False
        if code_result.get("success", False) is False:
            print(f"❌ 初始化代码生成失败: {code_result.get('error', '')}")
            error_code = code_result.get("code", "")

            error_info = code_result.get("error","")

            # 阶段零: 重点分析 - 找出最容易被忽视的致命关键点
            attention_analysis = self._analyze_critical_points(problem_description, problem_sample_io,error_code,error_info)


            # test_cases=test_scenarios_list
            test_cases = ["consider the sample io"]
            thought_content=""

            technical_plan=""
            # 阶段三: 智能编码生成
            code_result = self._generate_code(problem_description, test_cases=test_cases, parsed_assertions=test_cases, thought_content=thought_content, problem_sample_io=problem_sample_io, technical_plan=technical_plan, attention_analysis=attention_analysis,error_code=error_code,error_info=error_info, item=item)

            # 获取生成的代码
            generated_code = code_result.get("code", "")

            # 立即评估生成的代码（使用pass@k方式）
            if self.verbose >= VERBOSE_MINIMAL:
                print("\n立即评估生成的代码 (pass@1):")
        else:
            generated_code = code_result.get("code", "")

        try:
            # 获取数据集类型
            dataset_type = self.dataset.__class__.__name__.lower()
            
            # 根据数据集类型选择评估方式
            if "apps" in dataset_type:
                # APPS 数据集：使用 ExecEval 评估完整的隐藏测试用例
                if self.verbose >= VERBOSE_MINIMAL:
                    print("\n=== 最终评估：使用 ExecEval 测试完整隐藏测试集 ===")
                
                passed = self.dataset.evaluate(
                    item=item,
                    code=generated_code,
                    language=self.language
                )
                
                # APPS 数据集的 evaluate 方法返回布尔值
                pass_rate = 1.0 if passed else 0.0
                
                if self.verbose >= VERBOSE_MINIMAL:
                    test_count = len(item.get("test_list", []))
                    print(f"评估结果: {'✅ 通过' if passed else '❌ 失败'}")
                    print(f"测试用例数量: {test_count}")
                    print(f"通过率: {pass_rate:.2%}")
            
            elif "humaneval" in dataset_type or "mbpp" in dataset_type:
                # HumanEval/MBPP 数据集：使用 pass@k 评估函数
                from evaluations.pass_at_k import evaluate_humaneval_problem, evaluate_mbpp_problem
                
                if "humaneval" in dataset_type:
                    evaluate_fn = evaluate_humaneval_problem
                elif "mbpp" in dataset_type:
                    evaluate_fn = evaluate_mbpp_problem
                else:
                    evaluate_fn = evaluate_humaneval_problem
                
                # 使用pass@k评估（k=1）
                eval_result = evaluate_fn(
                    problem=item,
                    solutions=[generated_code],
                    timeout=30
                )
                
                # 解析结果
                passed = len(eval_result.get("correct", [])) > 0
                pass_rate = eval_result.get("pass_rate", 0.0)
                
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"评估结果: {'通过' if passed else '失败'}")
                    print(f"通过率: {pass_rate:.2%}")
                    
                    # 如果有错误信息，显示第一个错误
                    errors = eval_result.get("errors", [])
                    if errors and self.verbose >= VERBOSE_FULL:
                        print(f"错误信息: {errors[0][1]}")
            
            else:
                # 未知数据集类型，尝试使用通用评估
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"⚠️ 未知数据集类型: {dataset_type}，使用默认 HumanEval 评估")
                
                from evaluations.pass_at_k import evaluate_humaneval_problem
                eval_result = evaluate_humaneval_problem(
                    problem=item,
                    solutions=[generated_code],
                    timeout=5
                )
                
                passed = len(eval_result.get("correct", [])) > 0
                pass_rate = eval_result.get("pass_rate", 0.0)
                
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"❌ 评估时出错: {str(e)}")
                import traceback
                if self.verbose >= VERBOSE_FULL:
                    traceback.print_exc()
            passed = False
            pass_rate = 0.0
        
        # 构建结果
        end_time = time.time()
        total_time = end_time - start_time
        tokens_used = self.model.end_token_count()
        result_dict = {
            "problem_id": problem_id,
            "passed": passed,
            "pass_rate": pass_rate,
            "code": generated_code,
            "total_time": total_time,
            "tokens_used": tokens_used
        }
        
        return result_dict

  

    def _analyze_critical_points(self, problem_description: str, sample_io: List[str] = None, error_code: str = "", error_info: List[str] = None) -> Dict[str, Any]:
        """
        阶段零：分析问题中最容易被忽视的致命关键点
        
        Args:
            problem_description: 问题描述
            sample_io: 样例输入输出
            
        Returns:
            关键点分析结果
        """
        import time
        start_time = time.time()
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print("阶段零: 重点分析 - 寻找最容易被忽视的致命关键点")
            print(f"{'='*50}")
        attention_session_id = self.attention_agent.start_new_session()
        self.stage0_attention_session_id = attention_session_id  # 保存session_id供后续testcase分析使用
        
        # 使用AttentionAgent进行重点分析
        attention_result = self.attention_agent.find_fatal_points(
            problem_description=problem_description,
            sample_io=sample_io or [],
            error_info=error_info or [],
            error_code=error_code,
            session_id=attention_session_id
        )
        
        # 处理分析结果
        fatal_points = attention_result.get("fatal_points", "")
        recheck = attention_result.get("recheck", "")
        
        # # AttentionAgent自我纠错阶段
        # if self.verbose >= VERBOSE_MINIMAL:
        #     print(f"\n🔧 AttentionAgent进行自我纠错...")


        # attention_session_id = self.attention_agent.start_new_session()
        #  # 保存session_id供后续testcase分析使用
        # self.stage0_attention_session_id = attention_session_id
        # self_correction_result = self.attention_agent.self_correction(
        #     problem_description=problem_description,
        #     sample_io=sample_io or [],
        #     fatal_points=fatal_points,
        #     recheck=recheck,
        #     session_id=attention_session_id
        # )
        
        # # 使用纠错后的结果
        # final_fatal_points = self_correction_result.get("fatal_points", fatal_points)
        # final_recheck = self_correction_result.get("recheck", recheck)
        
        # if self.verbose >= VERBOSE_MINIMAL:
        #     print(f"\n🔍 AttentionAgent自我纠错后的结果:")
        #     print(f"   关键点: {final_fatal_points}")
        #     if final_recheck:
        #         print(f"   复查内容: {final_recheck}")
        
        # 计算执行时间
        elapsed_time = time.time() - start_time
        
        # 返回AttentionAgent的分析结果
        return {
            "fatal_points": fatal_points,
            "recheck": recheck,
            "raw_response": attention_result.get("raw_response", ""),
            "analysis_time": elapsed_time
        }
        
        # CTO审查阶段：逐个检查sample IO，验证分析是否正确
        if sample_io:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n🔍 CTO审查阶段：验证分析是否符合Sample IO...")
            
            reviewed_points = self._cto_review_attention_analysis(
                problem_description=problem_description,
                attention_analysis=fatal_points,
                sample_io=sample_io
            )
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n🔍 CTO审查后的关键点:")
                print(f"   {reviewed_points}")
            
            fatal_points = reviewed_points
        
        elapsed_time = time.time() - start_time
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n重点分析完成，耗时: {elapsed_time:.2f}秒")
            print(f"{'='*50}\n")
        
        return {
            "fatal_points": fatal_points,
        }
    
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n重点分析完成，耗时: {elapsed_time:.2f}秒")
            print(f"{'='*50}\n")
        
        return {
            "fatal_points": fatal_points,
        }


    def _generate_code(self, problem_description, test_cases, parsed_assertions, thought_content, technical_plan, problem_sample_io, attention_analysis: Dict[str, Any] = None, stage_error_analysis: Dict[str, Any] = None, error_code: str = None, error_info: str = None, item: Dict[str, Any] = None):
        """
        阶段三: 生成代码
        
        Args:
            problem_description: 问题描述
            test_cases: 测试用例
            technical_plan: 技术方案
            problem_sample_io: 样例输入输出
            attention_analysis: 阶段零的重点分析结果
            
        Returns:
            生成的代码
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n=== 阶段3: 生成代码 ===")

         # 重新提取fatal_points用于solution planning阶段
        fatal_points_str = 'N/A'
        if attention_analysis:
            if isinstance(attention_analysis, dict):
                fatal_points_str = attention_analysis.get('raw_response', 'N/A')
            else:
                fatal_points_str = str(attention_analysis)
        attention_dict = {"fatal_points": fatal_points_str} if fatal_points_str != 'N/A' else None

        # 使用代码生成智能体生成代码
        code_session_id = self.code_agent.start_new_session()
        code_result = self.code_agent.generate_code(
            problem_description=problem_description,
            test_cases=test_cases,
            technical_plan=technical_plan,
            language=self.language,
            problem_sample_io=problem_sample_io,
            attention_analysis=attention_dict,
            error_code=error_code,
            error_info=error_info,
            session_id=code_session_id
        )
        print("code_result:\n\n", code_result,"\n\n")
        
        # 获取生成的代码和会话ID
        generated_code = code_result.get("code", "")
        
        # 使用语法检查器检查代码（仅针对 Python 语言）
        grammar_summary = None
        if isinstance(self.language, str) and self.language.lower().startswith("python"):
            if self.verbose >= VERBOSE_MINIMAL:
                print("\n🧹 运行语法检查器 (pyflakes)...")

            grammar_context = {
                "problem_description": problem_description,
                "test_cases": problem_sample_io if isinstance(problem_sample_io, list) else [],
            }

            try:
                grammar_result = self.grammar_checker.ensure_clean(
                    generated_code,
                    context=grammar_context,
                )
            except RuntimeError as exc:
                grammar_summary = {
                    "success": False,
                    "fixed": False,
                    "attempts": 0,
                    "report": str(exc),
                    "issues": [],
                    "history": [],
                    "error": str(exc),
                }
                code_result["grammar_check"] = grammar_summary
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"语法检查器不可用: {exc}")
            else:
                def _issue_to_dict(issue):
                    return {
                        "line": issue.line,
                        "column": issue.column,
                        "message": issue.message,
                        "raw": issue.raw,
                    }

                grammar_summary = {
                    "success": grammar_result.success,
                    "fixed": grammar_result.fixed,
                    "attempts": grammar_result.attempts,
                    "report": grammar_result.report,
                    "issues": [_issue_to_dict(it) for it in grammar_result.issues],
                    "history": grammar_result.history,
                }

                generated_code = grammar_result.code
                code_result["code"] = generated_code
                code_result["grammar_check"] = grammar_summary

                if self.verbose >= VERBOSE_MINIMAL:
                    status = "通过" if grammar_result.success else "失败"
                    print(f"语法检查结果: {status}")
                    if not grammar_result.success and grammar_result.issues:
                        for issue in grammar_result.issues[:5]:
                            loc = f"行 {issue.line}" if issue.line else "未知位置"
                            print(f"  - {loc}: {issue.message}")

        code_session_id = code_result.get("session_id")       

        print(f"final generated_code:\n\n{generated_code}\n\n")

        # 处理sample_io，确保它是一个列表
        sample_io_list = None
        if problem_sample_io and isinstance(problem_sample_io, list):
            sample_io_list = problem_sample_io
        elif problem_sample_io and isinstance(problem_sample_io, str):
            sample_io_list = problem_sample_io.strip().split("\n")
        
        # 打印sample_io信息
        if self.verbose >= VERBOSE_MINIMAL:
            print("\nSample I/O tests:")
            if sample_io_list:
                for i, test in enumerate(sample_io_list):
                    print(f"  Test {i+1}: {test}")
            else:
                print("  No sample I/O tests available")
        
        # 如果没有sample_io，直接返回代码
        if not sample_io_list:
            if self.verbose >= VERBOSE_MINIMAL:
                print("\nNo sample I/O tests available. Skipping testing phase.")
            code_result["success"] = True
            code_result["attempts"] = 0
            return code_result
        
        # 根据数据集类型选择测试方式
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n=== 第一层测试: Sample I/O ===")
        
        if self.is_competitive and item:
            # APPS: 使用 ExecEval 测试（input/output 格式）
            if self.verbose >= VERBOSE_MINIMAL:
                print("使用 ExecEval 测试 APPS 代码...")
            
            sample_io_passed, test_log = self.dataset.evaluate_sample_io(
                item=item,
                code=generated_code,
                language=self.language
            )
            
            # 构建与 DebugAgent 兼容的结果格式
            sample_io_result = {
                "success": sample_io_passed,
                "output": test_log,
                "error": "" if sample_io_passed else test_log,
                "error_type": None if sample_io_passed else "ExecEval",
                "failed_tests": [] if sample_io_passed else [{"test": "APPS test", "error": test_log}]
            }
        else:
            # HumanEval/MBPP: 使用 DebugAgent 本地测试（assert 语句）
            if self.verbose >= VERBOSE_MINIMAL:
                print("使用本地执行测试代码...")
            
            sample_io_result = self.debug_agent.test_with_sample_io(
                code=generated_code,
                sample_io=sample_io_list,
                timeout=10
            )
            sample_io_passed = sample_io_result["success"]
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"Sample I/O 测试结果: {'通过' if sample_io_passed else '失败'}")
        
        # 第二层测试：测试parsed assertions (如果有的话)
        testcase_passed = True
      
       
        discussion_validation_threshold=1.0
        # 根据测试结果决定下一步行动
        if sample_io_passed and testcase_passed:
            if self.verbose >= VERBOSE_MINIMAL:
                print("\n🎉 代码通过所有测试！")
            code_result["code"] = generated_code
            code_result["success"] = True
            code_result["attempts"] = 1
            return code_result            
        elif not sample_io_passed :
            if self.verbose >= VERBOSE_MINIMAL:
                print("\n❌ Sample I/O 测试失败，进入讨论...")
            test_cases_for_discussion = problem_sample_io
            failed_tests = sample_io_result.get('failed_tests', [])
            discussion_topic = "Fix code to pass failing Sample I/O"
            discussion_validation_threshold = 1.0  # 100%验证
       
        
        # 启动多智能体调试机制
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"Failed tests: {len(failed_tests)}")
            print("\n🔧 启动多智能体调试系统...")

        from utils.dialogue import MultiAgentDebugger
        
        # 创建多智能体调试器（使用与workflow相同的模型）
        debugger = MultiAgentDebugger(model=self.model, verbose=self.verbose)
        if self.is_competitive:
            error_logs = failed_tests[0].get('error')
        else:
            # 构建错误日志
            error_logs = "\n".join([f"Test failed: {ft.get('error', 'Unknown error')}" for ft in failed_tests])
        
        # 使用多智能体调试器修复代码
        debug_result = debugger.debug_problem(
            problem_description=problem_description,
            current_code=generated_code,
            test_cases=test_cases_for_discussion,
            error_logs=error_logs,
            attention_analysis=attention_dict,
            init_code=error_code,
            is_competive=self.is_competitive,
            item=item,
            dataset=self.dataset
        )
        
        # 处理调试结果
        if debug_result["success"]:
            if self.verbose >= VERBOSE_MINIMAL:
                print("✅ 多智能体调试器成功修复代码!")
            extracted_code = debug_result["final_code"]
        else:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"❌ 多智能体调试器修复失败: {debug_result.get('error', 'Unknown error')}")
            extracted_code = generated_code  # 使用原始代码
        code_result["code"] = extracted_code
        code_result["attempts"] = 1
        code_result["failed_sample_io"] = sample_io_result if not sample_io_passed else "N/A"
        if debug_result.get("success"):
            code_result["debug_enhanced"] = True
            code_result["debug_history"] = debug_result.get("execution_history", [])
        return code_result
    

    def _generate_init_code(self, problem_description, problem_sample_io, item: Dict[str, Any] = None):
        """
        阶段三: 生成代码
        
        Args:
            problem_description: 问题描述
            test_cases: 测试用例
            problem_sample_io: 样例输入输出
            item: 数据项（用于 APPS 等竞赛型数据集的 ExecEval 评估）
            
        Returns:
            生成的代码
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n=== 阶段3: 生成代码 ===")


        # 使用代码生成智能体生成代码
        code_session_id = self.code_agent.start_new_session()
        code_result = self.code_agent.generate_init_code(
            problem_description=problem_description,
            language=self.language,
            problem_sample_io=problem_sample_io,
            session_id=code_session_id
        )
        print("code_result:\n\n", code_result,"\n\n")
        
        # 获取生成的代码和会话ID
        generated_code = code_result.get("code", "")
        
        # 使用语法检查器检查代码（仅针对 Python 语言）
        grammar_summary = None
        if isinstance(self.language, str) and self.language.lower().startswith("python"):
            if self.verbose >= VERBOSE_MINIMAL:
                print("\n🧹 运行语法检查器 (pyflakes)...")

            grammar_context = {
                "problem_description": problem_description,
                "test_cases": problem_sample_io if isinstance(problem_sample_io, list) else [],
            }

            try:
                grammar_result = self.grammar_checker.ensure_clean(
                    generated_code,
                    context=grammar_context,
                )
            except RuntimeError as exc:
                grammar_summary = {
                    "success": False,
                    "fixed": False,
                    "attempts": 0,
                    "report": str(exc),
                    "issues": [],
                    "history": [],
                    "error": str(exc),
                }
                code_result["grammar_check"] = grammar_summary
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"语法检查器不可用: {exc}")
            else:
                def _issue_to_dict(issue):
                    return {
                        "line": issue.line,
                        "column": issue.column,
                        "message": issue.message,
                        "raw": issue.raw,
                    }

                grammar_summary = {
                    "success": grammar_result.success,
                    "fixed": grammar_result.fixed,
                    "attempts": grammar_result.attempts,
                    "report": grammar_result.report,
                    "issues": [_issue_to_dict(it) for it in grammar_result.issues],
                    "history": grammar_result.history,
                }

                generated_code = grammar_result.code
                code_result["code"] = generated_code
                code_result["grammar_check"] = grammar_summary

                if self.verbose >= VERBOSE_MINIMAL:
                    status = "通过" if grammar_result.success else "失败"
                    print(f"语法检查结果: {status}")
                    if not grammar_result.success and grammar_result.issues:
                        for issue in grammar_result.issues[:5]:
                            loc = f"行 {issue.line}" if issue.line else "未知位置"
                            print(f"  - {loc}: {issue.message}")

        code_session_id = code_result.get("session_id")
       
        print(f"final generated_code:\n\n{generated_code}\n\n")

        # 处理sample_io，确保它是一个列表
        sample_io_list = None
        if problem_sample_io and isinstance(problem_sample_io, list):
            sample_io_list = problem_sample_io
        elif problem_sample_io and isinstance(problem_sample_io, str):
            sample_io_list = problem_sample_io.strip().split("\n")
        
        # 打印sample_io信息
        if self.verbose >= VERBOSE_MINIMAL:
            print("\nSample I/O tests:")
            if sample_io_list:
                for i, test in enumerate(sample_io_list):
                    print(f"  Test {i+1}: {test}")
            else:
                print("  No sample I/O tests available")
        
        # 如果没有sample_io，直接返回代码
        if not sample_io_list:
            if self.verbose >= VERBOSE_MINIMAL:
                print("\nNo sample I/O tests available. Skipping testing phase.")
            code_result["success"] = True
            code_result["attempts"] = 0
            return code_result
        
        # 根据数据集类型选择测试方式
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n=== 第一层测试: Sample I/O ===")
        
        if self.is_competitive and item:
            # APPS: 使用 ExecEval 测试（input/output 格式）
            if self.verbose >= VERBOSE_MINIMAL:
                print("使用 ExecEval 测试 APPS 代码...")
            
            sample_io_passed, test_log = self.dataset.evaluate_sample_io(
                item=item,
                code=generated_code,
                language=self.language
            )
            
            # 构建与 DebugAgent 兼容的结果格式
            sample_io_result = {
                "success": sample_io_passed,
                "output": test_log,
                "error": "" if sample_io_passed else test_log,
                "error_type": None if sample_io_passed else "ExecEval",
                "failed_tests": [] if sample_io_passed else [{"test": "APPS test", "error": test_log}]
            }
        else:
            # HumanEval/MBPP: 使用 DebugAgent 本地测试（assert 语句）
            if self.verbose >= VERBOSE_MINIMAL:
                print("使用本地执行测试代码...")
            
            sample_io_result = self.debug_agent.test_with_sample_io(
                code=generated_code,
                sample_io=sample_io_list,
                timeout=10
            )
            sample_io_passed = sample_io_result["success"]
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"Sample I/O 测试结果: {'通过' if sample_io_passed else '失败'}")
        
        # 第二层测试：测试parsed assertions (如果有的话)
        testcase_passed = True
      
       
        discussion_validation_threshold=1.0
        # 根据测试结果决定下一步行动
        if sample_io_passed:
            if self.verbose >= VERBOSE_MINIMAL:
                print("\n🎉 代码通过所有测试！")
            code_result["code"] = generated_code
            code_result["success"] = True
            code_result["attempts"] = 1
            return code_result            
        elif not sample_io_passed :
            code_result["code"] = generated_code
            code_result["success"] = False
            code_result["error"]=sample_io_result.get('failed_tests', [])
            return code_result
       
        
        
        return code_result

 