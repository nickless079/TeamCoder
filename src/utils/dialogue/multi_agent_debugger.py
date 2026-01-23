"""
多智能体调试器

为workflow提供的多智能体协作调试系统封装
"""

from typing import Dict, Any, List, Optional
from models.ModelFactory import ModelFactory
from agents.planning.SolutionPlanningAgent import SolutionPlanningAgent
from agents.core.CodeAgent import CodeAgent
from agents.core.CTOAgent import CTOAgent
from utils.dialogue import StateMachineOrchestrator
from datasets.Dataset import Dataset

class MultiAgentDebugger:
    """多智能体调试器类
    
    封装状态机驱动的三角色协作调试系统，供workflow使用
    """
    
    def __init__(self, model, verbose: int = 1):
        """初始化多智能体调试器
        
        Args:
            model: 语言模型实例
            verbose: 详细程度级别
        """
        self.model = model
        self.verbose = verbose
        
        # 初始化智能体
        self._init_agents()
        
        # 初始化状态机协调器
        self._init_orchestrator()
    
    def _init_agents(self):
        """初始化各个智能体"""
        # 初始化SolutionAgent
        self.solution_agent = SolutionPlanningAgent(
            model=self.model, 
            verbose=self.verbose
        )
        self.solution_agent.start_new_session()
        
        # 初始化CodeAgent
        self.code_agent = CodeAgent(
            model=self.model, 
            verbose=self.verbose
        )
        self.code_agent.start_new_session()
        
        # 初始化SimulationAgent（使用CTOAgent担任）
        self.simulation_agent = CTOAgent(
            model=self.model,
            verbose=self.verbose
        )
        self.simulation_agent.start_new_session()
        
        if self.verbose >= 1:
            print(f"✅ SolutionAgent Session ID: {getattr(self.solution_agent, 'session_id', 'Not Set')}")
            print(f"✅ CodeAgent Session ID: {getattr(self.code_agent, 'session_id', 'Not Set')}")
            print(f"✅ SimulationAgent Session ID: {getattr(self.simulation_agent, 'session_id', 'Not Set')}")
    
    def _init_orchestrator(self):
        """初始化状态机协调器"""
        self.orchestrator = StateMachineOrchestrator(
            solution_agent=self.solution_agent,
            code_agent=self.code_agent,
            simulation_agent=self.simulation_agent,
            quality_model=self.model,
            verbose=self.verbose
        )
    
    def debug_problem(self, 
                     problem_description: str,
                     current_code: str,
                     test_cases: List[str],
                     error_logs: str,
                     attention_analysis: Optional[Dict[str, Any]] = None,
                     init_code: Optional[str] = None,
                     is_competive: bool = False,
                     item :any = None,
                     dataset :Dataset = None) -> Dict[str, Any]:
        """调试问题
        
        Args:
            problem_description: 问题描述
            current_code: 当前错误代码
            test_cases: 测试用例列表
            error_logs: 错误日志
            attention_analysis: attention分析结果
            
        Returns:
            调试结果字典
        """
        return self.orchestrator.debug_problem(
            problem_description=problem_description,
            current_code=current_code,
            test_cases=test_cases,
            error_logs=error_logs,
            attention_analysis=attention_analysis,
            init_code=init_code,
            is_competive=is_competive,
            item=item,
            dataset=dataset
        )
    
    def set_verbose(self, verbose: int):
        """设置详细程度级别"""
        self.verbose = verbose
        self.orchestrator.verbose = verbose
        
        # 更新各个智能体的verbose级别
        self.solution_agent.verbose = verbose
        self.code_agent.verbose = verbose
        self.simulation_agent.verbose = verbose


def create_multi_agent_debugger(model_provider: str = "Alibaba",
                               model_name: str = "qwen3-4b", 
                               api_key: Optional[str] = None,
                               api_base: Optional[str] = None,
                               temperature: float = 0.2,
                               top_p: float = 0.95,
                               verbose: int = 1) -> MultiAgentDebugger:
    """创建多智能体调试器的工厂函数
    
    Args:
        model_provider: 模型提供商 (Alibaba, OpenAI, Ollama, etc.)
        model_name: 模型名称
        api_key: API密钥（可选，会尝试从环境变量获取）
        api_base: API基础URL（可选）
        temperature: 生成温度
        top_p: 生成top_p值
        verbose: 详细程度级别
        
    Returns:
        MultiAgentDebugger实例
    """
    # 使用ModelFactory创建模型，与主函数保持一致
    model_class = ModelFactory.get_model_class(model_provider)
    
    # 根据不同的模型提供商创建模型实例
    if model_provider.lower() == "ollama":
        model = model_class(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            api_base=api_base or "http://localhost:11434"
        )
    elif model_provider.lower() in ["alibaba", "aliyun", "bailian"]:
        model = model_class(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            api_base=api_base,
            api_key=api_key,
            verbose=verbose
        )
    else:
        # OpenAI, Anthropic, Gemini, Groq等
        model = model_class(
            model_name=model_name,
            temperature=temperature,
            top_p=top_p,
            api_key=api_key
        )
    
    # 创建并返回调试器
    return MultiAgentDebugger(model=model, verbose=verbose)
