"""
执行上下文管理器模块

功能说明：
- 管理变量执行过程中的所有状态
- 存储已执行变量的值
- 提供变量插值和依赖解析功能
- 管理任务取消标志
- 支持嵌套属性访问和类型保持
"""
from typing import Any, Dict, Optional
import json
import re
from app.core.models import TaskContext, VariableMetadata
from app.core.exceptions import DependencyError


class ExecutionContext:
    """
    执行上下文管理器
    
    核心职责：
    1. 存储执行过程中的所有变量值
    2. 提供变量插值功能（{{variable}}格式）
    3. 检查变量依赖关系
    4. 管理任务取消状态
    5. 支持智能类型转换
    
    使用场景：
    - SQL查询：插值表名、字段名、WHERE条件
    - AI提示词：插值已有变量到提示词模板
    - API请求：插值URL参数、请求体
    - 模板渲染：提供所有变量用于Jinja2渲染
    """
    
    # 类级别的取消标志存储（所有实例共享）
    _cancellation_flags: Dict[str, bool] = {}
    
    def __init__(self, task_id: str, template_id: str, 
                 user_inputs: Dict[str, Any], 
                 metadata: Dict[str, VariableMetadata]):
        """
        初始化执行上下文
        
        Args:
            task_id: 任务ID
            template_id: 模板ID
            user_inputs: 用户输入的变量值
            metadata: 所有变量的元数据定义
        """
        self.task_id = task_id
        self.template_id = template_id
        self.user_inputs = user_inputs
        self.metadata = metadata
        self.variables: Dict[str, Any] = {}  # 存储已执行的变量值
        
    def set_variable(self, name: str, value: Any):
        """
        设置变量值到上下文
        
        Args:
            name: 变量名
            value: 变量值（任意类型）
        """
        self.variables[name] = value
        
    def get_variable(self, name: str) -> Any:
        """
        从上下文获取变量值
        
        Args:
            name: 变量名
        
        Returns:
            Any: 变量值
            
        Raises:
            KeyError: 变量不存在
        """
        if name in self.variables:
            return self.variables[name]
        raise KeyError(f"Variable '{name}' not found in context")
        
    def has_variable(self, name: str) -> bool:
        """
        检查变量是否存在
        
        Args:
            name: 变量名
        
        Returns:
            bool: 是否存在
        """
        return name in self.variables
        
    def get_dependencies(self, variable_name: str) -> list[str]:
        """
        获取变量的依赖列表
        
        Args:
            variable_name: 变量名
        
        Returns:
            list[str]: 依赖的变量名列表
        """
        if variable_name not in self.metadata:
            return []
        var_meta = self.metadata[variable_name]
        return var_meta.dependencies or []
        
    def check_dependencies_ready(self, variable_name: str) -> tuple[bool, list[str]]:
        """
        检查变量的所有依赖是否已就绪
        
        用于在执行变量前验证依赖条件
        
        Args:
            variable_name: 变量名
        
        Returns:
            tuple[bool, list[str]]: (是否全部就绪, 缺失的依赖列表)
        """
        deps = self.get_dependencies(variable_name)
        missing = [dep for dep in deps if not self.has_variable(dep)]
        return len(missing) == 0, missing
        
    def interpolate_string(self, template_str: str) -> str:
        """
        字符串模板插值（变量替换）
        
        功能说明：
        - 支持{{variable}}格式（Jinja2风格）
        - 支持{variable}格式（Python格式化风格）
        - 支持嵌套属性访问：{{user.name}}
        - 支持过滤器：{{count | length}}
        - 智能类型转换（dict/list转JSON，None转空串）
        
        使用场景：
        - SQL查询：SELECT * FROM {{table_name}} WHERE id = {{user_id}}
        - API URL：https://api.com/users/{{user_id}}
        - AI提示词：分析以下数据：{{data}}
        
        支持的过滤器：
        - length: 获取长度
        - default: 默认值
        - upper/lower: 大小写转换
        - trim: 去除首尾空白
        - first/last: 获取首尾元素
        
        Args:
            template_str: 包含变量占位符的字符串
        
        Returns:
            str: 插值后的字符串
            
        Raises:
            DependencyError: 引用的变量不存在
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
        """Recursively interpolate variables in dictionary with type preservation"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._interpolate_with_type_preservation(value)
            elif isinstance(value, dict):
                result[key] = self.interpolate_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._interpolate_with_type_preservation(v) if isinstance(v, str) 
                    else self.interpolate_dict(v) if isinstance(v, dict)
                    else v
                    for v in value
                ]
            else:
                result[key] = value
        return result
    
    def _interpolate_with_type_preservation(self, value: str) -> Any:
        """
        Interpolate string with smart type preservation
        
        Rules:
        - Pure variable reference: "{{var}}" → preserve original type
        - Template string: "prefix {{var}} suffix" → return string
        - Multiple variables: "{{var1}} {{var2}}" → return string
        
        Examples:
            "{{count}}" where count=15 → 15 (int)
            "Total: {{count}}" where count=15 → "Total: 15" (str)
            "{{name}}" where name="Alice" → "Alice" (str)
            "{{active}}" where active=True → True (bool)
        """
        # Pattern to match pure variable reference (no surrounding text)
        pure_var_pattern = r'^\s*\{\{([^}]+)\}\}\s*$'
        match = re.match(pure_var_pattern, value)
        
        if match:
            # Pure variable reference - preserve type
            var_expr = match.group(1).strip()
            
            # If has filters, must return string
            if '|' in var_expr:
                return self.interpolate_string(value)
            
            # Get the actual value with type preservation
            try:
                if '.' in var_expr:
                    # Nested attribute access
                    parts = var_expr.split('.')
                    base_var = parts[0]
                    
                    if base_var not in self.variables:
                        raise DependencyError(f"Variable '{base_var}' not found")
                    
                    result = self.variables[base_var]
                    for attr in parts[1:]:
                        if isinstance(result, dict):
                            if attr not in result:
                                raise DependencyError(f"Attribute '{attr}' not found in {base_var}")
                            result = result[attr]
                        elif hasattr(result, attr):
                            result = getattr(result, attr)
                        else:
                            raise DependencyError(f"Attribute '{attr}' not accessible in {base_var}")
                    
                    return result  # Preserve original type
                else:
                    # Simple variable
                    if var_expr not in self.variables:
                        raise DependencyError(f"Variable '{var_expr}' not found")
                    
                    return self.variables[var_expr]  # Preserve original type
            except Exception as e:
                # If any error, fall back to string interpolation
                import logging
                logging.warning(f"Type preservation failed for '{value}': {e}. Using string interpolation.")
                return self.interpolate_string(value)
        else:
            # Not a pure variable - it's a template string
            return self.interpolate_string(value)
        
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
    
    # Task cancellation management methods
    @classmethod
    def set_cancellation_flag(cls, task_id: str):
        """Set cancellation flag for a task"""
        cls._cancellation_flags[task_id] = True
    
    @classmethod
    def is_cancelled(cls, task_id: str) -> bool:
        """Check if task is cancelled"""
        return cls._cancellation_flags.get(task_id, False)
    
    @classmethod
    def clear_cancellation_flag(cls, task_id: str):
        """Clear cancellation flag for a task"""
        if task_id in cls._cancellation_flags:
            del cls._cancellation_flags[task_id]
    
    def is_task_cancelled(self) -> bool:
        """Check if current task is cancelled"""
        return self.is_cancelled(self.task_id)

