"""
CoT (Chain-of-Thought) Workflow
基于思维链推理的代码生成工作流
"""

from typing import Dict, Any, Optional
import time

from .BaseWorkflow import BaseWorkflow
from models.Base import BaseModel
from datasets.Dataset import Dataset
from utils.results import Results
from agents.core.CodeAgent import CodeAgent
from prompts.cot import code as cot_prompts
from constants.verboseType import *


class CoTWorkflow(BaseWorkflow):
    """
    CoT 工作流
    使用思维链提示，通过 few-shot examples 引导模型逐步思考并生成代码
    """
    
    def __init__(
        self,
        model: BaseModel,
        dataset: Dataset,
        language: str,
        pass_at_k: int = 1,
        results: Results = None,
        verbose: int = 1,
        web_search: bool = False,  # CoT 不需要网络搜索
        docker_execution: bool = False,  # CoT 不需要 Docker
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
            print(f"CoT Workflow 初始化完成")
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
            return "HumanEval"  # MBPP 使用类似 HumanEval 的格式
        else:
            return "HumanEval"  # 默认
    
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
                # 使用 Agent 生成代码
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
                    # 默认使用HumanEval评估函数
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
            "attempts": attempts  # CoT 特有字段，记录尝试次数
        }
        
        return result_dict
    
    def _generate_code(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 CoT prompts + CodeAgent 生成代码
        
        Args:
            item: 数据项
            
        Returns:
            生成的代码结果 {"code": "...", "raw_response": "..."}
        """
        # 获取问题描述
        problem = self.dataset.get_prompt(item)
        
        # 使用 CoT prompts 构建消息
        messages = cot_prompts.get_messages(
            problem_description=problem,
            language=self.language,
            dataset_type=self.dataset_type
        )
        
        if self.verbose >= VERBOSE_FULL:
            print(f"\nCoT Prompt 长度: {len(messages[0]['content'])} 字符")
        
        # 开始新会话
        session_id = self.code_agent.start_new_session()
        
        # 使用 CodeAgent 的 _call_model 方法调用模型
        start_time = time.time()
        response = self.code_agent._call_model(messages, session_id=session_id)
        elapsed = time.time() - start_time
        
        if self.verbose >= VERBOSE_FULL:
            print(f"模型响应时间: {elapsed:.2f}秒")
            print(f"响应长度: {len(response)} 字符")
        
        # 使用 CodeAgent 的 _process_response 方法解析代码
        result = self.code_agent._process_response(response)
        
        # 代码清理
        try:
            from utils.code_sanitizer import sanitize_code_prefix
            if "code" in result and isinstance(result["code"], str):
                result["code"] = sanitize_code_prefix(result["code"])
        except Exception:
            pass
        
        result["session_id"] = session_id
        
        return result
    

    


