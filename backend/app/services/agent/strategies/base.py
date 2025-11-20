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
    
    ## 错误处理策略（统一规范）
    
    为了保持错误处理的一致性，所有ExecutionStrategy子类必须遵循以下规范：
    
    1. **execute方法不应该抛出异常**：
       - execute方法应该捕获所有内部异常
       - 失败时返回success=False的Operation对象，而不是抛出异常
       - 这确保了操作链的稳定执行
    
    2. **内部辅助方法可以抛出异常**：
       - execute方法内调用的私有方法可以抛出ValueError等异常
       - 这些异常应该在execute的try-except块中被捕获
       - 捕获后转换为失败的Operation对象
    
    3. **错误消息应该清晰**：
       - error_message应该包含足够的上下文信息
       - 使用logger.error记录详细的错误堆栈
       - 返回给用户的消息应该友好且可操作
    
    4. **Fallback机制（可选）**：
       - 某些策略可以实现fallback逻辑（如AI内容优化）
       - Fallback失败后仍应返回失败的Operation对象
       - 在details中记录fallback尝试的信息
    
    示例：
        ```python
        async def execute(self, step, memory) -> Operation:
            start_time = datetime.now()
            try:
                # 执行核心逻辑（可能抛出异常）
                result = await self._do_work(step, memory)
                return self._create_operation_result(...)
            except Exception as e:
                logger.error(f"操作失败: {str(e)}")
                # 返回失败结果，不抛出异常
                return self._create_operation_result(
                    ..., success=False, error_message=str(e)
                )
        ```
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
            Operation: 执行结果（成功或失败都返回Operation对象）
        
        Note:
            此方法不应该抛出异常。所有异常都应该被捕获并转换为
            success=False的Operation对象。参见类文档中的错误处理策略。
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

