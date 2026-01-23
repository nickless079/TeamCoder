"""
状态机驱动的三角色协作调试系统

核心组件:
- StateMachineOrchestrator: 状态机协调器
- MultiAgentDebugger: 多智能体调试器（workflow封装）
- DebugNode: 调试节点基类
- NodeTypes: 节点类型定义
- QualityGate: 质量门控系统
"""

from .orchestrator import StateMachineOrchestrator
from .multi_agent_debugger import MultiAgentDebugger, create_multi_agent_debugger
from .nodes import (
    DebugNode, 
    DiagnosisNode, 
    BlueprintDesignNode, 
    ImplementationNode, 
    ValidationNode
)
from .quality_gate import QualityGate
from .types import NodeType, AgentRole, DebugContext

__all__ = [
    'StateMachineOrchestrator',
    'MultiAgentDebugger',
    'create_multi_agent_debugger',
    'QualityGate',
    'DebugNode',
    'DiagnosisNode',
    'BlueprintDesignNode', 
    'ImplementationNode',
    'ValidationNode',
    'NodeType',
    'AgentRole',
    'DebugContext'
]
