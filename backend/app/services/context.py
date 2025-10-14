"""Execution context manager - P0"""
from typing import Any, Dict, Optional
import json
import re
from app.core.models import TaskContext, VariableMetadata
from app.core.exceptions import DependencyError


class ExecutionContext:
    """
    Manages variable execution context (in-memory for P0)
    Stores variable values and provides dependency resolution
    """
    
    def __init__(self, task_id: str, template_id: str, 
                 user_inputs: Dict[str, Any], 
                 metadata: Dict[str, VariableMetadata]):
        self.task_id = task_id
        self.template_id = template_id
        self.user_inputs = user_inputs
        self.metadata = metadata
        self.variables: Dict[str, Any] = {}
        
    def set_variable(self, name: str, value: Any):
        """Set variable value in context"""
        self.variables[name] = value
        
    def get_variable(self, name: str) -> Any:
        """Get variable value from context"""
        if name in self.variables:
            return self.variables[name]
        raise KeyError(f"Variable '{name}' not found in context")
        
    def has_variable(self, name: str) -> bool:
        """Check if variable exists in context"""
        return name in self.variables
        
    def get_dependencies(self, variable_name: str) -> list[str]:
        """Get dependencies for a variable"""
        if variable_name not in self.metadata:
            return []
        var_meta = self.metadata[variable_name]
        return var_meta.dependencies or []
        
    def check_dependencies_ready(self, variable_name: str) -> tuple[bool, list[str]]:
        """
        Check if all dependencies for a variable are ready
        Returns (all_ready, missing_deps)
        """
        deps = self.get_dependencies(variable_name)
        missing = [dep for dep in deps if not self.has_variable(dep)]
        return len(missing) == 0, missing
        
    def interpolate_string(self, template_str: str) -> str:
        """
        Interpolate variables in string templates
        Supports both {{variable_name}} (Jinja2 style) and {variable_name} (Python format style)
        Used for SQL queries, API URLs, AI prompts, system values
        """
        def replace_var(match):
            var_name = match.group(1).strip()
            if not self.has_variable(var_name):
                raise DependencyError(f"Variable '{var_name}' not found for interpolation")
            value = self.get_variable(var_name)
            # Convert to string representation
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
        
        # First, replace {{variable}} pattern (Jinja2 style)
        template_str = re.sub(r'\{\{([^}]+)\}\}', replace_var, template_str)
        
        # Then, replace {variable} pattern (Python format style)
        template_str = re.sub(r'\{([^{}]+)\}', replace_var, template_str)
        
        return template_str
        
    def interpolate_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively interpolate variables in dictionary"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.interpolate_string(value)
            elif isinstance(value, dict):
                result[key] = self.interpolate_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.interpolate_string(v) if isinstance(v, str) 
                    else self.interpolate_dict(v) if isinstance(v, dict)
                    else v
                    for v in value
                ]
            else:
                result[key] = value
        return result
        
    def get_all_variables(self) -> Dict[str, Any]:
        """Get all variables for template rendering"""
        return self.variables.copy()
        
    def snapshot(self) -> Dict[str, Any]:
        """Create a JSON-serializable snapshot of context"""
        return {
            "task_id": self.task_id,
            "template_id": self.template_id,
            "user_inputs": self.user_inputs,
            "variables": self.variables
        }

