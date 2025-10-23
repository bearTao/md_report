"""Base variable executor - P0"""
from abc import ABC, abstractmethod
from typing import Any
import time
from app.core.models import VariableMetadata, VariableExecutionResult, VariableStatus
from app.services.context import ExecutionContext
from app.core.exceptions import TaskCancelledException
from app.services.execution_logger import execution_logger


class BaseVariableExecutor(ABC):
    """Base class for all variable executors"""
    
    def __init__(self, variable_name: str, metadata: VariableMetadata, context: ExecutionContext):
        self.variable_name = variable_name
        self.metadata = metadata
        self.context = context
        
    async def execute(self) -> VariableExecutionResult:
        """
        Execute variable with timing and error handling
        Returns execution result
        """
        start_time = time.time()
        
        # Log start of execution
        execution_logger.info(
            self.context.task_id,
            f"Starting execution of variable '{self.variable_name}'",
            variable_name=self.variable_name,
            context={"source": self.metadata.source.value}
        )
        
        try:
            # Check if task is cancelled before starting
            if self.context.is_task_cancelled():
                execution_logger.warning(
                    self.context.task_id,
                    f"Task cancelled before executing variable '{self.variable_name}'",
                    variable_name=self.variable_name
                )
                raise TaskCancelledException(self.context.task_id, f"Task cancelled before executing variable '{self.variable_name}'")
            
            # Check dependencies
            ready, missing = self.context.check_dependencies_ready(self.variable_name)
            if not ready:
                execution_logger.warning(
                    self.context.task_id,
                    f"Variable '{self.variable_name}' missing dependencies: {', '.join(missing)}",
                    variable_name=self.variable_name,
                    context={"missing_dependencies": missing}
                )
                return VariableExecutionResult(
                    variable_name=self.variable_name,
                    status=VariableStatus.FAILED,
                    error=f"Missing dependencies: {', '.join(missing)}"
                )
            
            # Execute the variable
            value = await self._execute_impl()
            
            # Check if task was cancelled during execution
            if self.context.is_task_cancelled():
                execution_logger.warning(
                    self.context.task_id,
                    f"Task cancelled while executing variable '{self.variable_name}'",
                    variable_name=self.variable_name
                )
                raise TaskCancelledException(self.context.task_id, f"Task cancelled while executing variable '{self.variable_name}'")
            
            # Store in context
            self.context.set_variable(self.variable_name, value)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log successful execution
            execution_logger.info(
                self.context.task_id,
                f"Successfully executed variable '{self.variable_name}' in {duration_ms}ms",
                variable_name=self.variable_name,
                context={
                    "duration_ms": duration_ms,
                    "result_type": type(value).__name__
                }
            )
            
            return VariableExecutionResult(
                variable_name=self.variable_name,
                status=VariableStatus.SUCCESS,
                value=value,
                duration_ms=duration_ms
            )
        
        except TaskCancelledException:
            # Task was cancelled - propagate the exception
            duration_ms = int((time.time() - start_time) * 1000)
            execution_logger.warning(
                self.context.task_id,
                f"Variable '{self.variable_name}' execution cancelled",
                variable_name=self.variable_name,
                context={"duration_ms": duration_ms}
            )
            return VariableExecutionResult(
                variable_name=self.variable_name,
                status=VariableStatus.FAILED,
                error="Task was cancelled",
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            execution_logger.error(
                self.context.task_id,
                f"Variable '{self.variable_name}' execution failed: {str(e)}",
                variable_name=self.variable_name,
                context={
                    "duration_ms": duration_ms,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            # Use default value if available
            if self.metadata.default is not None:
                execution_logger.info(
                    self.context.task_id,
                    f"Using default value for variable '{self.variable_name}' after error",
                    variable_name=self.variable_name,
                    context={"default_value": str(self.metadata.default)}
                )
                self.context.set_variable(self.variable_name, self.metadata.default)
                return VariableExecutionResult(
                    variable_name=self.variable_name,
                    status=VariableStatus.SUCCESS,
                    value=self.metadata.default,
                    duration_ms=duration_ms,
                    metadata={"used_default": True, "error": str(e)}
                )
            
            return VariableExecutionResult(
                variable_name=self.variable_name,
                status=VariableStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms
            )
    
    @abstractmethod
    async def _execute_impl(self) -> Any:
        """
        Implement actual execution logic in subclasses
        Should raise exceptions on failure
        """
        pass

