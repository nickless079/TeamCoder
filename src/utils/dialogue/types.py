"""
节点类型定义和状态管理
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datasets.Dataset import Dataset
class NodeType(Enum):
    """调试节点类型"""
    DIAGNOSIS = "NODE_DIAGNOSIS"  # 根本原因诊断
    BLUEPRINT_DESIGN = "NODE_BLUEPRINT_DESIGN"  # 蓝图设计与审查
    TIMEOUT_HANDLER = "NODE_TIMEOUT_HANDLER"  # 超时处理节点
    STRESS_TESTING = "NODE_STRESS_TESTING"  # 蓝图压力测试
    IMPLEMENTATION = "NODE_IMPLEMENTATION"  # 最终代码实现
    VALIDATION = "NODE_VALIDATION"  # 自动验证与裁决

class AgentRole(Enum):
    """智能体角色"""
    SOLUTION_AGENT = "SolutionAgent"  # 策略制定者
    CODE_AGENT = "CodeAgent"  # 实现者
    SIMULATION_AGENT = "SimulationAgent"  # 仿真者
    ORCHESTRATOR = "Orchestrator"  # 协调者

class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"  # 等待执行
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    ROLLBACK = "rollback"  # 回滚

@dataclass
class DebugContext:
    """调试上下文"""
    problem_description: str
    test_cases: List[Dict[str, Any]]
    all_analysis: List[Any] = field(default_factory=list)
    current_code: Optional[str] = None
    init_code: str = None
    error_logs: Optional[str] = None
    sample_io: Optional[List[Dict[str, Any]]] = None
    expected_value: Optional[str] = None  # 添加提取门控得到的期望值
    attention_analysis: Optional[Dict[str, Any]] = None  # 添加attention分析结果
    is_competive: bool = None #是否竞赛
    item : any =None # 数据项
    # 节点间传递的数据
    diagnosis_result: Optional[Dict[str, Any]] = None
    blueprint: Optional[str] = None
    test_cases_generated: Optional[List[Dict[str, Any]]] = None
    final_code: Optional[str] = None
    
    # 历史记录
    dialogue_history: List[Dict[str, Any]] = None
    dataset: Dataset =None
    # 超时标志
    timeout: bool = False
    
    def __post_init__(self):
        if self.dialogue_history is None:
            self.dialogue_history = []

@dataclass 
class NodeResult:
    """节点执行结果"""
    success: bool
    output: Dict[str, Any]
    next_node: Optional[NodeType] = None
    rollback_to: Optional[NodeType] = None
    error_message: Optional[str] = None
    needs_intervention: bool = False  # 是否需要导演干预
    
class StateTransition:
    """状态转换规则"""
    
    # 正常流程的状态转换
    NORMAL_FLOW = {
        NodeType.DIAGNOSIS: NodeType.BLUEPRINT_DESIGN,
        NodeType.BLUEPRINT_DESIGN: NodeType.IMPLEMENTATION,
        NodeType.IMPLEMENTATION: NodeType.VALIDATION,
        NodeType.VALIDATION: None  # 结束
    }
    
    # 回滚流程
    ROLLBACK_RULES = {
        NodeType.STRESS_TESTING: NodeType.BLUEPRINT_DESIGN,  # 压力测试失败回滚到设计
        NodeType.VALIDATION: NodeType.DIAGNOSIS,  # 验证失败回滚到诊断
    }
    
    # 超时处理规则
    TIMEOUT_RULES = {
        NodeType.BLUEPRINT_DESIGN: NodeType.TIMEOUT_HANDLER,  # 蓝图设计超时转到超时处理节点
    }
    
    @classmethod
    def get_next_node(cls, current_node: NodeType, success: bool = True, timeout: bool = False) -> Optional[NodeType]:
        """获取下一个节点"""
        if success:
            return cls.NORMAL_FLOW.get(current_node)

        return cls.ROLLBACK_RULES.get(current_node)
