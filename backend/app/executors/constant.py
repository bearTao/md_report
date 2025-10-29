"""Constant variable executor"""
from typing import Any
from app.executors.base import BaseVariableExecutor


class ConstantExecutor(BaseVariableExecutor):
    """
    Executes constant type variables
    
    Constant variables have fixed values defined in metadata.
    They are useful for:
    - Business constants (e.g., tax rates, salary standards)
    - Configuration values (e.g., API endpoints, company info)
    - Fixed parameters used across multiple variables
    """
    
    async def _execute_impl(self) -> Any:
        """
        Return the constant value from metadata
        
        Returns:
            The value field from metadata
            
        Raises:
            ValueError: If value field is not provided
        """
        if self.metadata.value is None:
            raise ValueError(
                f"Constant variable '{self.variable_name}' must have a 'value' field defined in metadata"
            )
        
        return self.metadata.value

