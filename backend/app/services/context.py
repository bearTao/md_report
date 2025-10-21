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
            var_expr = match.group(1).strip()
            
            # Check if expression contains Jinja2 filters (e.g., "variable | length")
            if '|' in var_expr:
                parts = var_expr.split('|')
                var_name = parts[0].strip()
                filters = [f.strip() for f in parts[1:]]
                
                # Get the variable value
                value = _get_variable_value(var_name)
                
                # Apply filters
                for filter_name in filters:
                    value = _apply_filter(filter_name, value, var_name)
                
                return str(value) if value is not None else ''
            else:
                # No filters, just get the variable
                value = _get_variable_value(var_expr)
                
                # Convert to string representation
                if isinstance(value, (dict, list)):
                    return json.dumps(value, ensure_ascii=False)
                elif value is None:
                    return ''  # Return empty string for None values
                return str(value)
        
        def _get_variable_value(var_name):
            """Helper to get variable value, supporting nested attributes"""
            # Support nested attribute access (e.g., overview.micro_grid_name)
            if '.' in var_name:
                parts = var_name.split('.')
                base_var = parts[0]
                
                if base_var not in self.variables:
                    raise DependencyError(f"Variable '{base_var}' not found for interpolation")
                
                value = self.variables[base_var]
                
                # Navigate through nested attributes
                for attr in parts[1:]:
                    if isinstance(value, dict):
                        if attr not in value:
                            raise DependencyError(f"Variable '{var_name}' not found ('{attr}' not in {base_var})")
                        value = value[attr]
                    elif hasattr(value, attr):
                        value = getattr(value, attr)
                    else:
                        raise DependencyError(f"Variable '{var_name}' not found ('{attr}' not accessible)")
                return value
            else:
                # Simple variable access
                if var_name not in self.variables:
                    raise DependencyError(f"Variable '{var_name}' not found for interpolation")
                return self.variables[var_name]
        
        def _apply_filter(filter_name, value, var_name):
            """Apply Jinja2-style filter to value"""
            if filter_name == 'length':
                if value is None:
                    return 0
                if isinstance(value, (list, dict, str)):
                    return len(value)
                else:
                    raise DependencyError(f"Cannot apply 'length' filter to {var_name} (type: {type(value).__name__})")
            elif filter_name == 'default':
                # Simple default filter (no parameters supported yet)
                return value if value is not None else ''
            elif filter_name == 'upper':
                return str(value).upper() if value is not None else ''
            elif filter_name == 'lower':
                return str(value).lower() if value is not None else ''
            elif filter_name == 'trim':
                return str(value).strip() if value is not None else ''
            elif filter_name == 'first':
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    return value[0]
                return value
            elif filter_name == 'last':
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    return value[-1]
                return value
            else:
                # Unknown filter - just return the value
                import logging
                logging.warning(f"Unknown filter '{filter_name}' applied to {var_name}, ignoring")
                return value
        
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

