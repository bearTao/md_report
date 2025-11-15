"""
操作执行器

本模块负责执行具体的操作步骤,根据操作类型选择合适的执行策略。

职责:
- 根据操作类型分发到对应的执行策略
- 协调执行流程
- 收集执行结果
"""
from typing import List, Dict
from sqlalchemy.orm import Session
import logging

from app.services.agent.strategies.base import ExecutionStrategy
from app.services.agent.strategies.parameter_update import ParameterUpdateStrategy
from app.services.agent.strategies.ai_refinement import AIRefinementStrategy
from app.services.agent.strategies.template_modification import TemplateModificationStrategy
from app.schemas.modification_schemas import (
    OperationStep,
    Operation,
    OperationType,
    ConversationMemory
)

logger = logging.getLogger(__name__)


class OperationExecutor:
    """
    操作执行器类
    
    根据操作类型选择合适的策略并执行操作。
    
    采用策略模式,为每种操作类型提供专门的执行策略。
    
    Attributes:
        db: 数据库会话
        strategies: 策略字典,映射操作类型到执行策略
    """
    
    def __init__(self, db: Session):
        """
        初始化操作执行器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        
        # 初始化模板修改策略实例
        template_strategy = TemplateModificationStrategy(db)
        
        # 初始化策略字典
        self.strategies: Dict[OperationType, ExecutionStrategy] = {
            OperationType.UPDATE_PARAMETER: ParameterUpdateStrategy(db),
            OperationType.REFINE_AI_CONTENT: AIRefinementStrategy(db),  # Phase 3
            OperationType.ADD_SECTION: template_strategy,  # Phase 4
            OperationType.MODIFY_SECTION: template_strategy,
            OperationType.REMOVE_SECTION: template_strategy,
        }
    
    async def execute(
        self,
        steps: List[OperationStep],
        memory: ConversationMemory
    ) -> List[Operation]:
        """
        执行操作步骤列表
        
        按顺序执行所有操作步骤,收集结果。
        
        Args:
            steps: 操作步骤列表
            memory: 对话记忆
        
        Returns:
            List[Operation]: 操作结果列表
        """
        results = []
        
        for step in steps:
            try:
                logger.info(
                    f"执行步骤 {step.step_number}: {step.description} "
                    f"(类型: {step.operation_type})"
                )
                
                # 获取对应的执行策略
                strategy = self.strategies.get(step.operation_type)
                
                if not strategy:
                    # 策略未实现
                    error_msg = f"操作类型 {step.operation_type} 的策略尚未实现"
                    logger.error(error_msg)
                    
                    # 创建失败的操作结果
                    from app.schemas.modification_schemas import ParameterUpdateDetails
                    failed_operation = Operation(
                        operation_type=step.operation_type,
                        details=ParameterUpdateDetails(
                            variable_name=step.target_variable or "unknown",
                            old_value=None,
                            new_value=None,
                            dependent_variables=[]
                        ),
                        success=False,
                        error_message=error_msg
                    )
                    results.append(failed_operation)
                    continue
                
                # 执行操作
                result = await strategy.execute(step, memory)
                results.append(result)
                
                # 如果操作失败,记录日志但继续执行后续步骤
                # (某些步骤失败不应该阻止其他独立步骤的执行)
                if not result.success:
                    logger.warning(
                        f"步骤 {step.step_number} 执行失败: {result.error_message}"
                    )
            
            except Exception as e:
                logger.exception(f"执行步骤 {step.step_number} 时发生异常: {str(e)}")
                
                # 创建失败的操作结果
                from app.schemas.modification_schemas import ParameterUpdateDetails
                failed_operation = Operation(
                    operation_type=step.operation_type,
                    details=ParameterUpdateDetails(
                        variable_name=step.target_variable or "unknown",
                        old_value=None,
                        new_value=None,
                        dependent_variables=[]
                    ),
                    success=False,
                    error_message=f"执行异常: {str(e)}"
                )
                results.append(failed_operation)
        
        # 统计执行结果
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        
        logger.info(
            f"操作执行完成: {success_count}/{total_count} 成功, "
            f"{total_count - success_count} 失败"
        )
        
        return results
    
    def add_strategy(
        self,
        operation_type: OperationType,
        strategy: ExecutionStrategy
    ) -> None:
        """
        添加新的执行策略
        
        允许动态添加新的操作类型支持。
        
        Args:
            operation_type: 操作类型
            strategy: 执行策略实例
        """
        self.strategies[operation_type] = strategy
        logger.info(f"添加执行策略: {operation_type}")

