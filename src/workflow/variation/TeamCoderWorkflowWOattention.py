from typing import Dict, Any, List, Optional, Tuple
import time
import json
import os
import re

from ..BaseWorkflow import BaseWorkflow
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

class TeamCoderWorkflowWOattention(BaseWorkflow):
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
    
    def _correct_failed_testcases(self, problem_description: str, failed_testcases: list, all_testcases: list,attenton_analysis: str,sample_io: list,stage=5) -> list:
        """
        使用AttentionAgent（继续阶段0的session）对失败的testcase进行改错
        
        Args:
            problem_description: 问题描述
            failed_testcases: 失败的测试用例
            all_testcases: 所有的测试用例
            
        Returns:
            改错后的测试用例列表
        """
       
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n🔧 AttentionAgent继续阶段0分析，改错{len(failed_testcases)}个失败的测试用例...")
        
        # 构建错误分析prompt（不包含代码）
        failed_test_info = []
        if stage ==1:
            failed_test_info.append("# **there is no code,the Full Evidence Pool is most wrong,please fix them according to the <FATAL_POINT_ANALYSIS>**")
        else:
            for test in failed_testcases:
                failed_test_info.append(f"失败测试: {test.get('test', '')} - 错误: {test.get('error', '')}")
        
        correction_prompt = f"""
---
# Audit and Correct Test Cases Based on a Failure

## 1. Ground Truth (The Supreme Law - Immutable)
<PROBLEM_DESCRIPTION>
{problem_description}
</PROBLEM_DESCRIPTION>
<SAMPLE_IO>
{sample_io}
</SAMPLE_IO>

## 2. Primary Evidence: The Failure (Your Starting Point)
This is the most critical piece of evidence. Your investigation must start here.
<FAILED_TESTS>
{chr(10).join(failed_test_info)}
</FAILED_TESTS>

## 3. Secondary Clue: The Initial Analysis
This is a hypothesis from a previous agent. It may be helpful, but it can be wrong and must be validated against the failure.
<FATAL_POINT_ANALYSIS>
{attenton_analysis}
</FATAL_POINT_ANALYSIS>

## 4. Full Evidence Pool (To be Audited)
{chr(10).join(all_testcases)}

## Your Mission: From Failure, Deduce Truth, and Correct All Tests.

You must follow a rigorous, non-negotiable auditing protocol.

## Output (exactly TWO parts in order)

### Part 1: <thought> Block
Your auditing process MUST follow these explicit steps:
1.  **Analyze the Failure**: Look at the `FAILED_TESTS`. For one of the failures, identify the `input`, the `code's_actual_output`, and the `test's_expected_output`.
2.  **Establish the 'Rule of Truth' via Cross-Examination**: Now, you must determine who is correct: the code, or the test's expectation.
    a.  First, based **ONLY** on the **Supreme Law** (`PROBLEM_DESCRIPTION` and `SAMPLE_IO`), **manually calculate** what the **True Expected Output** for the failing input *should* be. **You must show your step-by-step reasoning based on the problem's definition.**
    b.  **Compare**: Is your calculated `True Expected Output` the same as the `code's_actual_output` or the `test's_expected_output`?
    c.  **Verdict**: Based on the comparison, state the single, correct 'Rule of Truth'. This rule must explain both the `Sample I/O` and why the test failed. *(e.g., "The Rule of Truth is that GPA checks must be `>`. The code's output of 'D' for input `1.0` was correct. The test's expectation of 'D+' was therefore FLAWED.")*
3.  **Audit ALL Test Cases Against the 'Rule of Truth'**: Now that you have the confirmed 'Rule of Truth', systematically apply it to **EVERY** test case in the `Full Evidence Pool`. For each one, state if it's CORRECT or if it's FLAWED and needs correction.
4.  **Final Conclusion**: Summarize which test cases are being corrected to align with the 'Rule of Truth'.

### Part 2: <corrected_tests> Block
List ALL test cases here. This includes all originally correct test cases from the pool plus the ones you have corrected based on your 'Rule of Truth'.
the format is
[
    "assert func(args) == expected_output",
    "assert func(args) == expected_output",
    ...
]
...
</corrected_tests>
"""
        
        try:
            # 使用阶段0的session_id继续对话
            messages = [
                {"role": "user", "content": correction_prompt}
            ]
            
            response = self.attention_agent._call_model(messages, session_id=self.stage0_attention_session_id)

           
            # 解析响应，提取改正后的测试用例
            import re
            corrected_testcases = []
            
            # 尝试从<corrected_tests>标签中提取
            tests_match = re.search(r'<corrected_tests>(.*?)</corrected_tests>', response, re.DOTALL | re.IGNORECASE)
            if tests_match:
                tests_content = tests_match.group(1).strip()
                
                # 尝试解析JSON格式
                try:
                    import json
                    # 清理JSON内容，移除可能的markdown代码块标记
                    json_content = tests_content
                    if json_content.startswith('```') and json_content.endswith('```'):
                        json_content = json_content[3:-3].strip()
                    if json_content.startswith('json'):
                        json_content = json_content[4:].strip()
                    
                    test_list = json.loads(json_content)
                    if isinstance(test_list, list):
                        corrected_testcases = test_list
                    else:
                        raise ValueError("JSON内容不是列表格式")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    # JSON解析失败，尝试按行解析
                    if self.verbose >= VERBOSE_MINIMAL:
                        print(f"JSON解析失败: {e}，尝试按行解析")
                    lines = tests_content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and line.startswith('assert'):
                            corrected_testcases.append(line)
            else:
                # 备用解析：直接从整个响应中提取assert语句
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and line.startswith('assert'):
                        corrected_testcases.append(line)
            
            if not corrected_testcases:
                # 如果没有解析到有效的测试用例，返回原始测试用例
                if self.verbose >= VERBOSE_MINIMAL:
                    print("⚠️ 未能解析到有效的改正结果，使用原始测试用例")
                return all_testcases
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"✅ 成功改错，得到{len(corrected_testcases)}个测试用例")
                
            return corrected_testcases
            
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"❌ 测试用例改错失败: {e}，使用原始测试用例")
            return all_testcases
    
    import json
    import re
    from typing import List, Dict, Any

    def _route_problem_complexity(
        self,
        problem_description: str,
        problem_sample_io: List[Dict[str, Any]]
    ) -> bool:
        """
        路由函数：判断问题是否可以直接生成代码

        通过分析问题描述和样例IO，判断问题复杂度：
        - True: 简单问题 (Simple)，可尝试直接生成代码
        - False: 复杂问题 (Complex)，必须走完整的规划-测试-编码流程

        Args:
            problem_description: 问题描述
            problem_sample_io: 样例输入输出

        Returns:
            bool: True表示简单问题，False表示复杂问题
        """
        
        # 注意：在f-string中，JSON的左右大括号需要转义为 {{ 和 }}
        router_prompt = f"""
Role: Algorithm Complexity Classifier

Task:
Analyze the provided Python coding problem (description, function signature, and sample input/output) and classify it into one of two categories: "Simple" or "Complex".

Definitions:

1. [Simple]:
   - logic is linear and straightforward.
   - Can be solved with standard Python built-ins (e.g., list slicing, basic loops, string methods, set/dict lookups) without complex state management.
   - No complex mathematical derivations or specific algorithmic patterns (like DP, DFS/BFS) are needed.
   - Direct translation of the requirement into code.

2. [Complex] (The "Safe" Mode):
   - Requires ANY mathematical reasoning (geometry, number theory, polynomial evaluation, finding roots).
   - Requires specific algorithms (Binary Search, Two Pointers, Sliding Window, Recursion, Dynamic Programming, Graph/Tree traversal).
   - Requires handling tricky edge cases or specific conditional logic that deviates from standard behavior (e.g., "if X > Y, do a completely different logic Z").
   - Multi-step logical reasoning where step B depends on the complex result of step A.

Calibration Examples (Threshold for "Complex"):
- Example A: "Circular shift digits. IF shift > num_digits, return reversed digits." -> Classify as COMPLEX. (Reason: The specific conditional override makes it error-prone for simple direct generation).
- Example B: "Find zero of a polynomial." -> Classify as COMPLEX. (Reason: Requires mathematical implementation/numerical methods).
- Example C: "Return the sum of a list." -> Classify as SIMPLE.
- Example D: "Check if a string is a palindrome." -> Classify as SIMPLE.

Input Format:
This will provide the `problem_description` and `sample_io`.
---
Problem:
{problem_description}

Sample IO:
{problem_sample_io}
---

Output Format:
Return a single JSON object (no markdown, no extra text):
{{
    "category": "Simple" | "Complex",
    "reason": "Brief explanation < 20 words"
}}
"""

        messages = [
            {"role": "user", "content": router_prompt}
        ]

        try:
            # 1. 调用模型
            router_session = self.cto_agent.start_new_session()
            response = self.cto_agent._call_model(messages, session_id=router_session)
            
            # 2. 清洗响应内容 (去除可能存在的 Markdown 代码块标记)
            content = response.strip()
            if "```" in content:
                # 使用正则提取 ```json ... ``` 或 ``` ... ``` 中间的内容
                match = re.search(r"```(?:json)?\s*(.*)\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1)
            
            # 3. 解析 JSON
            try:
                data = json.loads(content)
                category = data.get("category", "Complex") # 默认 Complex
                reason = data.get("reason", "No reason provided")
            except json.JSONDecodeError:
                # 如果 JSON 解析彻底失败，记录并启用安全模式
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"\n⚠️ Router JSON Decode Error. Raw response: {content[:50]}...")
                return False  # Default to Complex

            # 4. 做出决策
            # 只有明确标记为 "Simple" 时才返回 True
            if category.lower() == "simple":
                decision = True
                log_tag = "SIMPLE (Direct Gen)"
            else:
                decision = False
                log_tag = "COMPLEX (Full Workflow)"

            # 5. 日志输出
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n🧭 Router Decision: {log_tag}")
                if self.verbose >= VERBOSE_FULL:
                    print(f"   Reason: {reason}")

            return decision

        except Exception as e:
            # 6. 异常处理：任何环节出错，都默认走复杂流程（安全兜底）
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n⚠️ Router System Error: {e}, defaulting to COMPLEX workflow")
            return False
        
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
        
        # use_direct = self._route_problem_complexity(
        #     problem_description=problem_description,
        #     problem_sample_io=problem_sample_io
        # )
        code_result = {}
        #if use_direct: 
        code_result = self._generate_init_code(problem_description, problem_sample_io=problem_sample_io, item=item)
        generated_code = "" # code_result.get("success", False) is False
        if code_result.get("success", False) is False:
            print(f"❌ 初始化代码生成失败: {code_result.get('error', '')}")
            error_code = code_result.get("code", "")

            error_info = code_result.get("error","")

            # 阶段零: 重点分析 - 找出最容易被忽视的致命关键点
            #attention_analysis = self._analyze_critical_points(problem_description, problem_sample_io,error_code,error_info)
            attention_analysis={
            "fatal_points": "none",
            "recheck": "none",
            "raw_response": "none",
            "analysis_time": "none"
            }

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

    def _analyze_critical_points_1(self, problem_description: str, sample_io: List[str] = None, error_code: str = "", error_info: List[str] = None) -> Dict[str, Any]:
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
        none_sample_io = False
        if len(sample_io) == 0 :
            sample_io = ["attention this problem has no sample io,so you must read the problem description carefully"]
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print("阶段零: 重点分析 - 寻找最容易被忽视的致命关键点")
            print(f"{'='*50}")
        attention_session_id = self.attention_agent.start_new_session()
        self.stage0_attention_session_id = attention_session_id  # 保存session_id供后续testcase分析使用
        
        # Stage 0.1: Analyze the blueprint to find fatal traps.
        if self.verbose >= VERBOSE_MINIMAL:
            print("\nStage 0.1: Analyzing blueprint for fatal traps...")

        blueprint_result_str=""
        attention_result = self.attention_agent.analyze_traps(
            problem_blueprint_json=blueprint_result_str or "",
            problem_description=problem_description,
            sample_io=sample_io or [],
            error_code=error_code,
            error_info=error_info or [],
            session_id=attention_session_id
        )
        print(f"\n🔍 AttentionAgent分析结果 (raw):\n{attention_result}\n")
        
        # 处理分析结果
        fatal_points = attention_result.get("fatal_points", "")
        recheck = attention_result.get("recheck", "")
        trap = attention_result.get("raw_response", "")

        # Stage 0.2: Generate a structured blueprint of the problem.
        if self.verbose >= VERBOSE_MINIMAL:
            print("\nStage 0.2: Generating problem blueprint...")
        blueprint_result = self.attention_agent.generate_blueprint(
            problem_description=problem_description,
            sample_io=sample_io or [],
            error_code=error_code,
            error_info=error_info or [],
            trap=trap,
            session_id=attention_session_id
        )
        
        import json
        print(f"\n🔧 Blueprint generation result (raw):\n{blueprint_result}\n")
        def extract_summary_rule(blueprint_result):
            # 尝试从blueprint_json提取（即使为空也不会报错）
            if 'blueprint_json' in blueprint_result and blueprint_result['blueprint_json']:
                try:
                    return blueprint_result['blueprint_json']['summary-rule']
                except KeyError:
                    pass  # 继续尝试其他路径
                
            # 从raw_response提取（处理为空或解析失败的情况）
            if 'raw_response' in blueprint_result:
                print("尝试从raw_response中提取summary-rule...")
                try:
                    
                    raw_dict =json.loads(blueprint_result['raw_response'])
                    print(f"解析后的raw_response内容: {raw_dict}")
                    return raw_dict['summary-rule']
                except (json.JSONDecodeError, KeyError):
                    return blueprint_result['raw_response']
                
            # 所有路径失败时返回None
            return None

        blueprint_result_str = json.dumps(blueprint_result.get("raw_response", {}))
        # 提取并打印结果
        summary_rule = extract_summary_rule(blueprint_result)

        print(f"summary_rule: {summary_rule}")

  
        attention_result["raw_response"] = {"Rules": summary_rule, "Traps": attention_result.get("raw_response", "")}

        
        if none_sample_io:
            sample_io = []

        # 计算执行时间
        elapsed_time = time.time() - start_time
        
        # 返回AttentionAgent的分析结果
        return {
            "fatal_points": fatal_points,
            "recheck": recheck,
            "raw_response": attention_result.get("raw_response", ""),
            "analysis_time": elapsed_time
        }
        
        
  

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
    
    def _cto_review_attention_analysis(self, problem_description: str, attention_analysis: str, sample_io: List[str]) -> str:
        """
        CTO审查AttentionAgent的分析，逐个检查sample IO验证分析是否正确
        
        Args:
            problem_description: 问题描述
            attention_analysis: AttentionAgent的分析结果
            sample_io: 样例输入输出
            
        Returns:
            CTO审查后的修正分析
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\nCTO审查AttentionAgent分析\n{'-'*50}")
        
        # 构建CTO审查的提示
        review_prompt = f"""
As a CTO, please carefully review the attention analysis provided by the AttentionAgent against each sample I/O case.

## Problem Description
{problem_description}

## AttentionAgent's Analysis
{attention_analysis}

## Sample I/O Cases to Verify Against
{chr(10).join([f"Sample {i+1}: {io}" for i, io in enumerate(sample_io)])}

## Your Task
Please verify the AttentionAgent's analysis word by word against each sample I/O case:

1. **Examine each statement** in the analysis to ensure it accurately reflects what the sample I/O demonstrates
2. **Check each sample I/O** individually to verify if the analysis correctly identifies the critical points
3. **Identify any misunderstandings** where the analysis doesn't match what the sample I/O actually shows
4. **Correct any errors** by providing the accurate interpretation based on the sample I/O

## Requirements
- Be extremely precise and literal in your verification
- If any part of the analysis contradicts or misinterprets the sample I/O, correct it
- Focus on factual accuracy rather than general insights
- Ensure every word in your corrected analysis can be directly verified by the sample I/O


<MOCK>!!!The sample io is always correct,so you couldn't doubt the sample io!!!Simulate whether each sample input/output (sampleio) conforms to your new analysis. Particularly focus on simulating some special sampleio cases. If a sampleio passes the simulation, include it in your new analysis; if it fails, document the reasons for the failure.
</MOCK>
Please return only in this **format** use <CORRECTED_ANALYSIS> and </CORRECTED_ANALYSIS>:
<CORRECTED_ANALYSIS>
Write down the correct critical flaws here, preferably with complex examples for explanation—avoid making them overly simplistic.
</CORRECTED_ANALYSIS>
"""
        
        # 使用CTO Agent进行审查
        try:
            messages = [
                {"role": "system", "content": "You are a CTO responsible for ensuring technical accuracy. Your task is to verify and correct analysis against concrete sample data."},
                {"role": "user", "content": review_prompt}
            ]
            
            # 创建新的session用于阶段0的CTO检查
            stage0_cto_session = self.cto_agent.start_new_session()
            cto_response = self.cto_agent._call_model(messages, session_id=stage0_cto_session)
            
            # 保存session ID供后续使用
            self.stage0_cto_session_id = stage0_cto_session
            
            # 提取修正后的分析
            import re
            corrected_match = re.search(r'<CORRECTED_ANALYSIS>\s*(.*?)\s*</CORRECTED_ANALYSIS>', cto_response, re.DOTALL | re.IGNORECASE)
            
            if corrected_match:
                corrected_analysis = corrected_match.group(1).strip()
                if self.verbose >= VERBOSE_FULL:
                    print(f"CTO审查完成，原分析长度: {len(attention_analysis)}, 修正后长度: {len(corrected_analysis)}")
                return corrected_analysis
            else:
                if self.verbose >= VERBOSE_MINIMAL:
                    print("CTO审查未返回格式化结果，使用原分析")
                return attention_analysis
                
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"CTO审查过程出错: {e}，使用原分析")
            return attention_analysis
    
    def _final_fatal_check(self, code: str, problem_description: str, session_id: str) -> str:
        """
        最终致命检查：结合阶段0的分析检查代码中的致命问题
        
        Args:
            code: 要检查的代码
            problem_description: 问题描述
            session_id: 阶段0的CTO session ID
            
        Returns:
            检查并可能修正后的代码
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\n最终致命检查：结合阶段0分析检查代码\n{'-'*50}")
        
        # 构建简洁的检查提示
        check_prompt = f"""
结合你之前的分析，仔细查看以下代码有什么致命的、容易忽视的问题，如果有请修改。

## Problem Description
{problem_description}

## Current Code
```python
{code}
```

请仔细检查代码中是否存在与你之前分析的致命关键点相关的问题。特别是能否通过 sample。如果发现问题，请修改代码。

返回格式：
<FINAL_CODE>
修正后的完整代码（如果无需修改则返回原代码）
</FINAL_CODE>
"""
        
        try:
            # 使用阶段0的session继续对话
            self.cto_agent.set_active_session(session_id)
            messages = [
                {"role": "user", "content": check_prompt}
            ]
            
            cto_response = self.cto_agent._call_model(messages, session_id=session_id, include_history=True)
            
            # 提取最终代码
            import re
            code_match = re.search(r'<FINAL_CODE>\s*(.*?)\s*</FINAL_CODE>', cto_response, re.DOTALL | re.IGNORECASE)
            
            if code_match:
                final_code = code_match.group(1).strip()
                if self.verbose >= VERBOSE_FULL:
                    print(f"最终检查完成，原代码长度: {len(code)}, 检查后长度: {len(final_code)}")
                return final_code
            else:
                if self.verbose >= VERBOSE_MINIMAL:
                    print("最终检查未返回格式化代码，使用原代码")
                return code
                
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"最终检查过程出错: {e}，使用原代码")
            return code
     
   
    
    def _generate_test_cases(self, problem_description: str, sample_io: List[str] = None, attention_analysis: Dict[str, Any] = None, stage_error_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        阶段一: CTO监督的测试用例协作生成
        
        Args:
            problem_description: 问题描述
            sample_io: 样例输入输出
            attention_analysis: 阶段零的重点分析结果
            
        Returns:
            生成的测试用例
        """
        start_time = time.time()
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\n阶段一: CTO监督的测试用例协作生成\n{'-'*50}")
        

        # 使用综合测试智能体生成测试用例
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n使用综合测试智能体生成测试用例")
        test_session_id = self.test_agent.start_new_session()
       
        
        test_cases = self.test_agent.generate_test_cases(problem_description, sample_io=sample_io or [])
        
        # 解析TestAgent返回：thought与结构化测试用例
        test_propose = ""

        if isinstance(test_cases, dict):
            test_propose = test_cases.get("input", "")
            
        
        print(f"\n\n综合测试用例\n\n: {test_cases}")

        attention_dict_str = attention_analysis.get("raw_response", "") if attention_analysis else ""
        attention_analysis = {"attention_analysis": attention_dict_str} if attention_dict_str else None
        test_cases = self.test_agent.evaluate_single_test(problem_description,assertion=test_propose,sample_io=sample_io,attention_analysis=attention_analysis)

                # 解析TestAgent返回：thought与结构化测试用例
        test_resolve = ""

        if isinstance(test_cases, dict):
            test_resolve = test_cases.get("assertion", "")
        print(f"\n\n综合测试用例结果\n\n: {test_resolve}")



        return test_resolve
        # 将thought包装成字典以供下游使用
        test_agent_attention = {"fatal_points": test_propose} if test_propose else None

        if self.verbose >= VERBOSE_FULL:
            print("综合测试用例(thought):", (test_agent_thought[:200] + '...') if len(test_agent_thought) > 200 else test_agent_thought)
            print("综合测试用例(structured):", test_agent_structured)
        
        # 收集测试结果
        all_test_results = [test_agent_structured]
        
        
        # # CTO总结测试用例（阶段一暂时取消，改为AttentionAgent改错方案）
        # if self.verbose >= VERBOSE_MINIMAL:
        #     print("\nCTO总结测试用例")
        # cto_session_id = self.cto_agent.start_new_session()
        # final_test_cases = self.cto_agent.summarize_test_cases(
        #     problem_description=problem_description,
        #     test_results=all_test_results,
        #     sample_io=sample_io,
        #     attention_analysis=test_agent_attention,
        #     session_id=cto_session_id
        # )
        
        # 使用AttentionAgent对阶段一生成的测试用例进行审计/改错
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n🔧 使用AttentionAgent审计/改错测试用例（阶段一）...")
        # 提取原始测试用例断言列表
        original_cases = []
        if isinstance(test_agent_structured, dict):
            items = test_agent_structured.get("test_cases", [])
            for it in items:
                if isinstance(it, dict) and it.get("assertion"):
                    original_cases.append(it["assertion"]) 
                elif isinstance(it, str) and it.strip().startswith("assert"):
                    original_cases.append(it.strip())
        
        # 仅保留前8个测试用例（若不足8个则不处理）
        if len(original_cases) > 8:
            original_cases = original_cases[:8]

        corrected_testcases = self._correct_failed_testcases(
            problem_description=problem_description,
            failed_testcases=['most is wrong,please fix them'],  # 阶段一无失败用例，也执行审计
            all_testcases=original_cases,
            attenton_analysis=attention_dict,
            sample_io=sample_io or [],
            stage=1
        )
        
        # 构建final_test_cases，保持与下游兼容
        final_test_cases = {
            "thought": test_agent_thought,
            "structured_data": {
                "test_cases": [{"assertion": s, "description": ""} for s in corrected_testcases]
            }
        }
        
        
        elapsed_time = time.time() - start_time
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n测试用例生成完成，耗时: {elapsed_time:.2f}秒")
            
            # 获取测试用例数量
            test_case_count = "未知"
            if final_test_cases.get("structured_data") and "test_cases" in final_test_cases["structured_data"]:
                test_case_count = len(final_test_cases["structured_data"]["test_cases"])
            print(f"生成的测试用例数量: {test_case_count}")
        
        return final_test_cases
    
    def _generate_test_scenarios(self, problem_description: str, problem_sample_io: List[str] = None, attention_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        阶段 1.1: 生成测试场景
        
        Args:
            problem_description: 问题描述
            problem_sample_io: 问题的样例输入输出
            attention_analysis: 阶段零的重点分析结果
            
        Returns:
            生成的测试场景
        """
        import time
        start_time = time.time()
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print("阶段 1.1: 生成测试场景")
            print(f"{'='*50}")
        
        # 提取 attention_analysis 的内容
        attention_analysis_str = ""
        if attention_analysis:
            if isinstance(attention_analysis, dict):
                # 优先使用 raw_response，其次是 fatal_points
                attention_analysis_str = attention_analysis.get('raw_response', 
                                                             attention_analysis.get('fatal_points', ''))
            else:
                attention_analysis_str = str(attention_analysis)
        
        if not attention_analysis_str:
            attention_analysis_str = "No previous analysis available"
        
        # 使用 TestAgent 的场景生成功能
        try:
            from prompts.testing.test_agent import get_scenario_generation_messages
            
            messages = get_scenario_generation_messages(
                problem_description=problem_description,
                attention_analysis=attention_analysis_str,
                problem_sample_io=problem_sample_io or []
            )
            
            # 创建新的session用于测试场景生成
            scenario_session_id = self.test_agent.start_new_session()
            response = self.test_agent._call_model(messages, session_id=scenario_session_id)
            
            # 解析响应中的JSON
            import re
            import json
            
            # 尝试提取JSON块
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
            if not json_match:
                json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
            
            test_scenarios = []
            if json_match:
                try:
                    json_content = json_match.group(1).strip()
                    parsed_json = json.loads(json_content)
                    test_scenarios = parsed_json.get('test_scenarios', [])
                except json.JSONDecodeError as e:
                    if self.verbose >= VERBOSE_MINIMAL:
                        print(f"JSON解析失败: {e}")
                    test_scenarios = []
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n🎯 生成的测试场景数量: {len(test_scenarios)}")
                if test_scenarios and self.verbose >= VERBOSE_FULL:
                    for i, scenario in enumerate(test_scenarios[:3]):  # 只显示前3个
                        print(f"  场景 {i+1}:")
                        print(f"    输入: {scenario.get('input', 'N/A')}")
                        print(f"    描述: {scenario.get('description', 'N/A')}")
                        if i < len(test_scenarios) - 1:
                            print()
            
            elapsed_time = time.time() - start_time
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n测试场景生成完成，耗时: {elapsed_time:.2f}秒")
                print(f"{'='*50}\n")
            
            return {
                "test_scenarios": test_scenarios,
                "raw_response": response,
                "generation_time": elapsed_time,
                "session_id": scenario_session_id
            }
            
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"❌ 测试场景生成失败: {e}")
            
            elapsed_time = time.time() - start_time
            return {
                "test_scenarios": [],
                "raw_response": "",
                "generation_time": elapsed_time,
                "error": str(e)
            }
        
    def _plan_solution(self, problem_description, test_cases, thought_content, problem_sample_io, attention_analysis: Dict[str, Any] = None, stage_error_analysis: Dict[str, Any] = None):
        """
        规划解决方案
        
        Args:
            problem_description: 问题描述
            test_cases: 测试用例
            attention_analysis: 阶段零的重点分析结果
            
        Returns:
            最终的技术方案
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n=== 阶段2: 规划解决方案 ===")
        
        
        # 第一步: 解决方案规划Agent独立生成解决方案
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n第一步: 解决方案规划Agent生成初步解决方案")
        
        if test_cases is None:
            test_cases = [('no test cases','there is no test cases,you should think the plan by yourself')]

      
        test_cases_for_plan = test_cases
        thought_content=""
        print("test_cases_for_plan:\n\n", test_cases_for_plan,"\n\n")
        
        # 重新提取fatal_points用于solution planning阶段
        fatal_points_str = 'N/A'
        if attention_analysis:
            if isinstance(attention_analysis, dict):
                fatal_points_str = attention_analysis.get('raw_response', 'N/A')
            else:
                fatal_points_str = str(attention_analysis)
        attention_dict = {"fatal_points": fatal_points_str} if fatal_points_str != 'N/A' else None
        
        solution_planning_session_id = self.solution_planning_agent.start_new_session()
        # 使用解决方案规划Agent生成初步解决方案
        initial_solutions = self.solution_planning_agent.generate_solutions(
            problem_description=problem_description,
            test_cases=test_cases_for_plan,
            thought_content=thought_content,
            problem_sample_io=problem_sample_io,
            attention_analysis=attention_dict,
            session_id=solution_planning_session_id
        )
        
        # 先获取结构化数据用于打印
        structured_data = initial_solutions.get("raw_response", {})

        
 
        return structured_data
        
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n进入CTO评审完善阶段")

        # CTO评审并完善初步方案
        final_technical_plan = self.cto_agent.review_and_refine_solution(
            problem_description=problem_description,
            initial_solutions=initial_solutions,
            test_cases=problem_sample_io,
            thought_content=thought_content,
            problem_sample_io=problem_sample_io,
            attention_analysis=attention_analysis
        )

        if self.verbose >= VERBOSE_FULL:
            print("CTO评审完善结果:")
            if final_technical_plan.get("thought"):
                print("思考过程:", final_technical_plan["thought"])
            if final_technical_plan.get("structured_data"):
                print("完善后的技术方案:", final_technical_plan["structured_data"])

        return final_technical_plan


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
        code_result["code"]=generated_code
        code_result["success"] = sample_io_passed
        return code_result   
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

    def _save_generated_code(self, test_cases, code):
        """
        保存生成的代码到文件，以便后续评估
        
        Args:
            test_cases: 测试用例
            code: 生成的代码
        """
        # 获取任务ID
        task_id = ""
        if isinstance(test_cases, dict) and "task_id" in test_cases:
            task_id = test_cases["task_id"]
        
        if not task_id:
            return
        
        # 创建保存目录
        model_dir = f"results/solutions/{self.model.model_name}"
        os.makedirs(model_dir, exist_ok=True)
        
        # 检查是否已有解决方案文件
        solution_file = f"{model_dir}/solutions.jsonl"
        
        # 准备解决方案数据
        solution_data = {
            "task_id": task_id,
            "model": self.model.model_name,
            "language": self.language,
            "timestamp": time.time(),
            "code": code
        }
        
        # 追加到文件
        with open(solution_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(solution_data) + "\n")
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n代码已保存到: {solution_file}")
            
        # 创建任务特定的目录
        task_dir = f"{model_dir}/{task_id.split('/')[0]}"  # 提取主要部分，如HumanEval
        os.makedirs(task_dir, exist_ok=True)
            
        # 同时保存到任务特定的文件
        task_file = f"{task_dir}/{task_id.split('/')[-1]}.json"  # 使用最后部分作为文件名，如0.json
        
        # 检查是否已有任务特定文件
        if os.path.exists(task_file):
            # 读取现有解决方案
            with open(task_file, "r", encoding="utf-8") as f:
                task_data = json.load(f)
                
            # 添加新解决方案
            if "solutions" in task_data:
                task_data["solutions"].append(code)
            else:
                task_data["solutions"] = [code]
        else:
            # 创建新的任务数据
            task_data = {
                "task_id": task_id,
                "model": self.model.model_name,
                "language": self.language,
                "solutions": [code]
            }
        
        # 保存任务特定文件
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=2)
            
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"任务特定代码已保存到: {task_file}")
    
    def _execute_and_verify(self, item: Dict[str, Any], code: str) -> Tuple[bool, str]:
        """
        阶段四: Docker环境的执行验证
        
        Args:
            item: 数据项
            code: 生成的代码
            
        Returns:
            (是否通过, 测试日志)
        """
        start_time = time.time()
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\n阶段四: Docker环境的执行验证\n{'-'*50}")
        
        # 第一步: 容器化执行测试
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n第一步: 容器化执行测试")
        
        if self.docker_execution:
            passed, test_log = self.docker_executor.execute(
                item,
                code,
                self.language,
                self.dataset
            )
        else:
            # 如果不使用Docker，则使用数据集的内置评估方法
            passed, test_log = self.dataset.evaluate_sample_io(
                item,
                code,
                self.language
            )
        
        # 第二步: 结果分析和迭代优化
        if self.verbose >= VERBOSE_MINIMAL:
            print("\n第二步: 结果分析和迭代优化")
            print(f"执行结果: {'通过' if passed else '失败'}")
            if not passed and self.verbose >= VERBOSE_FULL:
                print(f"测试日志:\n{test_log}")
        
        elapsed_time = time.time() - start_time
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n执行验证完成，耗时: {elapsed_time:.2f}秒")
        
        return passed, test_log