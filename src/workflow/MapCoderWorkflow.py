"""
MapCoder Workflow
复杂的多步骤策略：KB + Exemplars + Planning + Verification + Code + Testing + Improvement
"""

from typing import Dict, Any, Optional, List, Tuple
import time
import xml.etree.ElementTree as ET

from .BaseWorkflow import BaseWorkflow
from models.Base import BaseModel
from datasets.Dataset import Dataset
from datasets.APPSDataset import APPSDataset
from utils.results import Results
from agents.core.CodeAgent import CodeAgent
from prompts.mapcoder import code as mapcoder_prompts
from constants.verboseType import *


class MapCoderWorkflow(BaseWorkflow):
    """
    MapCoder 工作流
    知识库 + 例子 + 规划 + 验证 + 代码生成 + 测试改进
    """
    
    def __init__(
        self,
        model: BaseModel,
        dataset: Dataset,
        language: str,
        k: int = 3,  # 生成 K 个例子
        t: int = 5,  # 最多改进 T 次
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
        
        self.k = k  # 生成 K 个例子用于 planning
        self.t = t  # 最多改进 T 次
        
        # 获取数据集类型
        self.dataset_type = self._get_dataset_type()
        
        # 判断是否为竞赛型数据集
        self.is_competitive = isinstance(self.dataset, APPSDataset)
        
        # 初始化 CodeAgent
        self._init_agents()
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*60}")
            print(f"MapCoder Workflow 初始化完成")
            print(f"数据集: {self.dataset_type}")
            print(f"语言: {self.language}")
            print(f"K (例子数): {self.k}")
            print(f"T (最大改进次数): {self.t}")
            print(f"Pass@K: {self.pass_at_k}")
            print(f"{'='*60}\n")
    
    def _init_agents(self):
        """初始化 Agent"""
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
            return "MBPP"
        else:
            return "HumanEval"
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个问题
        
        Args:
            item: 数据项
            
        Returns:
            处理结果
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
                # 使用 MapCoder 多步骤生成代码
                code_result = self._generate_code(item)
                code = code_result.get("code", "")
                generated_code = code
                attempts += 1
                
                if self.verbose >= VERBOSE_FULL:
                    print(f"\n最终生成的代码:\n{code}\n")
                
                # 评估代码
                from evaluations.pass_at_k import evaluate_humaneval_problem, evaluate_mbpp_problem
                
                dataset_type = self.dataset.__class__.__name__.lower()
                if "humaneval" in dataset_type:
                    evaluate_fn = evaluate_humaneval_problem
                elif "mbpp" in dataset_type:
                    evaluate_fn = evaluate_mbpp_problem
                else:
                    evaluate_fn = evaluate_humaneval_problem
                
                eval_result = evaluate_fn(
                    problem=item,
                    solutions=[code],
                    timeout=5
                )
                
                is_correct = len(eval_result.get("correct", [])) > 0
                pass_rate = eval_result.get("pass_rate", 0.0)
                
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"最终评估结果: {'通过' if is_correct else '失败'}")
                    print(f"通过率: {pass_rate:.2%}")
                
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
            "tokens_used": tokens_used,
            "attempts": attempts
        }
        
        return result_dict
    
    def _generate_code(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 MapCoder 多步骤生成代码
        
        Args:
            item: 数据项
            
        Returns:
            生成的代码结果
        """
        problem = self.dataset.get_prompt(item)
        sample_io = self._get_sample_io_str(item.get("sample_io", []))
        
        # Step 1: 生成知识库和例子
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n📚 Step 1: 生成知识库和例子 (K={self.k})...")
        
        kb_exemplars = self._generate_kb_exemplars(problem)
        
        if not kb_exemplars:
            if self.verbose >= VERBOSE_MINIMAL:
                print("⚠️ 知识库生成失败，退回到 direct 模式")
            return self._fallback_direct(problem)
        
        algorithm = kb_exemplars.get("algorithm", "")
        examples = kb_exemplars.get("problems", [])
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"✓ 生成了 {len(examples)} 个例子")
            print(f"✓ 识别的算法: {algorithm[:100]}...")
        
        # Step 2 & 3: 为每个例子生成 planning 并验证
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n📋 Step 2&3: 生成并验证 Planning (K={self.k})...")
        
        plannings = []
        for idx, example in enumerate(examples[:self.k], 1):
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n  Planning {idx}/{min(self.k, len(examples))}...")
            
            planning = self._generate_planning(
                problem=problem,
                example=example,
                algorithm=algorithm,
                sample_io=sample_io
            )
            
            if not planning:
                continue
            
            # 验证 planning
            confidence = self._verify_planning(problem, planning)
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"    置信度: {confidence}%")
            
            plannings.append((planning, confidence, example))
        
        # Step 4: 按置信度排序，选择最佳 planning
        plannings.sort(key=lambda x: x[1], reverse=True)
        best_planning, best_confidence, best_example = plannings[0]
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n✓ 选择最佳 planning (置信度: {best_confidence}%)")
        
        # Step 5: 生成代码
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n💻 Step 4: 生成代码...")
        
        code = self._generate_code_with_planning(
            problem=problem,
            planning=best_planning,
            algorithm=algorithm,
            sample_io=sample_io
        )
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"✓ 代码生成完成，长度: {len(code)}")
        
        # Step 6: 测试并改进（最多 T 次）
        if sample_io:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n🧪 Step 5: 测试并改进 (最多 {self.t} 次)...")
            
            for attempt in range(self.t):
                # 测试代码
                passed, test_log = self._test_code(item, code)
                
                if passed:
                    if self.verbose >= VERBOSE_MINIMAL:
                        print(f"✅ 代码通过 sample IO 测试！")
                    break
                
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"  改进尝试 {attempt + 1}/{self.t}...")
                
                # 改进代码
                code = self._improve_code(
                    problem=problem,
                    current_planning=best_planning,
                    current_code=code,
                    test_log=test_log,
                    algorithm=algorithm
                )
                
                if self.verbose >= VERBOSE_FULL:
                    print(f"  改进后代码长度: {len(code)}")
        
        return {
            "code": code,
            "algorithm": algorithm,
            "planning": best_planning,
            "confidence": best_confidence
        }
    
    def _generate_kb_exemplars(self, problem: str) -> Dict[str, Any]:
        """Step 1: 生成知识库和例子"""
        messages = mapcoder_prompts.get_kb_exemplars_messages(
            problem_description=problem,
            k=self.k,
            language=self.language
        )
        
        session_id = self.code_agent.start_new_session()
        response = self.code_agent._call_model(messages, session_id=session_id)
        
        if self.verbose >= VERBOSE_FULL:
            print(f"  KB+Exemplars 响应长度: {len(response)}")
        
        # 后处理 response（清理注释）
        response = self._trim_text(
            response, 
            "# Identify the algorithm (Brute-force, Dynamic Programming, Divide-and-conquer, Greedy, Backtracking, Recursive, Binary search, and so on) that needs to be used to solve the original problem."
        )
        response = self._trim_text(
            response, 
            "# Write a useful tutorial about the above mentioned algorithms. Provide a high level generic tutorial for solving this types of problem. Do not generate code."
        )
        response = self._trim_text(response, "# Planning to solve this problem:")
        response = self._trim_text(
            response, 
            f"# Let's think step by step to solve this problem in {self.language} programming language."
        )
        
        # 替换标签为 CDATA 格式
        response = self._replace_tag(response, 'algorithm')
        response = self._replace_tag(response, 'description')
        response = self._replace_tag(response, 'code')
        response = self._replace_tag(response, 'planning')
        
        # 解析 XML 响应
        try:
            parsed = self._parse_xml(response)
            
            # 提取 algorithm 和 problems
            algorithm = parsed.get("algorithm", "")
            problems_raw = parsed.get("problem", [])
            
            # 确保 problems 是列表
            if not isinstance(problems_raw, list):
                problems_raw = [problems_raw]
            
            return {
                "algorithm": algorithm,
                "problems": problems_raw
            }
        except Exception as e:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"⚠️ XML 解析失败: {e}")
            return None
    
    def _generate_planning(
        self,
        problem: str,
        example: Dict[str, Any],
        algorithm: str,
        sample_io: str
    ) -> str:
        """Step 2: 生成 planning"""
        try:
            example_problem = example.get("description", "")
            example_planning = example.get("planning", "")
            
            messages = mapcoder_prompts.get_problem_planning_messages(
                problem_description=problem,
                example_problem=example_problem,
                example_planning=example_planning,
                algorithm=algorithm,
                sample_io=sample_io,
                language=self.language
            )
            
            session_id = self.code_agent.start_new_session()
            planning = self.code_agent._call_model(messages, session_id=session_id)
            
            return planning
        except Exception as e:
            if self.verbose >= VERBOSE_FULL:
                print(f"  ⚠️ Planning 生成失败: {e}")
            return ""
    
    def _verify_planning(self, problem: str, planning: str) -> int:
        """Step 3: 验证 planning 并返回置信度"""
        try:
            messages = mapcoder_prompts.get_planning_verification_messages(
                problem_description=problem,
                planning=planning,
                language=self.language
            )
            
            session_id = self.code_agent.start_new_session()
            response = self.code_agent._call_model(messages, session_id=session_id)
            
            # 后处理：替换标签为 CDATA 格式
            response = self._replace_tag(response, 'explanation')
            response = self._replace_tag(response, 'confidence')
            
            # 解析 XML 响应
            parsed = self._parse_xml(response)
            confidence = int(str(parsed.get("confidence", 50)).strip())
            
            return confidence
        except Exception as e:
            if self.verbose >= VERBOSE_FULL:
                print(f"  ⚠️ Planning 验证失败: {e}")
            return 50  # 默认置信度
    
    def _generate_code_with_planning(
        self,
        problem: str,
        planning: str,
        algorithm: str,
        sample_io: str
    ) -> str:
        """Step 4: 根据 planning 生成代码"""
        messages = mapcoder_prompts.get_code_generation_messages(
            problem_description=problem,
            planning=planning,
            algorithm=algorithm,
            sample_io=sample_io,
            language=self.language,
            dataset_type=self.dataset_type
        )
        
        session_id = self.code_agent.start_new_session()
        response = self.code_agent._call_model(messages, session_id=session_id)
        
        # 解析代码
        code_result = self.code_agent._process_response(response)
        code = code_result.get("code", "")
        
        # 代码清理
        try:
            from utils.code_sanitizer import sanitize_code_prefix
            code = sanitize_code_prefix(code)
        except Exception:
            pass
        
        return code
    
    def _test_code(self, item: Dict[str, Any], code: str) -> Tuple[bool, str]:
        """测试代码是否通过 sample IO"""
        try:
            passed, test_log = self.dataset.evaluate_sample_io(
                item,
                code,
                self.language
            )
            return passed, test_log
        except Exception as e:
            return False, str(e)
    
    def _improve_code(
        self,
        problem: str,
        current_planning: str,
        current_code: str,
        test_log: str,
        algorithm: str
    ) -> str:
        """Step 5: 根据测试结果改进代码"""
        messages = mapcoder_prompts.get_code_improvement_messages(
            problem_description=problem,
            current_planning=current_planning,
            current_code=current_code,
            test_log=test_log,
            algorithm=algorithm,
            language=self.language,
            dataset_type=self.dataset_type
        )
        
        session_id = self.code_agent.start_new_session()
        response = self.code_agent._call_model(messages, session_id=session_id)
        
        # 解析代码
        code_result = self.code_agent._process_response(response)
        code = code_result.get("code", "")
        
        # 代码清理
        try:
            from utils.code_sanitizer import sanitize_code_prefix
            code = sanitize_code_prefix(code)
        except Exception:
            pass
        
        return code
    
    def _fallback_direct(self, problem: str) -> Dict[str, Any]:
        """退回到 direct 模式"""
        from prompts.direct import code as direct_prompts
        
        messages = direct_prompts.get_messages(
            problem_description=problem,
            language=self.language
        )
        
        session_id = self.code_agent.start_new_session()
        response = self.code_agent._call_model(messages, session_id=session_id)
        result = self.code_agent._process_response(response)
        
        return result
    
    def _parse_xml(self, response: str) -> dict:
        """解析 XML 响应"""
        # 清理 response
        if '```xml' in response:
            response = response.replace('```xml', '')
        if '```' in response:
            response = response.replace('```', '')
        
        try:
            root = ET.fromstring(response)
        except:
            try:
                root = ET.fromstring('<root>\n' + response + '\n</root>')
            except:
                try:
                    root = ET.fromstring('<root>\n' + response)
                except:
                    return {}
        
        return self._xml_to_dict(root)
    
    def _xml_to_dict(self, element) -> dict:
        """将 XML 元素转换为字典"""
        result = {}
        for child in element:
            if len(child) > 0:  # 有子元素
                child_data = self._xml_to_dict(child)
                if child.tag in result:
                    if isinstance(result[child.tag], list):
                        result[child.tag].append(child_data)
                    else:
                        result[child.tag] = [result[child.tag], child_data]
                else:
                    result[child.tag] = child_data
            else:  # 叶子节点
                result[child.tag] = child.text if child.text else ""
        return result
    
    @staticmethod
    def _trim_text(text: str, trimmed_text: str) -> str:
        """移除指定文本"""
        return text.replace(trimmed_text, '').strip()
    
    @staticmethod
    def _replace_tag(text: str, tag: str) -> str:
        """替换标签为 CDATA 格式"""
        if f'<{tag}><![CDATA[' in text and f']]></{tag}>' in text:
            return text 
        else:
            return text.replace(f'<{tag}>', f'<{tag}><![CDATA[').replace(f'</{tag}>', f']]></{tag}>').strip()
    
    def _get_sample_io_str(self, sample_io: any) -> str:
        """获取 sample IO 字符串"""
        if not sample_io:
            return ""
        
        if len(sample_io) > 0:
            if isinstance(sample_io[0], str):
                return "\n".join(sample_io)
            if isinstance(sample_io[0], dict):
                return "\n".join([
                    f"Input:\n{io['input']}\nExpected output:\n{io['output'][0]}"
                    for io in sample_io
                ])
        
        return str(sample_io)
    
 