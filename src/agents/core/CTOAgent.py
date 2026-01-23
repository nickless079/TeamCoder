from typing import Dict, Any, List, Optional
import json
import re

from ..BaseAgent import BaseAgent
from models.Base import BaseModel
from constants.verboseType import *
from utils.agent_dialogue import AgentDialogue

class CTOAgent(BaseAgent):
    """
    CTO智能体，负责总结测试用例、评估技术方案和审查代码
    """
    def __init__(
        self,
        model: BaseModel,
        verbose: int = 1,
        enabled: bool = True,
    ):
        """
        初始化CTO智能体
        
        Args:
            model: 模型实例
            verbose: 输出详细程度
            enabled: 是否启用该智能体
        """
        super().__init__(
            model=model,
            verbose=verbose,
            enabled=enabled,
            agent_name="CTOAgent",
            prompt_module_path="core.cto"
        )
        
        # 初始化对话工具，用于需要时进行对话总结
        self.dialogue_tool = AgentDialogue(verbose=verbose, max_turns=3)
    
    def _generate_prompt(self, task_type: str, **kwargs) -> List[Dict[str, str]]:
        """
        根据任务类型生成提示
        
        Args:
            task_type: 任务类型，如'summarize_test_cases', 'evaluate_solutions'等
            **kwargs: 任务相关参数
            
        Returns:
            消息列表
        """
        return self.prompt_module.get_messages(task_type, **kwargs)
    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        处理模型响应
        
        Args:
            response: 模型响应文本
            
        Returns:
            处理后的结果
        """
        # 尝试从响应中提取JSON格式的结果

       
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        
        # 尝试提取thought标签内容
        thought_match = re.search(r'<thought>\s*(.*?)\s*</thought>', response, re.DOTALL | re.IGNORECASE)
        
        result = {
            "structured_data": None,
            "thought": None,
            "raw_response": response
        }
        
        if json_match:
            try:
                json_str = json_match.group(1)
                result["structured_data"] = json.loads(json_str)
            except json.JSONDecodeError:
                # JSON解析失败，保持structured_data为None
                pass
        
        if thought_match:
            result["thought"] = thought_match.group(1).strip()
        
        return result
    
    def summarize_test_cases(self, problem_description: str, test_results: List[Dict[str, Any]], sample_io: List[Dict[str, Any]], attention_analysis: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """
        总结测试用例（第一阶段）
        
        Args:
            problem_description: 问题描述
            test_results: 各测试智能体的测试结果列表
            
        Returns:
            测试用例总结
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\n第一阶段: CTO总结测试用例\n{'-'*50}")
            
        result = self.execute(
            session_id=session_id,
            task_type="summarize_test_cases",
            problem_description=problem_description,
            test_results=test_results,
            sample_io=sample_io,
            attention_analysis=attention_analysis
        )

        print('the summarize_test_cases is result:\n', result,'\n')

        return result["result"]
    
    def evaluate_solutions(self, problem_description: str, test_cases: Dict[str, Any], search_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估技术方案（第二阶段-1）
        
        Args:
            problem_description: 问题描述
            test_cases: 测试用例
            search_results: 搜索结果
            
        Returns:
            评估结果
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\n第二阶段: CTO评估技术方案\n{'-'*50}")
            
        result = self.execute(
            task_type="evaluate_solutions",
            problem_description=problem_description,
            test_cases=test_cases,
            search_results=search_results
        )
        return result["result"]
    
    def finalize_technical_plan(self, problem_description: str, test_cases: Dict[str, Any], optimized_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        确定最终技术方案（第二阶段-2）
        
        Args:
            problem_description: 问题描述
            test_cases: 测试用例
            optimized_plan: 优化后的方案
            
        Returns:
            最终技术方案
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\n第二阶段: CTO确定最终技术方案\n{'-'*50}")
            
        result = self.execute(
            task_type="finalize_technical_plan",
            problem_description=problem_description,
            test_cases=test_cases,
            optimized_plan=optimized_plan
        )
        return result["result"]
    
    def review_and_refine_solution(self, problem_description: str, initial_solutions: Dict[str, Any], 
                                  test_cases: Dict[str, Any], thought_content: str = None,
                                  problem_sample_io: List[str] = None, 
                                  attention_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        评审并完善初步解决方案
        
        Args:
            problem_description: 问题描述
            initial_solutions: 初步解决方案
            test_cases: 测试用例
            thought_content: 思考内容
            problem_sample_io: 样例输入输出
            attention_analysis: 重点分析结果
            
        Returns:
            完善后的技术方案
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'-'*50}\nCTO评审完善阶段\n{'-'*50}")
            
        result = self.execute(
            session_id=None,
            task_type="evaluate_solutions",
            initial_solutions=initial_solutions,
            problem_description=problem_description,
            test_cases=test_cases,
            attention_analysis=attention_analysis,
            thought_content=thought_content
        )

        if self.verbose >= VERBOSE_FULL:
            print('CTO评审完善结果:\n', result, '\n')

        return result["result"]
    
    def review_code(self, problem_description, test_cases, technical_plan, code, language, attention_analysis=None, thought_content=None):
        """
        审查代码
        
        Args:
            problem_description: 问题描述
            test_cases: 测试用例
            technical_plan: 技术方案
            code: 代码
            language: 编程语言
            attention_analysis: 重点分析结果
            thought_content: 思考内容
            
        Returns:
            审查结果
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name}正在审查代码...")
            
        result = self.execute(
            session_id=None,
            task_type="review_code",
            problem_description=problem_description,
            test_cases=test_cases,
            technical_plan=technical_plan,
            code=code,
            language=language,
            attention_analysis=attention_analysis,
            thought_content=thought_content
        )

        if self.verbose >= VERBOSE_FULL:
            print('CTO代码检查结果:\n', result, '\n')

        return result["result"]
    
    def check_imports(self, code: str, language: str) -> Dict[str, Any]:
        """
        检查代码中的import语句是否正确
        
        Args:
            code: 要检查的代码
            language: 编程语言
            
        Returns:
            检查结果，包含修正后的代码
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name}正在检查import语句...")
            
        result = self.execute(
            session_id=None,
            task_type="check_imports",
            code=code,
            language=language
        )

        if self.verbose >= VERBOSE_FULL:
            print('CTO import检查结果:\n', result, '\n')

        return result["result"]
    
    def summarize_dialogue(self, dialogue_history: List[Dict[str, str]], topic: str) -> Dict[str, Any]:
        """
        总结智能体之间的对话
        
        Args:
            dialogue_history: 对话历史记录
            topic: 对话主题
            
        Returns:
            对话总结
        """
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\nCTO总结对话: {topic}\n")
            
        summary = self.dialogue_tool.summarize_dialogue(
            dialogue_history=dialogue_history,
            summarizer_agent=self
        )
        
        return {
            "topic": topic,
            "summary": summary,
            "raw_dialogue": dialogue_history
        } 