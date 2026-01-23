"""
Prompt 动态加载器（全局单例）
用于根据当前策略动态加载对应的 prompt 模块
"""
import importlib
from typing import Any, Optional

class PromptLoader:
    """全局 Prompt 加载器（单例模式）"""
    
    _instance: Optional['PromptLoader'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._current_strategy: Optional[str] = None
        self._prompts_package: Optional[str] = None
        self._cache = {}  # 模块缓存
        self._initialized = True
    
    def initialize(self, strategy_name: str, prompts_package: str):
        """
        初始化 Prompt 加载器
        
        Args:
            strategy_name: 策略名称
            prompts_package: prompts 包路径，例如 "prompts.teamcoder"
        """
        self._current_strategy = strategy_name
        self._prompts_package = prompts_package
        self._cache.clear()
        
        print(f"✅ Prompt 加载器已初始化")
        print(f"   策略: {strategy_name}")
        print(f"   Prompts 包: {prompts_package}")
    
    def get_prompt_module(self, module_path: str) -> Any:
        """
        获取 prompt 模块
        
        Args:
            module_path: 模块相对路径，例如 "core.attention"
            
        Returns:
            对应的 prompt 模块
            
        Example:
            >>> loader = PromptLoader()
            >>> loader.initialize("teamcoder", "prompts.teamcoder")
            >>> attention_prompts = loader.get_prompt_module("core.attention")
            >>> messages = attention_prompts.get_messages(...)
        """
        if not self._prompts_package:
            raise RuntimeError(
                "❌ Prompt 加载器未初始化\n"
                "   请先调用 prompt_loader.initialize(strategy_name, prompts_package)"
            )
        
        # 检查缓存
        if module_path in self._cache:
            return self._cache[module_path]
        
        # 动态导入模块
        full_path = f"{self._prompts_package}.{module_path}"
        try:
            module = importlib.import_module(full_path)
            self._cache[module_path] = module
            return module
        except ImportError as e:
            raise ImportError(
                f"❌ 无法加载 prompt 模块\n"
                f"   完整路径: {full_path}\n"
                f"   当前策略: {self._current_strategy}\n"
                f"   错误详情: {e}"
            )
    
    @property
    def current_strategy(self) -> Optional[str]:
        """获取当前策略名称"""
        return self._current_strategy


# 全局单例实例
prompt_loader = PromptLoader()

