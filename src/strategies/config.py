"""
策略配置：定义 strategy → workflow_type 和 prompts_package 的映射
"""

STRATEGY_CONFIG = {
    "teamcoder": {
        "workflow_type": "teamcoderworkflowv1",
        "prompts_package": "prompts.teamcoder",
        "description": "TeamCoder 原始策略 - 基于 Arbiter 的多智能体协作"
    },
    "teamcoderwodirect": {
        "workflow_type": "teamcoderworkflowwodirect",
        "prompts_package": "prompts.teamcoder",
        "description": "TeamCoder 无 Direct 策略 - 去除 Direct Agent"
    },
    "teamcoderwoattention": {
        "workflow_type": "teamcoderworkflowwoattention",
        "prompts_package": "prompts.teamcoder",
        "description": "TeamCoder 无 Attention 策略 - 去除 Attention Agent"
    },
    "teamcoderwomidterm": {
        "workflow_type": "teamcoderworkflowwomidterm",
        "prompts_package": "prompts.teamcoder",
        "description": "TeamCoder 无 Midterm 策略 - 去除 Midterm Agent"
    },
    "teamcoderwotimeout": {
        "workflow_type": "teamcoderworkflowwotimeout",
        "prompts_package": "prompts.teamcoder",
        "description": "TeamCoder 无 Timeout 策略 - 去除 Timeout Agent"
    },
    "cot": {
        "workflow_type": "cotworkflow",
        "prompts_package": "prompts.cot",
        "description": "Chain-of-Thought (CoT) 策略 - 使用思维链推理生成代码"
    },
    "direct": {
        "workflow_type": "directworkflow",
        "prompts_package": "prompts.direct",
        "description": "Direct 策略 - 直接生成代码，不使用 few-shot examples"
    },
    "selfplanning": {
        "workflow_type": "selfplanningworkflow",
        "prompts_package": "prompts.selfplanning",
        "description": "SelfPlanning 策略 - 先规划步骤，再根据步骤生成代码"
    },
    "analogical": {
        "workflow_type": "analogicalworkflow",
        "prompts_package": "prompts.analogical",
        "description": "Analogical 策略 - 通过类比学习：识别算法、写教程、提供例子"
    },
    "mapcoder": {
        "workflow_type": "mapcoderworkflow",
        "prompts_package": "prompts.mapcoder",
        "description": "MapCoder 策略 - 知识库+例子+规划+验证+代码+测试改进"
    },
    "codesim": {
        "workflow_type": "codesimworkflow",
        "prompts_package": "prompts.codesim",
        "description": "CodeSIM 策略 - 规划+模拟验证+代码生成+多轮调试优化"
    },
    # 后续可以添加更多策略
    # "your_strategy": {
    #     "workflow_type": "teamcoderworkflowv1",
    #     "prompts_package": "prompts.your_strategy",
    #     "description": "您的策略描述"
    # }
}

def get_strategy_config(strategy_name: str) -> dict:
    """
    获取策略配置
    
    Args:
        strategy_name: 策略名称
        
    Returns:
        策略配置字典，包含 workflow_type 和 prompts_package
        
    Raises:
        ValueError: 如果策略不存在
    """
    if strategy_name not in STRATEGY_CONFIG:
        available = list(STRATEGY_CONFIG.keys())
        raise ValueError(
            f"❌ 未知策略: {strategy_name}\n"
            f"   可用策略: {available}"
        )
    return STRATEGY_CONFIG[strategy_name]

def list_strategies() -> list:
    """
    列出所有可用策略
    
    Returns:
        策略名称列表
    """
    return list(STRATEGY_CONFIG.keys())

