"""Base variable executor - P0"""
from abc import ABC, abstractmethod
from typing import Any
import time
from app.core.models import VariableMetadata, VariableExecutionResult, VariableStatus
from app.services.context import ExecutionContext


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
        
        try:
            # Check dependencies
            ready, missing = self.context.check_dependencies_ready(self.variable_name)
            if not ready:
                return VariableExecutionResult(
                    variable_name=self.variable_name,
                    status=VariableStatus.FAILED,
                    error=f"Missing dependencies: {', '.join(missing)}"
                )
            
            # Execute the variable
            value = await self._execute_impl()
            
            # Store in context
            self.context.set_variable(self.variable_name, value)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return VariableExecutionResult(
                variable_name=self.variable_name,
                status=VariableStatus.SUCCESS,
                value=value,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Use default value if available
            if self.metadata.default is not None:
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

