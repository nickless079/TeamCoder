from typing import Dict, Any, List, Optional, Tuple
import time
import uuid
import re

from constants.verboseType import *
from agents.BaseAgent import BaseAgent

class DiscussionCoordinator:
    """
    讨论协调者类，负责智能管理群组讨论流程
    """
    def __init__(self, coordinator_agent: BaseAgent, verbose: int = 1):
        """
        初始化讨论协调者
        
        Args:
            coordinator_agent: 协调者智能体（通常是CTO）
            verbose: 输出详细程度
        """
        self.coordinator = coordinator_agent
        self.verbose = verbose
        
        # 智能体专业领域映射
        self.agent_expertise = {
            "CTOAgent": {
                "domains": ["决策", "总结", "架构", "管理", "协调", "评估"],
                "priority": 10,
                "description": "技术总监，负责决策和总体协调"
            },
            "SolutionPlanningAgent": {
                "domains": ["算法", "方案设计", "技术分析", "规划", "优化"],
                "priority": 8,
                "description": "解决方案规划专家，负责技术方案设计"
            },
            "CodeAgent": {
                "domains": ["编程", "实现", "代码生成", "语法", "优化", "修复"],
                "priority": 7,
                "description": "代码生成专家，负责具体代码实现"
            },
            "TestAgent": {
                "domains": ["测试", "验证", "质量保证", "用例设计", "错误分析"],
                "priority": 6,
                "description": "测试专家，负责测试用例设计和验证"
            }
        }
        
        # 讨论模式定义
        self.discussion_patterns = {
            "code_failure": {
                "description": "代码失败修复讨论",
                "phases": [
                    {"agent": "TestAgent", "task": "分析错误和测试失败原因", "max_turns": 1},
                    {"agent": "SolutionPlanningAgent", "task": "提供修复建议", "max_turns": 1},
                
                    {"agent": "CodeAgent", "task": "实现代码修复", "max_turns": 1}
                ]
            },
            "multi_stage_collaboration": {
                "description": "多阶段智能体协作代码修复",
                "phases": [
                   
                    {"agent": "TestAgent", "task": "从测试角度分析失败原因", "max_turns": 1},
                    {"agent": "SolutionPlanningAgent", "task": "基于前期分析提供修复方案", "max_turns": 1},
                    {"agent": "CodeAgent", "task": "实现代码修复", "max_turns": 1}
                ]
            },
            "design_review": {
                "description": "设计方案评审讨论",
                "phases": [
                    {"agent": "SolutionPlanningAgent", "task": "介绍设计方案", "max_turns": 1},
                
                    {"agent": "TestAgent", "task": "评估测试覆盖", "max_turns": 1},
                    {"agent": "CodeAgent", "task": "评估实现难度并提供代码", "max_turns": 1}
                ]
            },
            "test_case_generation": {
                "description": "测试用例生成讨论",
                "phases": [
                    {"agent": "TestAgent", "task": "分析测试需求", "max_turns": 1},
                    {"agent": "SolutionPlanningAgent", "task": "提供技术建议", "max_turns": 1},
            
                    {"agent": "CodeAgent", "task": "实现测试代码", "max_turns": 1}
                ]
            },
            "free_discussion": {
                "description": "自由讨论模式",
                "phases": []  # 空phases表示使用动态协调
            }
        }
    
    def analyze_discussion_context(self, topic: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析讨论上下文，确定讨论类型和策略
        
        Args:
            topic: 讨论主题
            context: 讨论上下文
            
        Returns:
            分析结果，包含讨论类型、关键词、建议策略等
        """
        analysis_prompt = f"""
作为技术总监，请分析以下讨论情况，确定最佳的讨论策略：

讨论主题: {topic}

上下文信息:
{self._format_context_for_analysis(context)}

注意!!:
sample_io总是正确的,不要去质疑sample_io的正确性

请分析并返回以下信息：
1. 讨论类型（code_failure/multi_stage_collaboration/design_review/test_case_generation/free_discussion）
2. 关键问题点
3. 需要重点参与的智能体
4. 预计讨论轮次
5. 讨论优先级（1-10）

讨论类型说明：
- code_failure: 简单的代码错误修复，主要涉及测试分析和代码修改
- multi_stage_collaboration: 需要多个阶段智能体协作的复杂问题，涉及测试分析、方案设计、代码实现等多个环节
- design_review: 设计方案的评审和讨论
- test_case_generation: 测试用例的生成和验证
- free_discussion: 开放式讨论

判断multi_stage_collaboration的条件：
- 涉及到前期阶段的测试用例、技术方案等信息
- 需要多个专业领域专家协作（测试、规划、编码、管理）
- 问题复杂度较高，需要系统性分析

注意：TestAgent现在承担错误分析和测试验证的双重职责，CodeAgent负责代码修复，SolutionPlanningAgent负责技术方案，CTOAgent负责协调管理。

请用以下格式回复：
<ANALYSIS>
讨论类型: [类型]
关键问题: [问题描述]
重点智能体: [智能体列表]
预计轮次: [数字]
优先级: [1-10]
建议策略: [策略描述]
</ANALYSIS>
"""
        
        # 创建临时会话进行分析
        temp_session = self.coordinator.start_new_session()
        self.coordinator.set_active_session(temp_session)
        
        response = self.coordinator._call_model([
            {"role": "system", "content": "你是一位经验丰富的技术总监，擅长分析技术讨论需求并制定讨论策略。"},
            {"role": "user", "content": analysis_prompt}
        ], session_id=temp_session, include_history=False)
        
        # 解析分析结果
        analysis = self._parse_analysis_response(response)
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n=== 协调者分析结果 ===")
            print(f"讨论类型: {analysis.get('discussion_type', 'unknown')}")
            print(f"关键问题: {analysis.get('key_issues', 'unknown')}")
            print(f"重点智能体: {analysis.get('key_agents', [])}")
            print(f"预计轮次: {analysis.get('estimated_turns', 'unknown')}")
            print(f"优先级: {analysis.get('priority', 'unknown')}")
            print(f"========================\n")
        
        return analysis
    
    def plan_discussion_flow(self, analysis: Dict[str, Any], available_agents: List[BaseAgent]) -> Dict[str, Any]:
        """
        根据分析结果规划讨论流程
        
        Args:
            analysis: 讨论分析结果
            available_agents: 可用的智能体列表
            
        Returns:
            讨论流程计划
        """
        discussion_type = analysis.get('discussion_type', 'free_discussion')
        
        if discussion_type in self.discussion_patterns:
            pattern = self.discussion_patterns[discussion_type]
            
            if pattern['phases']:
                # 使用预定义模式
                return self._create_structured_plan(pattern, available_agents, analysis)
            else:
                # 使用动态协调
                return self._create_dynamic_plan(available_agents, analysis)
        else:
            # 默认动态协调
            return self._create_dynamic_plan(available_agents, analysis)
    
    def choose_next_speaker(self, 
                          current_context: Dict[str, Any], 
                          dialogue_history: List[Dict[str, str]], 
                          available_agents: List[BaseAgent],
                          discussion_plan: Dict[str, Any],
                          current_turn: int) -> BaseAgent:
        """
        智能选择下一个发言者
        
        Args:
            current_context: 当前讨论上下文
            dialogue_history: 对话历史
            available_agents: 可用智能体列表
            discussion_plan: 讨论计划
            current_turn: 当前轮次
            
        Returns:
            下一个应该发言的智能体
        """
        plan_type = discussion_plan.get('type', 'dynamic')
        
        if plan_type == 'structured':
            # 结构化流程
            return self._choose_speaker_structured(discussion_plan, current_turn, available_agents)
        else:
            # 动态协调
            return self._choose_speaker_dynamic(current_context, dialogue_history, available_agents)
    
    def should_continue_discussion(self, 
                                 dialogue_history: List[Dict[str, str]], 
                                 discussion_plan: Dict[str, Any],
                                 max_turns: int) -> bool:
        """
        判断是否应该继续讨论
        
        Args:
            dialogue_history: 对话历史
            discussion_plan: 讨论计划
            max_turns: 最大轮次
            
        Returns:
            是否继续讨论
        """
        current_turn = len(dialogue_history)
        
        # 检查是否达到最大轮次
        if current_turn >= max_turns:
            print(f"达到最大轮次: {max_turns}")
            return False
        
        # 检查是否达到目标
        if self._check_discussion_goals_achieved(dialogue_history, discussion_plan):
            print('讨论目标已达成')
            return False
        
        # 检查是否出现循环或无效讨论
        if self._detect_circular_discussion(dialogue_history):
            print('出现循环或无效讨论')
            return False
        
        return True
    
    def _format_context_for_analysis(self, context: Dict[str, Any]) -> str:
        """格式化上下文信息用于分析"""
        formatted = ""
        for key, value in context.items():
            if isinstance(value, list):
                value_str = "\n".join([str(v) for v in value[:3]])  # 只显示前3项
                if len(value) > 3:
                    value_str += f"\n... (共{len(value)}项)"
            else:
                value_str = str(value)[:500]  # 限制长度
            formatted += f"{key}: {value_str}\n\n"
        return formatted
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析协调者的分析回复"""
        analysis = {}
        
        # 提取ANALYSIS标签内容
        match = re.search(r'<ANALYSIS>(.*?)</ANALYSIS>', response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            
            # 解析各个字段
            patterns = {
                'discussion_type': r'讨论类型:\s*([^\n]+)',
                'key_issues': r'关键问题:\s*([^\n]+)',
                'key_agents': r'重点智能体:\s*([^\n]+)',
                'estimated_turns': r'预计轮次:\s*(\d+)',
                'priority': r'优先级:\s*(\d+)',
                'strategy': r'建议策略:\s*([^\n]+)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    value = match.group(1).strip()
                    if key == 'key_agents':
                        # 解析智能体列表
                        agents = [agent.strip() for agent in value.split(',')]
                        analysis[key] = agents
                    elif key in ['estimated_turns', 'priority']:
                        # 转换为数字
                        try:
                            analysis[key] = int(value)
                        except ValueError:
                            analysis[key] = 5  # 默认值
                    else:
                        analysis[key] = value
        
        # 设置默认值
        analysis.setdefault('discussion_type', 'free_discussion')
        analysis.setdefault('estimated_turns', 5)
        analysis.setdefault('priority', 5)
        analysis.setdefault('key_agents', [])
        
        return analysis
    
    def _create_structured_plan(self, pattern: Dict[str, Any], available_agents: List[BaseAgent], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """创建结构化讨论计划"""
        plan = {
            'type': 'structured',
            'pattern': pattern,
            'phases': [],
            'total_estimated_turns': 0
        }
        
        agent_map = {agent.agent_name: agent for agent in available_agents}
        
        for phase in pattern['phases']:
            agent_name = phase['agent']
            if agent_name in agent_map:
                plan['phases'].append({
                    'agent': agent_map[agent_name],
                    'agent_name': agent_name,
                    'task': phase['task'],
                    'max_turns': phase['max_turns']
                })
                plan['total_estimated_turns'] += phase['max_turns']
        
        # 打印结构化计划
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n=== 结构化讨论计划 ===")
            print(f"模式: {pattern.get('description', 'unknown')}")
            print(f"预计总轮次: {plan['total_estimated_turns']}")
            print("阶段安排:")
            for i, phase in enumerate(plan['phases'], 1):
                print(f"  {i}. {phase['agent_name']}: {phase['task']} ({phase['max_turns']}轮)")
            print(f"====================\n")
        
        return plan
    
    def _create_dynamic_plan(self, available_agents: List[BaseAgent], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """创建动态协调计划"""
        plan = {
            'type': 'dynamic',
            'key_agents': analysis.get('key_agents', []),
            'estimated_turns': analysis.get('estimated_turns', 5),
            'priority_order': self._calculate_agent_priorities(available_agents, analysis)
        }
        
        # 打印动态协调计划
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n=== 动态协调计划 ===")
            print(f"关键智能体: {plan['key_agents']}")
            print(f"预计轮次: {plan['estimated_turns']}")
            print(f"优先级顺序: {plan['priority_order']}")
            print(f"==================\n")
        
        return plan
    
    def _calculate_agent_priorities(self, available_agents: List[BaseAgent], analysis: Dict[str, Any]) -> List[str]:
        """根据分析结果计算智能体优先级顺序"""
        key_agents = analysis.get('key_agents', [])
        agent_scores = {}
        
        for agent in available_agents:
            agent_name = agent.agent_name
            base_score = self.agent_expertise.get(agent_name, {}).get('priority', 5)
            
            # 如果是关键智能体，加分
            if agent_name in key_agents:
                base_score += 3
            
            agent_scores[agent_name] = base_score
        
        # 按分数降序排列
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        return [agent_name for agent_name, _ in sorted_agents]
    
    def _choose_speaker_structured(self, discussion_plan: Dict[str, Any], current_turn: int, available_agents: List[BaseAgent]) -> BaseAgent:
        """在结构化模式下选择发言者"""
        phases = discussion_plan.get('phases', [])
        if not phases:
            return available_agents[current_turn % len(available_agents)]
        
        # 计算当前应该在哪个阶段
        turn_count = 0
        for phase in phases:
            if current_turn < turn_count + phase['max_turns']:
                return phase['agent']
            turn_count += phase['max_turns']
        
        # 如果超出了所有阶段，返回CTO进行总结
        cto_agents = [agent for agent in available_agents if 'CTO' in agent.agent_name]
        return cto_agents[0] if cto_agents else available_agents[0]
    
    def _choose_speaker_dynamic(self, current_context: Dict[str, Any], dialogue_history: List[Dict[str, str]], available_agents: List[BaseAgent]) -> BaseAgent:
        """在动态模式下选择发言者"""
        if not dialogue_history:
            # 第一轮，让CTO开始协调
            cto_agents = [agent for agent in available_agents if 'CTO' in agent.agent_name]
            return cto_agents[0] if cto_agents else available_agents[0]
        
        # 分析最近的对话内容和上下文，选择最合适的智能体
        recent_content = dialogue_history[-1]['content'] if dialogue_history else ""
        last_speaker = dialogue_history[-1].get('agent', '') if dialogue_history else ""
        
        # 创建智能体映射
        agent_map = {agent.agent_name: agent for agent in available_agents}
        
        # 智能选择逻辑
        
        # 1. 如果刚开始讨论，按专业领域顺序
        if len(dialogue_history) <= 2:
            # 优先顺序：CTO -> TestAgent -> SolutionPlanningAgent -> CodeAgent (CodeAgent总是最后)
            priority_order = ["CTOAgent", "TestAgent", "SolutionPlanningAgent", "CodeAgent"]
            for agent_name in priority_order:
                if agent_name in agent_map and agent_name != last_speaker:
                    return agent_map[agent_name]
        
        # 2. 根据对话内容智能选择
        content_keywords = {
            "错误": ["TestAgent", "CodeAgent"],
            "测试": ["TestAgent", "CodeAgent"],
            "方案": ["SolutionPlanningAgent", "CTOAgent"],
            "算法": ["SolutionPlanningAgent", "CodeAgent"],
            "实现": ["CodeAgent", "SolutionPlanningAgent"],
            "代码": ["CodeAgent", "SolutionPlanningAgent"],
            "修复": ["CodeAgent", "TestAgent"],
            "分析": ["TestAgent", "SolutionPlanningAgent"],
            "设计": ["SolutionPlanningAgent", "CTOAgent"],
            "决定": ["CTOAgent"],
            "总结": ["CTOAgent"],
            "验证": ["TestAgent", "CodeAgent"],
            "优化": ["SolutionPlanningAgent", "CodeAgent"]
        }
        
        # 查找内容关键词匹配
        for keyword, preferred_agents in content_keywords.items():
            if keyword in recent_content:
                for agent_name in preferred_agents:
                    if agent_name in agent_map and agent_name != last_speaker:
                        return agent_map[agent_name]
        
        # 3. 检查是否需要特定角色介入
        
        # 如果连续两轮都是同一类型的专家在说话，让CTO介入协调
        if len(dialogue_history) >= 2:
            last_two_speakers = [dialogue_history[-1].get('agent', ''), dialogue_history[-2].get('agent', '')]
            if self._are_same_type_agents(last_two_speakers):
                if "CTOAgent" in agent_map and "CTOAgent" not in last_two_speakers:
                    return agent_map["CTOAgent"]
        
        # 如果讨论了错误但还没有修复代码，优先选择CodeAgent
        error_discussed = any("错误" in msg.get('content', '') or "失败" in msg.get('content', '') 
                            for msg in dialogue_history[-3:])
        code_not_provided = not any("<CODE>" in msg.get('content', '') 
                                  for msg in dialogue_history)
        
        if error_discussed and code_not_provided:
            if "CodeAgent" in agent_map and last_speaker != "CodeAgent":
                return agent_map["CodeAgent"]
        
        # 4. 如果已经有了修复代码，让其他专家验证
        if "<CODE>" in recent_content and last_speaker == "CodeAgent":
            validation_order = ["TestAgent", "CTOAgent"]
            for agent_name in validation_order:
                if agent_name in agent_map:
                    return agent_map[agent_name]
        
        # 5. 根据专业领域相关性评分
        agent_scores = {}
        for agent in available_agents:
            agent_name = agent.agent_name
            if agent_name == last_speaker:
                continue  # 避免连续发言
                
            score = 0
            expertise = self.agent_expertise.get(agent_name, {})
            domains = expertise.get('domains', [])
            base_priority = expertise.get('priority', 5)
            
            # 基础优先级
            score += base_priority
            
            # 专业领域匹配
            for domain in domains:
                if domain in recent_content:
                    score += 3
            
            # 上下文相关性
            context_relevance = self._calculate_context_relevance(agent_name, current_context, dialogue_history)
            score += context_relevance
            
            agent_scores[agent_name] = score
        
        # 选择得分最高的智能体
        if agent_scores:
            best_agent_name = max(agent_scores.items(), key=lambda x: x[1])[0]
            return agent_map[best_agent_name]
        
        # 6. 兜底：智能轮询（避免刚发言的智能体）
        available_for_next = [agent for agent in available_agents 
                            if agent.agent_name != last_speaker]
        if available_for_next:
            return available_for_next[len(dialogue_history) % len(available_for_next)]
        
        # 最后的兜底
        return available_agents[len(dialogue_history) % len(available_agents)]
    
    def _are_same_type_agents(self, agent_names: List[str]) -> bool:
        """判断是否是相同类型的智能体"""
        agent_types = {
            "technical": ["SolutionPlanningAgent", "CodeAgent"],
            "quality": ["TestAgent"],
            "management": ["CTOAgent"]
        }
        
        for agent_type, agents in agent_types.items():
            if all(name in agents for name in agent_names if name):
                return True
        return False
    
    def _calculate_context_relevance(self, agent_name: str, current_context: Dict[str, Any], dialogue_history: List[Dict[str, str]]) -> float:
        """计算智能体与当前上下文的相关性"""
        relevance_score = 0.0
        
        # 基于上下文内容计算相关性
        context_text = " ".join([str(v) for v in current_context.values()])
        
        agent_keywords = {
            "CTOAgent": ["决策", "管理", "协调", "总结", "策略"],
            "SolutionPlanningAgent": ["方案", "算法", "设计", "规划", "分析"],
            "CodeAgent": ["代码", "实现", "编程", "函数", "语法"],
            "TestAgent": ["测试", "用例", "验证", "质量"]
        }
        
        keywords = agent_keywords.get(agent_name, [])
        for keyword in keywords:
            if keyword in context_text:
                relevance_score += 1.0
        
        # 基于对话历史计算参与度
        recent_participation = sum(1 for msg in dialogue_history[-5:] 
                                 if msg.get('agent') == agent_name)
        
        # 如果最近参与较少，稍微提高相关性
        if recent_participation == 0:
            relevance_score += 0.5
        elif recent_participation <= 1:
            relevance_score += 0.2
        
        return relevance_score
    
    def _check_discussion_goals_achieved(self, dialogue_history: List[Dict[str, str]], discussion_plan: Dict[str, Any]) -> bool:
        """检查讨论目标是否已达成"""
        if not dialogue_history:
            return False
        
        # 检查最近的消息是否包含结论性内容
        recent_messages = dialogue_history[-2:] if len(dialogue_history) >= 2 else dialogue_history
        
        conclusion_keywords = ["总结", "结论", "决定", "完成", "解决", "确定"]
        
        for msg in recent_messages:
            content = msg.get('content', '')
            if any(keyword in content for keyword in conclusion_keywords):
                return True
        
        # 检查是否有CodeAgent提供了代码（表示完成了修复任务）
        for msg in dialogue_history[-4:]:  # 检查最近4轮（一个完整周期）
            if msg.get('agent') == 'CodeAgent' and '<CODE>' in msg.get('content', ''):
                print("检测到CodeAgent已提供修复代码，目标达成")
                return True
        
        return False
    
    def _detect_circular_discussion(self, dialogue_history: List[Dict[str, str]]) -> bool:
        """检测是否出现循环讨论"""
        if len(dialogue_history) < 4:
            return False
        
        # 检查最近4条消息是否有重复模式
        recent_messages = dialogue_history[-4:]
        contents = [msg.get('content', '') for msg in recent_messages]
        
        # 简单检查：如果连续两轮内容非常相似，可能是循环
        for i in range(len(contents) - 1):
            similarity = self._calculate_content_similarity(contents[i], contents[i + 1])
            if similarity > 0.8:  # 相似度阈值
                return True
        
        return False
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """计算两个内容的相似度"""
        # 简单的相似度计算：基于共同词汇
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)


class GroupDialogue:
    """
    Group Dialogue Tool for facilitating structured conversations between multiple agents
    
    This tool provides a framework for multiple agents to engage in structured dialogue.
    It extends the concept of AgentDialogue to support group discussions with multiple participants.
    The tool itself doesn't generate content, but rather calls the provided agents to generate dialogue content.
    """
    def __init__(
        self,
        verbose: int = 1,
        max_turns: int = 5,
        use_coordinator: bool = True
    ):
        """
        初始化 Group Dialogue Tool
        
        Args:
            verbose: 输出详细程度
            max_turns: 最大对话轮次
            use_coordinator: 是否使用智能协调机制
        """
        self.verbose = verbose
        self.max_turns = max_turns
        self.use_coordinator = use_coordinator
        self.dialogue_sessions = {}  # 存储不同对话的会话ID
        self.stage_sessions = {}  # 存储各个阶段的会话ID
        self.coordinator = None
    
    def set_coordinator(self, coordinator_agent: BaseAgent):
        """设置协调者智能体"""
        self.coordinator = DiscussionCoordinator(coordinator_agent, self.verbose)
    
    def collect_stage_sessions(
        self,
        stage_name: str,
        session_ids: Dict[str, str],
        workflow_id: str = None
    ) -> Dict[str, str]:
        """
        收集特定阶段的会话ID
        
        Args:
            stage_name: 阶段名称
            session_ids: 该阶段各智能体的会话ID字典
            workflow_id: 工作流ID，如果为None则自动生成
            
        Returns:
            包含每个智能体会话ID的字典
        """
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())
        
        # 保存阶段会话信息
        if workflow_id not in self.stage_sessions:
            self.stage_sessions[workflow_id] = {}
        
        self.stage_sessions[workflow_id][stage_name] = session_ids
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print(f"已收集阶段 '{stage_name}' 的 {len(session_ids)} 个智能体会话ID (工作流ID: {workflow_id})")
            print(f"{'='*50}\n")
        
        return session_ids
    
    def get_stage_sessions(
        self,
        stage_name: str,
        workflow_id: str
    ) -> Dict[str, str]:
        """
        获取特定阶段的会话ID
        
        Args:
            stage_name: 阶段名称
            workflow_id: 工作流ID
            
        Returns:
            包含该阶段每个智能体会话ID的字典
        """
        if workflow_id in self.stage_sessions and stage_name in self.stage_sessions[workflow_id]:
            return self.stage_sessions[workflow_id][stage_name]
        return {}
    
    def conduct_group_dialogue(
        self,
        agents: List[BaseAgent],
        agent_session_ids: Dict[str, str],
        discussion_topic: str,
        initial_prompt: str,
        context: Dict[str, Any] = None,
        max_turns: int = None,
        dialogue_id: str = None,
        agent_order: List[int] = None,
        output_prompt: str = None
    ) -> Dict[str, Any]:
        """
        组织多个智能体之间的群组对话
        
        Args:
            agents: 参与对话的智能体列表
            agent_session_ids: 智能体名称到会话ID的映射
            discussion_topic: 讨论主题
            initial_prompt: 初始提示
            context: 对话上下文信息
            max_turns: 最大对话轮次
            dialogue_id: 对话ID，如果为None则自动生成
            agent_order: 智能体发言顺序，如果为None则按顺序循环
            output_prompt: 最终输出提示
            
        Returns:
            包含对话历史和最终输出的字典
        """
        if not agents:
            raise ValueError("必须提供至少一个智能体")
        
        max_turns = max_turns or self.max_turns
        
        # 处理对话ID
        if dialogue_id is None:
            dialogue_id = str(uuid.uuid4())
        
        # 准备对话历史
        dialogue_history = []
        
        # 保存会话信息
        self.dialogue_sessions[dialogue_id] = (agent_session_ids, dialogue_history)
        
        # 准备上下文消息
        context_msg = ""
        if context:
            context_msg = "以下是相关的上下文信息:\n\n"
            for key, value in context.items():
                context_msg += f"## {key}\n{value}\n\n"
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print(f"开始 {len(agents)} 个智能体之间的群组对话 (ID: {dialogue_id})")
            print(f"主题: {discussion_topic}")
            print(f"最大轮次: {max_turns}")
            print(f"使用智能协调: {self.use_coordinator and self.coordinator is not None}")
            print(f"{'='*50}\n")
            print(f"[初始提示]: {initial_prompt}\n")
        
        # 智能协调机制
        discussion_plan = None
        # analysis key——issue
        analysis_key_issue=None
        if self.use_coordinator and self.coordinator:
            # 分析讨论上下文
            analysis = self.coordinator.analyze_discussion_context(discussion_topic, context or {})
            analysis_key_issue=analysis.get("key_issues",'unknown')
            # 规划讨论流程
            discussion_plan = self.coordinator.plan_discussion_flow(analysis, agents)
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"讨论计划类型: {discussion_plan.get('type', 'unknown')}")
                if discussion_plan.get('type') == 'structured':
                    print(f"预计总轮次: {discussion_plan.get('total_estimated_turns', 'unknown')}")
        
        # 对话循环
        for turn in range(max_turns):
            # 智能选择当前发言者
            if self.use_coordinator and self.coordinator and discussion_plan:
                current_agent = self.coordinator.choose_next_speaker(
                    context or {}, dialogue_history, agents, discussion_plan, turn
                )
                
            else:
                # 默认轮询机制
                if agent_order is None:
                    agent_order = list(range(len(agents)))
                agent_idx = agent_order[turn % len(agent_order)]
                current_agent = agents[agent_idx]
            
            current_role = current_agent.agent_name
            
            # 获取当前智能体的会话ID
            session_id = agent_session_ids.get(current_role)
            if not session_id:
                if self.verbose >= VERBOSE_MINIMAL:
                    print(f"警告: 找不到智能体 {current_role} 的会话ID，将创建新会话")
                session_id = current_agent.start_new_session()
                agent_session_ids[current_role] = session_id
            
            # 获取当前agent的讨论任务
            agent_task = self._get_agent_discussion_task(current_role, discussion_topic)
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n--- 轮次 {turn+1}/{max_turns} ---")
                print(f"当前发言者: {current_role}")
                print(f"任务目标: {agent_task}")
                if self.use_coordinator and discussion_plan:
                    if discussion_plan.get('type') == 'structured':
                        phases = discussion_plan.get('phases', [])
                        current_phase = self._get_current_phase(phases, turn)
                        if current_phase:
                            print(f"当前任务: {current_phase.get('task', '未知')}")
            
            # 准备当前智能体的消息
            user_message = ""
            
            if turn == 0:
                # 第一轮，包含初始提示和上下文
                user_message = f"{initial_prompt}\n\n{context_msg}\n\nthe leader's key issue(CTO is the leader) is {analysis_key_issue}\n"
            else:
                # 后续轮次，包含之前的对话历史
                history_text = ""
                for msg in dialogue_history[-min(len(dialogue_history), 3):]:  # 最近3条消息
                    history_text += f"[{msg['agent']}]: {msg['content']}\n\n"
                
                user_message = f"请继续讨论主题: {discussion_topic}\n\n最近的对话历史:\n{history_text}"
                
                # 最后一轮，添加输出提示
                if turn == max_turns - 1 and output_prompt:
                    user_message += f"\n\n{output_prompt}"
            
            # 发送系统+用户角色消息
            messages = [
                {"role": "system", "content": f"你是 {current_role}，正在参与一个关于 '{discussion_topic}' 的群组讨论,你在讨论中的目标是：{agent_task}"},
                {"role": "user", "content": user_message},
                {"role": "user", "content": f"If you are CTOAgent, TestAgent, or SoulutionPlanningAgent, please add <SUGGESTIONS>your final advice</SUGGESTIONS> at the end of your analysis. If you are CodeAgent, please add <CODE>the final code according to the analysis of other members and yours</CODE> at the end of your analysis."}
            ]
            
            # 调用当前智能体生成回复
            start_time = time.time()
            current_agent.set_active_session(session_id)
            response = current_agent._call_model(messages, session_id=session_id, include_history=True)
            elapsed_time = time.time() - start_time
            
            # 解析并提取关键内容
            parsed_content = self._parse_agent_response(response, current_role)
            
            # 记录解析后的内容到共享对话历史
            dialogue_history.append({
                "role": "assistant",
                "content": parsed_content,  # 存储解析后的内容而不是原始回复
                "agent": current_role,
                "time": elapsed_time,
                "turn": turn + 1,
                "original_response": response  # 保留原始回复用于调试（可选）
            })
            
            # 更新会话信息
            self.dialogue_sessions[dialogue_id] = (agent_session_ids, dialogue_history)
            
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n[{current_role}]: {response}")
                print(f"(用时: {elapsed_time:.2f} 秒)")
            
            # 智能判断是否应该继续讨论
            if self.use_coordinator and self.coordinator and discussion_plan:
                print('------\n开始智能判定\n------\n')
                
                # 检查是否完成了一个完整的plan周期
                plan_type = discussion_plan.get('type', 'dynamic')
                
                if plan_type == 'structured':
                    # 结构化模式：检查是否完成了所有阶段
                    phases = discussion_plan.get('phases', [])
                    total_plan_turns = sum(phase.get('max_turns', 1) for phase in phases)
                    
                    # 只在完成完整周期时判定（每个agent发言1次，共4轮）
                    if (turn + 1) % total_plan_turns == 0:
                        print(f"完成一个完整的plan周期 ({total_plan_turns}轮)，开始判定...")
                        if not self.coordinator.should_continue_discussion(dialogue_history, discussion_plan, max_turns):
                            if self.verbose >= VERBOSE_MINIMAL:
                                print(f"\n协调者判断讨论已达成目标，提前结束讨论")
                            break
                    else:
                        print(f"当前轮次 {turn + 1}，未完成完整周期 ({total_plan_turns}轮)，继续讨论...")
                else:
                    # 动态模式：每4轮判定一次（假设有4个agent）
                    if (turn + 1) % len(agents) == 0:
                        print(f"完成一轮所有agent发言 ({len(agents)}轮)，开始判定...")
                        if not self.coordinator.should_continue_discussion(dialogue_history, discussion_plan, max_turns):
                            if self.verbose >= VERBOSE_MINIMAL:
                                print(f"\n协调者判断讨论已达成目标，提前结束讨论")
                            break
                    else:
                        print(f"当前轮次 {turn + 1}，未完成一轮所有agent发言，继续讨论...")
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print(f"{len(agents)} 个智能体之间的群组对话已完成 (ID: {dialogue_id})")
            print(f"{'='*50}\n")
        
        final_output = dialogue_history[-1]["content"] if dialogue_history else ""
        return {
            "history": dialogue_history,
            "final_output": final_output,
            "dialogue_id": dialogue_id,
            "session_ids": agent_session_ids,
            "discussion_plan": discussion_plan
        }
    
    def _parse_agent_response(self, response: str, agent_name: str) -> str:
        """
        解析agent回复，提取关键内容以控制上下文长度
        
        Args:
            response: agent的原始回复
            agent_name: agent名称
            
        Returns:
            解析后的关键内容
        """
        import re
        
        if agent_name == "CodeAgent":
            # CodeAgent: 提取<CODE>标签内容
            code_match = re.search(r'<CODE>(.*?)</CODE>', response, re.DOTALL | re.IGNORECASE)
            if code_match:
                code_content = code_match.group(1).strip()
                return f"[{agent_name}] 提供修复代码:\n<CODE>\n{code_content}\n</CODE>"
            else:
                # 如果没有CODE标签，返回简化的回复
                return f"[{agent_name}] {response[:200]}..." if len(response) > 200 else f"[{agent_name}] {response}"
        
        else:
            # 其他Agent: 提取<SUGGESTIONS>标签内容
            suggestions_match = re.search(r'<SUGGESTIONS>(.*?)</SUGGESTIONS>', response, re.DOTALL | re.IGNORECASE)
            if suggestions_match:
                suggestions_content = suggestions_match.group(1).strip()
                return f"[{agent_name}] 建议:\n<SUGGESTIONS>\n{suggestions_content}\n</SUGGESTIONS>"
            else:
                # 如果没有SUGGESTIONS标签，返回简化的回复（取前200字符）
                return f"[{agent_name}] {response[:200]}..." if len(response) > 200 else f"[{agent_name}] {response}"
    
    def _get_agent_discussion_task(self, agent_name: str, discussion_topic: str) -> str:
        """
        为每个agent定义在讨论中的具体目标和任务
        
        Args:
            agent_name: agent名称
            discussion_topic: 讨论主题
            
        Returns:
            该agent在讨论中的具体任务描述
        """
        task_mapping = {
            "CTOAgent": {
                "code_failure": "作为技术总监，协调整个讨论流程，分析技术决策，确保所有专家意见得到综合考虑，并对最终解决方案进行技术可行性评估",
                "multi_stage_collaboration": "统筹各阶段的协作，识别关键技术问题，协调各专家的建议，确保解决方案的整体一致性",
                "design_review": "从架构和技术管理角度审查设计方案，评估技术风险，提供架构级别的指导意见",
                "test_case_generation": "指导测试策略制定，确保测试覆盖面和测试质量标准的达成",
                "default": "作为技术领导者，协调讨论进程，综合各方意见，确保技术决策的合理性"
            },
            "TestAgent": {
                "code_failure": "从测试角度深入分析代码失败原因，识别边界条件和异常情况，提供详细的错误诊断和测试建议",
                "multi_stage_collaboration": "评估各阶段产出的测试覆盖度，提供测试策略建议，确保代码质量符合测试标准",
                "design_review": "从测试角度评审设计方案，识别潜在的测试难点和质量风险",
                "test_case_generation": "设计全面的测试用例，包括正常情况、边界条件和异常处理的测试场景",
                "default": "从测试和质量保证角度分析问题，提供测试相关的专业建议"
            },
            "SolutionPlanningAgent": {
                "code_failure": "分析代码失败的根本原因，设计技术解决方案，提供算法优化和架构改进建议",
                "multi_stage_collaboration": "整合各阶段的技术需求，制定统一的技术实现方案，确保方案的技术可行性",
                "design_review": "从技术实现角度评审设计方案，提供算法选择和性能优化建议",
                "test_case_generation": "从技术实现角度分析测试需求，确保测试用例覆盖关键算法逻辑",
                "default": "从技术方案设计角度分析问题，提供系统性的解决方案"
            },
            "CodeAgent": {
                "code_failure": "根据其他专家的分析和建议，实现具体的代码修复，确保修复后的代码能通过所有测试用例",
                "multi_stage_collaboration": "将各阶段的建议转化为具体的代码实现，确保代码质量和功能完整性",
                "design_review": "将设计方案转化为可执行的代码，确保实现与设计的一致性",
                "test_case_generation": "实现支持测试用例执行的代码结构，确保代码可测试性",
                "default": "将讨论中的建议转化为具体的代码实现，确保代码的正确性和可维护性"
            }
        }
        
        # 根据讨论主题确定具体的任务类型
        task_type = "default"
        if "code failure" in discussion_topic.lower() or "fix code" in discussion_topic.lower():
            task_type = "code_failure"
        elif "multi-stage" in discussion_topic.lower() or "collaboration" in discussion_topic.lower():
            task_type = "multi_stage_collaboration"
        elif "design" in discussion_topic.lower() or "review" in discussion_topic.lower():
            task_type = "design_review"
        elif "test case" in discussion_topic.lower() or "testing" in discussion_topic.lower():
            task_type = "test_case_generation"
        
        return task_mapping.get(agent_name, {}).get(task_type, task_mapping.get(agent_name, {}).get("default", "参与讨论并提供专业建议"))

    def _get_current_phase(self, phases: List[Dict[str, Any]], current_turn: int) -> Optional[Dict[str, Any]]:
        """获取当前轮次对应的阶段"""
        turn_count = 0
        for phase in phases:
            if current_turn < turn_count + phase['max_turns']:
                return phase
            turn_count += phase['max_turns']
        return None
    
    def get_dialogue_session(self, dialogue_id: str) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
        """
        获取对话会话信息
        
        Args:
            dialogue_id: 对话ID
            
        Returns:
            (会话ID字典, 对话历史)
        """
        if dialogue_id in self.dialogue_sessions:
            return self.dialogue_sessions[dialogue_id]
        else:
            return {}, []
    
    def clear_dialogue_session(self, dialogue_id: str) -> bool:
        """
        清除对话会话
        
        Args:
            dialogue_id: 对话ID
            
        Returns:
            是否成功清除
        """
        if dialogue_id in self.dialogue_sessions:
            del self.dialogue_sessions[dialogue_id]
            return True
        else:
            return False
    
    def summarize_group_dialogue(
        self,
        dialogue_history: List[Dict[str, str]],
        summarizer_agent: BaseAgent,
        summary_prompt: str = None,
        topic: str = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        使用指定的智能体总结群组对话内容
        
        Args:
            dialogue_history: 对话历史记录
            summarizer_agent: 用于总结的智能体
            summary_prompt: 总结提示，如果为None，则使用默认提示
            topic: 对话主题，用于生成更具体的总结提示
            session_id: 会话ID，如果为None则创建新会话
            
        Returns:
            对话总结，包含原始总结文本和结构化信息
        """
        if not summary_prompt:
            summary_prompt = f"""请总结以下关于"{topic or '此主题'}"的群组讨论

请分析讨论内容，提取以下信息:
1. 主要讨论点和关键观点
2. 各方达成的共识
3. 存在的分歧或未解决的问题
4. 提出的解决方案或建议
5. 最终确定的技术方法和实施策略

请以结构化方式组织您的总结，确保其简洁、全面且客观。

讨论历史:
{{dialogue_text}}
"""
        
        # 构建对话文本
        dialogue_text = ""
        for msg in dialogue_history:
            if "agent" in msg:
                turn_info = f"(轮次 {msg.get('turn', '?')})" if "turn" in msg else ""
                dialogue_text += f"[{msg['agent']} {turn_info}]: {msg['content']}\n\n"
            elif "role" in msg and msg["role"] != "system":
                dialogue_text += f"[{msg['role']}]: {msg['content']}\n\n"
        
        # 构建总结提示
        messages = [
            {"role": "system", "content": "你是一位专业的对话总结者，擅长从对话中提取关键信息、共识和分歧。"},
            {"role": "user", "content": summary_prompt.format(dialogue_text=dialogue_text)}
        ]
        
        # 调用总结智能体
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{'='*50}")
            print(f"生成群组对话总结...")
            
        # 创建新会话或使用指定会话
        if session_id is None:
            session_id = summarizer_agent.start_new_session()
        else:
            summarizer_agent.set_active_session(session_id)
            
        summary = summarizer_agent._call_model(messages, session_id=session_id, include_history=False)
        
        # 尝试提取结构化信息
        import re
        import json
        
        # 寻找JSON格式的内容
        json_match = re.search(r'```json\s*(.*?)\s*```', summary, re.DOTALL)
        structured_data = None
        
        if json_match:
            try:
                json_str = json_match.group(1)
                structured_data = json.loads(json_str)
            except (json.JSONDecodeError, IndexError):
                pass
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n对话总结:")
            print(f"{summary[:500]}..." if len(summary) > 500 else summary)
            print(f"{'='*50}\n")
            
        return {
            "summary": summary,
            "structured_data": structured_data,
            "topic": topic,
            "session_id": session_id
        }