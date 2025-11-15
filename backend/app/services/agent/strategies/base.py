"""
执行策略基类

定义所有操作执行策略的通用接口。
"""
from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime

from app.schemas.modification_schemas import (
    OperationStep,
    Operation,
    ConversationMemory
)


class ExecutionStrategy(ABC):
    """
    执行策略基类
    
    所有具体的执行策略都继承自此类,实现execute方法。
    
    策略模式允许我们为不同类型的操作提供不同的执行逻辑,
    同时保持统一的接口。
    """
    
    @abstractmethod
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        """
        执行操作步骤
        
        Args:
            step: 操作步骤
            memory: 对话记忆（包含当前状态）
        
        Returns:
            Operation: 执行结果
        
        Raises:
            Exception: 执行失败时抛出异常
        """
        pass
    
    def _create_operation_result(
        self,
        operation_type: str,
        details: Any,
        success: bool = True,
        error_message: str = None,
        duration_ms: int = None,
        cost_usd: float = None
    ) -> Operation:
        """
        创建操作结果对象
        
        辅助方法,用于构建标准的Operation对象。
        
        Args:
            operation_type: 操作类型
            details: 操作详情对象
            success: 是否成功
            error_message: 错误消息（如果失败）
            duration_ms: 执行时长（毫秒）
            cost_usd: LLM调用成本（美元）
        
        Returns:
            Operation: 操作对象
        """
        return Operation(
            operation_type=operation_type,
            details=details,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            cost_usd=cost_usd
        )

