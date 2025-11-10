"""
用户输入变量执行器模块

功能说明：
- 从用户输入中提取变量值
- 自动类型转换和验证
- 支持必填项检查
- 支持默认值
"""
from typing import Any
from app.executors.base import BaseVariableExecutor
from app.core.exceptions import VariableExecutionError


class UserInputExecutor(BaseVariableExecutor):
    """
    用户输入执行器
    
    功能：
    1. 从用户输入中提取变量值
    2. 根据元数据进行类型转换
    3. 验证必填字段
    4. 处理默认值
    
    使用场景：
    - 报告生成时用户输入的参数（日期、名称、ID等）
    - 表单提交的数据
    - API请求中的用户参数
    """
    
    async def _execute_impl(self) -> Any:
        """
        从用户输入中提取值并转换类型
        
        执行流程：
        1. 检查用户是否提供了该变量
        2. 如果未提供且为必填项，抛出错误
        3. 如果未提供且非必填，返回默认值
        4. 进行类型转换
        
        Returns:
            Any: 转换后的变量值
            
        Raises:
            VariableExecutionError: 必填字段缺失或类型转换失败
        """
        # 步骤1：检查用户输入中是否包含该变量
        if self.variable_name not in self.context.user_inputs:
            if self.metadata.required:
                # 必填项缺失，抛出错误
                raise VariableExecutionError(
                    self.variable_name,
                    f"Required user input '{self.variable_name}' not provided"
                )
            # 非必填项，返回默认值
            return self.metadata.default
        
        value = self.context.user_inputs[self.variable_name]
        
        # 步骤2：根据元数据定义的类型进行转换
        value = self._convert_type(value)
        
        return value
    
    def _convert_type(self, value: Any) -> Any:
        """
        将值转换为期望的类型
        
        支持的类型转换：
        - string: 转换为字符串
        - number: 转换为整数或浮点数（自动判断）
        - boolean: 转换为布尔值（支持'true'、'1'、'yes'等）
        - array/object: 保持原样（已由JSON解析器处理）
        
        Args:
            value: 原始值
        
        Returns:
            Any: 转换后的值
            
        Raises:
            VariableExecutionError: 类型转换失败
        """
        target_type = self.metadata.type
        
        if value is None:
            return value
            
        if target_type == "string":
            return str(value)
        elif target_type == "number":
            try:
                # 自动判断整数还是浮点数
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
                # 支持多种布尔值表示
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        elif target_type in ("array", "object"):
            # 数组和对象类型已由JSON加载器解析，无需转换
            return value
        
        # 其他类型保持不变
        return value

