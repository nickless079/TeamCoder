from typing import Dict, Any, List, Optional
from models.Base import BaseModel
from constants.verboseType import *
from strategies.prompt_loader import prompt_loader

class BaseAgent:
    """
    基础智能体类，所有具体智能体实现的父类
    """
    def __init__(
        self,
        model: BaseModel,
        verbose: int = 1,
        enabled: bool = True,
        agent_name: str = "BaseAgent",
        prompt_module_path: str = None,
    ):
        """
        初始化基础智能体
        
        Args:
            model: 模型实例
            verbose: 输出详细程度
            enabled: 是否启用该智能体
            agent_name: 智能体名称
            prompt_module_path: prompt 模块路径，例如 "core.attention"
        """
        self.model = model
        self.verbose = verbose
        self.enabled = enabled
        self.agent_name = agent_name
        
        # Prompt 模块管理
        self._prompt_module_path = prompt_module_path
        self._prompt_module = None  # 懒加载
        
        # 添加会话状态管理
        self.conversation_history = {}  # 使用字典存储多个会话的历史记录
        self.current_session_id = None  # 当前活跃的会话ID
    
    @property
    def prompt_module(self):
        """
        懒加载 prompt 模块
        
        Returns:
            对应策略的 prompt 模块
        """
        if self._prompt_module is None and self._prompt_module_path:
            self._prompt_module = prompt_loader.get_prompt_module(
                self._prompt_module_path
            )
        return self._prompt_module
        
    def _generate_prompt(self, **kwargs) -> List[Dict[str, str]]:
        """
        生成提示
        
        Args:
            **kwargs: 提示参数
            
        Returns:
            消息列表，每个消息是包含'role'和'content'的字典
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        处理模型响应
        
        Args:
            response: 模型响应文本
            
        Returns:
            处理后的结果
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def start_new_session(self, session_id: str = None) -> str:
        """
        开始一个新的会话
        
        Args:
            session_id: 会话ID，如果为None则自动生成
            
        Returns:
            会话ID
        """
        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())
            
        self.current_session_id = session_id
        self.conversation_history[session_id] = []
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} - 开始新会话: {session_id}")
            
        return session_id
    
    def set_active_session(self, session_id: str) -> bool:
        """
        设置当前活跃的会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功设置
        """
        if session_id in self.conversation_history:
            self.current_session_id = session_id
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{self.agent_name} - 切换到会话: {session_id}")
            return True
        else:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{self.agent_name} - 会话 {session_id} 不存在")
            return False
    
    def get_conversation_history(self, session_id: str = None) -> List[Dict[str, str]]:
        """
        获取指定会话的历史记录
        
        Args:
            session_id: 会话ID，如果为None则使用当前会话
            
        Returns:
            会话历史记录
        """
        session_id = session_id or self.current_session_id
        return self.conversation_history.get(session_id, [])
    
    def _call_model(self, messages: List[Dict[str, str]], session_id: str = None, include_history: bool = True) -> str:
        """
        调用模型，并更新会话历史
        
        Args:
            messages: 消息列表
            session_id: 会话ID，如果为None则使用当前会话
            include_history: 是否包含历史消息
            
        Returns:
            模型响应文本
        """
      
        session_id = session_id or self.current_session_id
        print('the _call_modal is current_session_id:',self.current_session_id,'\n')
        print('the _call_model is session_id:', session_id,'\n')
        print('the _call_model is session_id  in self.conversation_history:',session_id  in self.conversation_history,'\n')
        if self.verbose >= VERBOSE_FULL:
            # 多行枚举行打印，保留换行，避免单行长日志
            print("the _call_model is messages:")
            for i, m in enumerate(messages, 1):
                role = m.get("role", "?")
                content = m.get("content", "")
                print(f"\n[{i}] role={role}\ncontent:\n{content}\n" + "-"*60)
        
        # 如果没有活跃会话，创建一个新会话
        if session_id is None:
            session_id = self.start_new_session()
        elif session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
            
        # 准备发送给模型的消息
        full_messages = []
        
        # 如果需要包含历史记录
        if include_history and session_id in self.conversation_history:
            # 获取系统消息（如果有）
            system_messages = [msg for msg in messages if msg['role'] == 'system']
            
            # 添加系统消息
            full_messages.extend(system_messages)
            
            # 添加历史记录（排除系统消息）
            full_messages.extend(self.conversation_history[session_id])
            
            # 添加新消息（排除系统消息）
            user_messages = [msg for msg in messages if msg['role'] != 'system']
            full_messages.extend(user_messages)
        else:
            full_messages = messages
            
        if self.verbose >= VERBOSE_FULL:
            print(f"\n{self.agent_name} - 调用模型:")

        
        response = self.model.chat(full_messages)
        
        # 更新会话历史
        # 保存用户消息（排除系统消息）
        for msg in messages:
            if msg['role'] != 'system':
                self.conversation_history[session_id].append(msg)
                
        # 保存助手回复
        self.conversation_history[session_id].append({
            "role": "assistant",
            "content": response
        })
        
        if self.verbose >= VERBOSE_FULL:
            print(f"\n{self.agent_name} - 模型响应:")
            print(response)  # 打印完整响应
        elif self.verbose >= VERBOSE_MINIMAL:
            # 在VERBOSE_MINIMAL模式下只打印前200个字符
            print(f"\n{self.agent_name} - 模型响应:")
            print(f"{response[:200]}..." if len(response) > 200 else response)
            
        return response
    
    def execute(self, session_id: str = None, include_history: bool = True, **kwargs) -> Dict[str, Any]:
        """
        执行智能体任务
        
        Args:
            session_id: 会话ID，如果为None则使用当前会话
            include_history: 是否包含历史消息
            **kwargs: 任务参数
            
        Returns:
            执行结果
        """
        if not self.enabled:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"{self.agent_name} 已禁用，跳过执行")
            return {"status": "disabled", "result": None}
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"\n{self.agent_name} 开始执行...")
            
        messages = self._generate_prompt(**kwargs)
        response = self._call_model(messages, session_id=session_id, include_history=include_history)
        result = self._process_response(response)
        
        if self.verbose >= VERBOSE_MINIMAL:
            print(f"{self.agent_name} 执行完成")
            
        return {"status": "success", "result": result, "session_id": session_id or self.current_session_id}
    
    def clear_session(self, session_id: str = None) -> bool:
        """
        清除指定会话的历史记录
        
        Args:
            session_id: 会话ID，如果为None则清除当前会话
            
        Returns:
            是否成功清除
        """
        session_id = session_id or self.current_session_id
        if session_id in self.conversation_history:
            self.conversation_history[session_id] = []
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{self.agent_name} - 已清除会话 {session_id} 的历史记录")
            return True
        else:
            if self.verbose >= VERBOSE_MINIMAL:
                print(f"\n{self.agent_name} - 会话 {session_id} 不存在")
            return False 