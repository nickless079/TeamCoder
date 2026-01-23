"""
状态机协调器 - 调试系统的核心控制器
"""

import time
from typing import Dict, Any, List, Optional
from agents.BaseAgent import BaseAgent
from .types import NodeType, DebugContext, AgentRole, StateTransition, NodeResult
from .quality_gate import QualityGate
from .nodeswotimeout import DiagnosisNode, BlueprintDesignNode, ImplementationNode, ValidationNode, TimeoutHandlerNode
from constants.verboseType import *
from datasets.Dataset import Dataset
class StateMachineOrchestrator:
    """
    状态机协调器
    
    这是整个调试系统的大脑，负责：
    1. 状态转换控制
    2. 节点执行协调
    3. 回滚和重启机制
    4. 质量门控管理
    """
    
    def __init__(
        self,
        solution_agent: BaseAgent,
        code_agent: BaseAgent,
        quality_model,  # 用于质量评估的模型
        simulation_agent: Optional[BaseAgent] = None,  # 新增的SimulationAgent参数
        verbose: int = 1,
        log_file_path: Optional[str] = None
    ):
        """
        初始化状态机协调器
        
        Args:
            solution_agent: 解决方案智能体
            code_agent: 代码智能体
            quality_model: 质量评估模型
            simulation_agent: 仿真智能体 (可选，用于第二阶段)
            verbose: 输出详细程度
            log_file_path: 日志文件路径，如果提供则将详细执行过程写入文件
        """
        self.verbose = verbose
        self.log_file_path = log_file_path
        
        # 智能体映射
        self.agents = {
            AgentRole.SOLUTION_AGENT: solution_agent,
            AgentRole.CODE_AGENT: code_agent,
            AgentRole.ORCHESTRATOR: self  # 协调器本身
        }
        
        # 如果提供了SimulationAgent，添加到智能体映射中
        if simulation_agent is not None:
            self.agents[AgentRole.SIMULATION_AGENT] = simulation_agent
        
        # 质量门控系统
        self.quality_gate = QualityGate(quality_model, verbose)
        
        # 节点实例化
        self.nodes = {
            NodeType.DIAGNOSIS: DiagnosisNode(self.quality_gate, verbose),
            NodeType.BLUEPRINT_DESIGN: BlueprintDesignNode(self.quality_gate, verbose),
            NodeType.TIMEOUT_HANDLER: TimeoutHandlerNode(self.quality_gate, verbose),
            NodeType.IMPLEMENTATION: ImplementationNode(self.quality_gate, verbose),
            NodeType.VALIDATION: ValidationNode(self.quality_gate, verbose)
        }
        
        # 状态管理
        self.current_node = NodeType.DIAGNOSIS
        self.execution_history = []
        self.max_restart_attempts = 2  # 最大重启次数
        self.max_reroll_attempts = 3
        self.restart_count = 0
        self.reroll_count=0
    
    def debug_problem(
        self,
        problem_description: str,
        test_cases: List[Dict[str, Any]],
        current_code: Optional[str] = None,
        error_logs: Optional[str] = None,
        sample_io: Optional[List[Dict[str, Any]]] = None,
        attention_analysis: Optional[Dict[str, Any]] = None,
        init_code: Optional[str] = None,
        is_competive: bool =None,
        item: any = None,
        dataset :Dataset = None
    ) -> Dict[str, Any]:
        """
        调试问题的主入口
        
        Args:
            problem_description: 问题描述
            test_cases: 测试用例
            current_code: 当前错误代码
            error_logs: 错误日志
            sample_io: 样例输入输出
            attention_analysis: attention分析结果
            
        Returns:
            调试结果
        """
        self._log("🚀 开始状态机驱动的调试流程...")
        
        # 初始化调试上下文
        context = DebugContext(
            problem_description=problem_description,
            test_cases=test_cases,
            current_code=current_code,
            error_logs=error_logs,
            sample_io=sample_io,
            attention_analysis=attention_analysis,
            init_code= init_code,
            is_competive=is_competive,
            item=item,
            dataset=dataset
        )
        
        start_time = time.time()
        
        try:
            # 执行状态机主循环
            final_result = self._execute_state_machine(context)
            
            execution_time = time.time() - start_time
            
            # 构建最终结果
            result = {
                "success": final_result.success,
                "final_code": context.final_code,
                "execution_time": execution_time,
                "execution_history": self.execution_history,
                "restart_count": self.restart_count,
                "reroll_count": self.reroll_count
            }
            
            if final_result.success:
                result["validation_result"] = final_result.output.get("validation_result")
                self._log(f"✅ 调试成功完成，耗时 {execution_time:.2f} 秒")
            else:
                result["error"] = final_result.error_message
                self._log(f"❌ 调试失败: {final_result.error_message}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._log(f"💥 调试过程发生异常: {str(e)}")
            return {
                "success": False,
                "error": f"调试过程异常: {str(e)}",
                "execution_time": execution_time,
                "execution_history": self.execution_history,
                "restart_count": self.restart_count,
                "reroll_count": self.reroll_count
            }
    
    def _execute_state_machine(self, context: DebugContext) -> NodeResult:
        """执行状态机主循环"""
        
        while True:
            self._log(f"📍 当前节点: {self.current_node.value}")
            
            # 获取当前节点实例
            current_node_instance = self.nodes[self.current_node]
            
            # 执行当前节点
            node_start_time = time.time()
            node_result = current_node_instance.execute(context, self.agents)
            node_execution_time = time.time() - node_start_time
            
            # 记录执行历史
            self.execution_history.append({
                "node": self.current_node.value,
                "success": node_result.success,
                "execution_time": node_execution_time,
                "output": node_result.output if node_result.success else None,
                "error": node_result.error_message if not node_result.success else None
            })
            
            if node_result.success:
                # 节点执行成功
                if node_result.next_node is None:
                    # 流程完成
                    self._log("🎯 调试流程成功完成")
                    return node_result
                else:
                    # 转到下一个节点
                    self.current_node = node_result.next_node
                    continue
            elif context.timeout and self.current_node == NodeType.VALIDATION:
                # 如果在验证节点超时，直接返回结果
                self._log("⏰ 验证节点超时，终止调试流程")
                return node_result
            else:
                # 节点执行失败，处理回滚或重启
                return self._handle_failure(node_result, context)
    
    def _handle_failure(self, node_result: NodeResult, context: DebugContext) -> NodeResult:
        """处理节点执行失败"""
        if node_result.rollback_to and self.reroll_count == self.max_reroll_attempts:
            self.reroll_count +=1
            self.current_node = NodeType.TIMEOUT_HANDLER
            return self._execute_state_machine(context)


        if node_result.rollback_to and self.reroll_count < self.max_reroll_attempts:
            # 回滚到指定节点
            self._log(f"🔄 回滚到节点: {node_result.rollback_to.value}")
            self.current_node = node_result.rollback_to
            self.reroll_count +=1
            self._log(f"🔄 回滚到节点次数: {self.reroll_count}")

            # if context.timeout and self.restart_count == self.max_restart_attempts:
            #     return node_result
            # elif context.timeout and self.restart_count < self.max_restart_attempts:
            #     self.restart_count += 1
            #     return self._restart_with_enriched_context(context, node_result)
            
            if context.timeout:
                return node_result
        
            # 继续执行
            return self._execute_state_machine(context)
        
        if self.current_node == NodeType.VALIDATION and self.restart_count < self.max_restart_attempts:
                # 验证失败，重启整个流程
                self.restart_count += 1
                return self._restart_with_enriched_context(context, node_result)
        else:
            # 无法恢复的失败
            self._log("❌ 无法恢复的失败，调试流程终止")
            return node_result
    
    def _inject_stress_test_failure_info(self, context: DebugContext, node_result: NodeResult):
        """注入压力测试失败信息到上下文"""
        failed_case = node_result.output.get("failed_case", "")
        if failed_case:
            # 将失败信息添加到问题描述中
            context.problem_description += f"\\n\\n## 压力测试失败案例\\n{failed_case}"
            self._log("📝 已注入压力测试失败信息到上下文")
    
    def _restart_with_enriched_context(self, context: DebugContext, validation_result: NodeResult) -> NodeResult:
        """使用丰富的上下文重启流程"""
        
        self.restart_count += 1
        self._log(f"🔄 执行第 {self.restart_count} 次重启...")
        
        # 构建极其丰富的新问题描述
        enriched_description = self._build_enriched_problem_description(context, validation_result)
        
        # 创建新的上下文
        new_context = DebugContext(
            problem_description=enriched_description,
            test_cases=context.test_cases,
            sample_io=context.sample_io
        )
        
        # 重置状态
        self.current_node = NodeType.DIAGNOSIS
        
        # 清理智能体会话历史（重新开始）
        for agent in self.agents.values():
            if hasattr(agent, 'start_new_session'):
                agent.start_new_session()
        
        # 重新执行状态机
        return self._execute_state_machine(new_context)
    
    def _build_enriched_problem_description(self, context: DebugContext, validation_result: NodeResult) -> str:
        """构建包含完整历史的丰富问题描述"""
        
        enriched_parts = [
            "# 原始问题描述",
            context.problem_description,
            "",
            "# 完整的失败历史",
            "## 之前的诊断分析",
            str(context.diagnosis_result) if context.diagnosis_result else "无诊断结果",
            "",
            "## 之前的蓝图设计", 
            context.blueprint if context.blueprint else "无蓝图设计",
            "",
            "## 失败的最终代码",
            context.final_code if context.final_code else "无最终代码",
            "",
            "## 最新的错误日志",
            str(validation_result.output.get("validation_result", {})) if validation_result.output else "无验证结果",
            "",
            "# 执行历史摘要"
        ]
        
        for i, history_item in enumerate(self.execution_history, 1):
            enriched_parts.append(f"{i}. {history_item['node']}: {'成功' if history_item['success'] else '失败'}")
            if not history_item['success'] and history_item.get('error'):
                enriched_parts.append(f"   错误: {history_item['error']}")
        
        enriched_parts.extend([
            "",
            f"# 重启次数: {self.restart_count}",
            "",
            "请基于以上完整的失败历史，重新进行更深层次的分析。"
        ])
        
        return "\\n".join(enriched_parts)
    
    def _log(self, message: str, level: int = VERBOSE_MINIMAL):
        """日志输出"""
        if self.verbose >= level:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] [Orchestrator] {message}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "total_nodes_executed": len(self.execution_history),
            "current_node": self.current_node.value,
            "restart_count": self.restart_count,
            "execution_history": self.execution_history
        }
