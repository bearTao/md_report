"""System variable executor - P0"""
from typing import Any
import uuid
from datetime import datetime
from app.executors.base import BaseVariableExecutor
from app.core.exceptions import VariableExecutionError


class SystemExecutor(BaseVariableExecutor):
    """Executes system type variables (timestamp, uuid, constants)"""
    
    async def _execute_impl(self) -> Any:
        """
        Generate system values based on configuration
        """
        if not self.metadata.system_config:
            raise VariableExecutionError(
                self.variable_name,
                "system_config not provided"
            )
        
        fields = self.metadata.system_config.fields
        result = {}
        
        for field_name, field_config in fields.items():
            generator_type = field_config.get("generator")
            
            if generator_type == "datetime":
                format_str = field_config.get("format", "%Y-%m-%d %H:%M:%S")
                result[field_name] = datetime.now().strftime(format_str)
                
            elif generator_type == "uuid":
                result[field_name] = str(uuid.uuid4())
                
            elif "value" in field_config:
                # Constant or templated value
                value = field_config["value"]
                # If value is a string, interpolate variables from context
                if isinstance(value, str):
                    result[field_name] = self.context.interpolate_string(value)
                else:
                    result[field_name] = value
                
            else:
                raise VariableExecutionError(
                    self.variable_name,
                    f"Unknown generator type or missing value for field '{field_name}'"
                )
        
        # If only one field, return its value directly (not wrapped in object)
        if len(result) == 1:
            return list(result.values())[0]
        
        return result

