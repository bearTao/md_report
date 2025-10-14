"""User input variable executor - P0"""
from typing import Any
from app.executors.base import BaseVariableExecutor
from app.core.exceptions import VariableExecutionError


class UserInputExecutor(BaseVariableExecutor):
    """Executes user_input type variables"""
    
    async def _execute_impl(self) -> Any:
        """
        Extract value from user inputs
        Apply type conversion and validation
        """
        # Get value from user inputs
        if self.variable_name not in self.context.user_inputs:
            if self.metadata.required:
                raise VariableExecutionError(
                    self.variable_name,
                    f"Required user input '{self.variable_name}' not provided"
                )
            # Return default if not required
            return self.metadata.default
        
        value = self.context.user_inputs[self.variable_name]
        
        # Basic type conversion based on metadata.type
        value = self._convert_type(value)
        
        return value
    
    def _convert_type(self, value: Any) -> Any:
        """Convert value to expected type"""
        target_type = self.metadata.type
        
        if value is None:
            return value
            
        if target_type == "string":
            return str(value)
        elif target_type == "number":
            try:
                return float(value) if '.' in str(value) else int(value)
            except (ValueError, TypeError):
                raise VariableExecutionError(
                    self.variable_name,
                    f"Cannot convert '{value}' to number"
                )
        elif target_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        elif target_type in ("array", "object"):
            # Already parsed by JSON loader
            return value
        
        return value

