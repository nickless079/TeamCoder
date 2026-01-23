"""
SelfPlanning Workflow
两步走：1. Planning (生成解决步骤) 2. Implementation (根据步骤生成代码)
"""

from typing import Dict, Any, Optional
import time

from .BaseWorkflow import BaseWorkflow
from models.Base import BaseModel
from datasets.Dataset import Dataset
from utils.results import Results
from agents.core.CodeAgent import CodeAgent
from prompts.selfplanning import code as selfplanning_prompts
from constants.verboseType import *


class SelfPlanningWorkflow(BaseWorkflow):
    """
    SelfPlanning 工作流
    先让模型规划解决步骤，再根据步骤生成代码
    """
    
    def __init__(
        self,
        model: BaseModel,
        dataset: Dataset,
        language: str,
        pass_at_k: int = 1,
        results: Results = None,
        verbose: int = 1,
        web_search: bool = False,
        docker_execution: bool = False,
        start_index: int = 0,
    ):
        super().__init__(
            model=model,
            dataset=dataset,
            language=language,
            pass_at_k=pass_at_k,
            results=results,
            verbose=verbose,
            web_search=web_search,
            docker_execution=docker_execution,
            start_index=start_index,
        )
        
        # 获取数据集类型
        self.dataset_type = self._get_dataset_type()
        
        # 初始化 CodeAgent（复用现有的 Agent）
        self._init_agents()
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*60}")
            print(f"SelfPlanning Workflow 初始化完成")
            print(f"数据集: {self.dataset_type}")
            print(f"语言: {self.language}")
            print(f"Pass@K: {self.pass_at_k}")
            print(f"{'='*60}\n")
    
    def _init_agents(self):
        """初始化 Agent（复用现有的 CodeAgent）"""
        self.code_agent = CodeAgent(
            model=self.model,
            verbose=self.verbose
        )
    
    def _get_dataset_type(self) -> str:
        """获取数据集类型"""
        dataset_class_name = self.dataset.__class__.__name__
        
        if "HumanEval" in dataset_class_name or "Human" in dataset_class_name:
            return "HumanEval"
        elif "APPS" in dataset_class_name:
            return "APPS"
        elif "XCode" in dataset_class_name:
            return "XCodeEval"
        elif "CodeContest" in dataset_class_name:
            return "CodeContest"
        elif "MBPP" in dataset_class_name:
            return "HumanEval"
        else:
            return "HumanEval"
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个问题
        
        Args:
            item: 数据项
            
        Returns:
            处理结果（与 TeamCoderWorkflowV1 格式一致）
        """
        import time
        start_time = time.time()
        
        # 开始 token 计数
        self.model.start_token_count()
        
        problem_id = item.get(self.dataset.id_key, "unknown")
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*60}")
            print(f"处理问题: {problem_id}")
            print(f"{'='*60}")
        
        # 初始化结果
        passed = False
        pass_rate = 0.0
        generated_code = ""
        attempts = 0
        
        # Pass@K: 尝试生成 K 次
        for attempt in range(self.pass_at_k):
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n尝试 {attempt + 1}/{self.pass_at_k}...")
            
            try:
                # 使用 Agent 生成代码（两步：planning + implementation）
                code_result = self._generate_code(item)
                code = code_result.get("code", "")
                generated_code = code  # 保存最后一次生成的代码
                attempts += 1
                
                if self.verbose >= VERBOSE_FULL:
                    print(f"\n生成的代码:\n{code}\n")
                
                # 使用与 TeamCoderWorkflowV1 相同的评估方式
                from evaluations.pass_at_k import evaluate_humaneval_problem, evaluate_mbpp_problem
                
                # 选择合适的评估函数
                dataset_type = self.dataset.__class__.__name__.lower()
                if "humaneval" in dataset_type:
                    evaluate_fn = evaluate_humaneval_problem
                elif "mbpp" in dataset_type:
                    evaluate_fn = evaluate_mbpp_problem
                else:
                    evaluate_fn = evaluate_humaneval_problem
                
                # 使用pass@k评估（k=1）
                eval_result = evaluate_fn(
                    problem=item,
                    solutions=[code],
                    timeout=5
                )
                
                # 解析结果
                is_correct = len(eval_result.get("correct", [])) > 0
                pass_rate = eval_result.get("pass_rate", 0.0)
                
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"评估结果: {'通过' if is_correct else '失败'}")
                    print(f"通过率: {pass_rate:.2%}")
                    
                    # 如果有错误信息，显示第一个错误
                    errors = eval_result.get("errors", [])
                    if errors and self.verbose >= VERBOSE_FULL:
                        print(f"错误信息: {errors[0][1]}")
                
                if is_correct:
                    passed = True
                    if self.verbose >= VERBOSE_MINIMAL:
                        print(f"✅ 测试通过！")
                    break
                else:
                    if self.verbose >= VERBOSE_MINIMAL:
                        print(f"❌ 测试失败")
                        
            except Exception as e:
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"⚠️ 生成/评估出错: {e}")
                    import traceback
                    if self.verbose >= VERBOSE_FULL:
                        traceback.print_exc()
                continue
        
        # 构建结果（与 TeamCoderWorkflowV1 格式一致）
        end_time = time.time()
        total_time = end_time - start_time
        tokens_used = self.model.end_token_count()
        
        result_dict = {
            "problem_id": problem_id,
            "passed": passed,
            "pass_rate": pass_rate,
            "code": generated_code,
            "total_time": total_time,
            "tokens_used": tokens_used,
            "attempts": attempts
        }
        
        return result_dict
    
    def _generate_code(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 SelfPlanning 两步法生成代码
        
        Args:
            item: 数据项
            
        Returns:
            生成的代码结果 {"code": "...", "planning": "...", "raw_response": "..."}
        """
        # 获取问题描述
        problem = self.dataset.get_prompt(item)
        
        # Step 1: Planning - 生成解决步骤
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n📋 Step 1: Planning...")
        
        planning_messages = selfplanning_prompts.get_planning_messages(
            problem_description=problem,
            language=self.language,
            dataset_type=self.dataset_type
        )
        
        if self.verbose >= VERBOSE_FULL:
            print(f"Planning Prompt 长度: {len(planning_messages[0]['content'])} 字符")
        
        # 创建新会话用于 planning
        planning_session_id = self.code_agent.start_new_session()
        
        start_time = time.time()
        planning_response = self.code_agent._call_model(planning_messages, session_id=planning_session_id)
        planning_elapsed = time.time() - start_time
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"✓ Planning 完成 ({planning_elapsed:.2f}秒)")
            if self.verbose >= VERBOSE_FULL:
                print(f"Planning 内容:\n{planning_response[:200]}...\n")
        
        # Step 2: Implementation - 根据 planning 生成代码
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n💻 Step 2: Implementation...")
        
        implementation_messages = selfplanning_prompts.get_implementation_messages(
            problem_description=problem,
            planning=planning_response,
            language=self.language
        )
        
        if self.verbose >= VERBOSE_FULL:
            print(f"Implementation Prompt 长度: {len(implementation_messages[0]['content'])} 字符")
        
        # 创建新会话用于 implementation
        impl_session_id = self.code_agent.start_new_session()
        
        start_time = time.time()
        impl_response = self.code_agent._call_model(implementation_messages, session_id=impl_session_id)
        impl_elapsed = time.time() - start_time
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"✓ Implementation 完成 ({impl_elapsed:.2f}秒)")
            print(f"总耗时: {planning_elapsed + impl_elapsed:.2f}秒")
        
        # 使用 CodeAgent 的 _process_response 方法解析代码
        result = self.code_agent._process_response(impl_response)
        
        # 代码清理
        try:
            from utils.code_sanitizer import sanitize_code_prefix
            if "code" in result and isinstance(result["code"], str):
                result["code"] = sanitize_code_prefix(result["code"])
        except Exception:
            pass
        
        # 保存 planning 和 session 信息
        result["planning"] = planning_response
        result["planning_session_id"] = planning_session_id
        result["impl_session_id"] = impl_session_id
        
        return result
    
