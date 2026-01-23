from typing import Type
from .Dataset import Dataset

# 动态导入，避免循环导入
def get_dataset_class(name):
    if name.lower() == "humaneval":
        from .HumanEvalDataset import HumanEvalDataset
        return HumanEvalDataset
    elif name.lower() == "mbpp":
        from .MBPPDataset import MBPPDataset
        return MBPPDataset
    elif name.lower() == "apps":
        from .APPSDataset import APPSDataset
        return APPSDataset
    elif name.lower() in ["xcode", "xcodeeval"]:
        from .XCodeDataset import XCodeDataset
        return XCodeDataset
    else:
        raise Exception(f"未知的数据集名称: {name}")

class DatasetFactory:
    """
    数据集工厂类，用于创建不同类型的数据集实例
    """
    @staticmethod
    def get_dataset_class(dataset_name: str) -> Type[Dataset]:
        """
        根据数据集名称获取对应的数据集类
        
        Args:
            dataset_name: 数据集名称
            
        Returns:
            对应的数据集类
            
        Raises:
            Exception: 如果提供的数据集名称未知
        """
        return get_dataset_class(dataset_name) 