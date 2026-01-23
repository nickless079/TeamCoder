import json
from typing import List, Dict, Any, Optional, TextIO

def read_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """
    读取JSONL文件
    
    Args:
        file_path: JSONL文件路径
        
    Returns:
        包含JSON对象的列表
    """
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:  # 跳过空行
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"解析JSON行时出错: {line}\n错误: {e}")
    return data

def write_jsonl(file_path: str, data: List[Dict[str, Any]]) -> None:
    """
    将数据写入JSONL文件
    
    Args:
        file_path: JSONL文件路径
        data: 要写入的数据列表
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def append_jsonl(file_path: str, item: Dict[str, Any]) -> None:
    """
    将单个数据项追加到JSONL文件
    
    Args:
        file_path: JSONL文件路径
        item: 要追加的数据项
    """
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

class JsonlWriter:
    """
    JSONL文件写入器，支持流式写入
    """
    def __init__(self, file_path: str, mode: str = 'w'):
        """
        初始化JSONL文件写入器
        
        Args:
            file_path: JSONL文件路径
            mode: 文件打开模式，'w'表示覆盖，'a'表示追加
        """
        self.file_path = file_path
        self.file: Optional[TextIO] = None
        self.mode = mode
        
    def __enter__(self) -> 'JsonlWriter':
        """
        上下文管理器入口
        
        Returns:
            JSONL文件写入器实例
        """
        self.file = open(self.file_path, self.mode, encoding='utf-8')
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        上下文管理器退出
        """
        if self.file:
            self.file.close()
            self.file = None
            
    def write(self, item: Dict[str, Any]) -> None:
        """
        写入单个数据项
        
        Args:
            item: 要写入的数据项
        """
        if self.file:
            self.file.write(json.dumps(item, ensure_ascii=False) + '\n')
        else:
            raise ValueError("文件未打开，请使用上下文管理器或手动调用open方法") 