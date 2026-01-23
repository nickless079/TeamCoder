# 状态机驱动的三角色协作调试系统

## 概述

这是一个基于状态机的智能调试系统，通过三个核心角色的协作来解决编程问题：

- **SolutionAgent (Planner)**: 逻辑与策略的制定者
- **CodeAgent (Coder)**: 策略的实现者
- **Orchestrator (Director)**: 流程的守护者、质量的控制者、异常的处理者

## 系统架构

### 五个核心节点

1. **NODE_DIAGNOSIS** - 根本原因诊断

   - 🎯 目标: 准确、深刻地识别问题根本原因
   - 👥 参与者: SolutionAgent + Orchestrator
   - 🔍 质量门控: LLM评估分析深度
2. **NODE_BLUEPRINT_DESIGN** - 蓝图设计与审查

   - 🎯 目标: 通过多轮讨论设计认可的逻辑严谨蓝图
   - 👥 参与者: SolutionAgent + CodeAgent + Orchestrator
   - 🔍 质量门控: 批准意图识别 + 重复检测
3. **NODE_STRESS_TESTING** - 蓝图压力测试

   - 🎯 目标: 理论推演确保蓝图处理各种边界情况
   - 👥 参与者: SolutionAgent(QA+审查者) + Orchestrator
   - 🔍 质量门控: 验证分析评估
4. **NODE_IMPLEMENTATION** - 最终代码实现

   - 🎯 目标: 将蓝图准确翻译成可执行Python代码
   - 👥 参与者: CodeAgent + Orchestrator
   - 🔍 质量门控: 格式验证
5. **NODE_VALIDATION** - 自动验证 与裁决

   - 🎯 目标: 实机测试，最终"通过"或"失败"裁决
   - 👥 参与者: Orchestrator(唯一行动者)
   - 🔍 质量门控: 代码执行验证

### 智能回滚机制

- **压力测试失败** → 回滚到蓝图设计
- **验证失败** → 回滚到诊断阶段（携带完整历史）

## 快速开始

### 1. 基本使用

```python
from models.AlibabaModel import AlibabaModel
from agents.planning.SolutionPlanningAgent import SolutionPlanningAgent
from agents.core.CodeAgent import CodeAgent
from utils.dialogue import StateMachineOrchestrator

# 初始化模型和智能体
model = AlibabaModel(model_name="qwen3-4b", api_key="your-key")
solution_agent = SolutionPlanningAgent(model=model)
code_agent = CodeAgent(model=model)

# 创建协调器
orchestrator = StateMachineOrchestrator(
    solution_agent=solution_agent,
    code_agent=code_agent,
    quality_model=model,
    verbose=1
)

# 执行调试
result = orchestrator.debug_problem(
    problem_description="编写一个计算斐波那契数列的函数...",
    test_cases=[
        {"assertion": "assert fibonacci(5) == 5"},
        {"assertion": "assert fibonacci(10) == 55"}
    ],
    current_code="def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
    error_logs="RecursionError: maximum recursion depth exceeded"
)

if result["success"]:
    print("调试成功!")
    print("最终代码:", result["final_code"])
else:
    print("调试失败:", result["error"])
```

### 2. 运行示例

```bash
cd src/utils/dialogue
python example.py
```

## 核心特性

### 🧠 智能质量门控

- 使用LLM评估诊断分析深度
- 智能识别批准意图
- 自动检测重复讨论

### 🔄 强大的回滚机制

- 节点级别的智能回滚
- 失败时自动注入上下文信息
- 多次重启机制应对复杂问题

### 📊 完整的执行追踪

- 详细的节点执行历史
- 时间统计和性能分析
- 错误原因追踪

### 🛡️ 鲁棒性设计

- 格式验证和错误处理
- 最大轮次限制防止无限循环
- 优雅的异常处理

## 配置说明

### 环境变量

```bash
export ALIBABA_API_KEY="your-alibaba-api-key"
# 或者使用
export DASHSCOPE_API_KEY="your-dashscope-api-key"
```

### 参数调优

```python
# 协调器参数
orchestrator = StateMachineOrchestrator(
    solution_agent=solution_agent,
    code_agent=code_agent,
    quality_model=model,
    verbose=1  # 0: 静默, 1: 基本, 2: 详细
)

# 在节点实现中调整
max_turns = 10  # 节点内最大对话轮数
max_restart_attempts = 2  # 最大重启次数
```

## 扩展指南

### 添加新节点

1. 继承 `DebugNode` 基类
2. 实现 `execute()` 方法
3. 在 `orchestrator.py` 中注册节点

### 自定义质量门控

1. 扩展 `QualityGate` 类
2. 添加新的评估方法
3. 在节点中调用评估

### 集成新智能体

1. 确保智能体继承 `BaseAgent`
2. 在 `AgentRole` 枚举中添加角色
3. 更新协调器的智能体映射

## 故障排除

### 常见问题

1. **API密钥错误**

   ```
   1. **API密钥错误**
   ```
   确保设置了正确的 ALIBABA_API_KEY 或 DASHSCOPE_API_KEY 环境变量
   ```
   ```
2. **导入错误**

   ```python
   # 确保项目根目录在Python路径中
   import sys
   sys.path.append('/path/to/TeamCoder/src')
   ```
3. **节点执行超时**

   ```python
   # 调整节点内最大轮次
   node.max_turns = 15
   ```

### 调试模式

```python
# 启用详细日志
orchestrator = StateMachineOrchestrator(..., verbose=2)

# 查看执行历史
summary = orchestrator.get_execution_summary()
print(summary)
```

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 许可证

本项目基于 MIT 许可证开源。
