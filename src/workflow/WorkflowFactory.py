from typing import Optional
from .BaseWorkflow import BaseWorkflow
from .TeamCoderWorkflow import TeamCoderWorkflow
from .TeamCoderWorkflowV1 import TeamCoderWorkflowV1
from .CoTWorkflow import CoTWorkflow
from .DirectWorkflow import DirectWorkflow
from .SelfPlanningWorkflow import SelfPlanningWorkflow
from .AnalogicalWorkflow import AnalogicalWorkflow
from .MapCoderWorkflow import MapCoderWorkflow
from .CodeSIMWorkflow import CodeSIMWorkflow

from models.Base import BaseModel
from datasets.Dataset import Dataset
from utils.results import Results

class WorkflowFactory:
    """
    工作流工厂类，用于创建不同类型的工作流实例
    """
    @staticmethod
    def get_workflow(
        model: BaseModel,
        dataset: Dataset,
        language: str,
        pass_at_k: int = 1,
        results: Optional[Results] = None,
        verbose: int = 1,
        web_search: bool = True,
        docker_execution: bool = True,
        workflow_type: str = "teamcoderworkflow",
        start_index: int = 0,  # 添加start_index参数
    ) -> BaseWorkflow:
        """
        获取工作流实例
        
        Args:
            model: 模型实例
            dataset: 数据集实例
            language: 编程语言
            pass_at_k: 评估时的pass@k值
            results: 结果记录器实例
            verbose: 输出详细程度
            web_search: 是否启用网络搜索
            docker_execution: 是否使用Docker执行验证
            workflow_type: 工作流类型 ("teamcoderworkflow", "teamcoderworkflowv1", "cotworkflow", "directworkflow", "selfplanningworkflow", "analogicalworkflow", "mapcoderworkflow", "codesimworkflow")
            start_index: 开始处理的数据集索引，默认为0
            
        Returns:
            工作流实例
        """
        # 根据workflow_type选择对应的工作流
        if workflow_type.lower() == "teamcoderworkflowv1":
            return TeamCoderWorkflowV1(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "teamcoderworkflowwodirect":
            from .variation.TeamCoderWorkflowWOdirect import TeamCoderWorkflowWOdirect
            return TeamCoderWorkflowWOdirect(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "teamcoderworkflowwoattention":
            from .variation.TeamCoderWorkflowWOattention import TeamCoderWorkflowWOattention
            return TeamCoderWorkflowWOattention(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "teamcoderworkflowwomidterm":
            from .variation.TeamCoderWorkflowWOmidterm import TeamCoderWorkflowWOmidterm
            return TeamCoderWorkflowWOmidterm(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "teamcoderworkflowwotimeout":
            from .variation.TeamCoderWorkflowWOtimeout import TeamCoderWorkflowWOtimeout
            return TeamCoderWorkflowWOtimeout(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "cotworkflow":
            return CoTWorkflow(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "directworkflow":
            return DirectWorkflow(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "selfplanningworkflow":
            return SelfPlanningWorkflow(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "analogicalworkflow":
            return AnalogicalWorkflow(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "mapcoderworkflow":
            return MapCoderWorkflow(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        elif workflow_type.lower() == "codesimworkflow":
            return CodeSIMWorkflow(
                model=model,
                dataset=dataset,
                language=language,
                pass_at_k=pass_at_k,
                results=results,
                verbose=verbose,
                web_search=web_search,
                docker_execution=docker_execution,
                start_index=start_index,
            )
        else:  # 默认使用原版TeamCoderWorkflow
            return TeamCoderWorkflow(
            model=model,
            dataset=dataset,
            language=language,
            pass_at_k=pass_at_k,
            results=results,
            verbose=verbose,
            web_search=web_search,
            docker_execution=docker_execution,
            start_index=start_index,
        ) 