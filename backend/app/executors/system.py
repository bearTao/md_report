"""
系统变量执行器模块

功能说明：
- 生成系统级变量（时间戳、UUID等）
- 支持常量值
- 支持模板插值
- 自动格式化输出
"""
from typing import Any
import uuid
from datetime import datetime
from app.executors.base import BaseVariableExecutor
from app.core.exceptions import VariableExecutionError


class SystemExecutor(BaseVariableExecutor):
    """
    系统执行器
    
    功能：
    1. 生成时间戳（自定义格式）
    2. 生成唯一标识符（UUID）
    3. 定义常量值
    4. 支持变量插值的模板值
    
    使用场景：
    - 报告生成时间
    - 任务唯一ID
    - 系统常量（如公司名称、版本号）
    - 动态计算的系统值
    """
    
    async def _execute_impl(self) -> Any:
        """
        根据配置生成系统值
        
        支持的生成器类型：
        - datetime: 当前时间（可自定义格式）
        - uuid: UUID v4唯一标识符
        - value: 常量或模板值（支持变量插值）
        
        返回规则：
        - 单字段：直接返回值（不包装为对象）
        - 多字段：返回字典对象
        
        Returns:
            Any: 生成的值（字符串、对象等）
            
        Raises:
            VariableExecutionError: 配置错误或生成失败
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
                # 生成器类型1：当前时间
                # 默认格式：2024-01-01 12:00:00
                # 可自定义格式：%Y年%m月%d日
                format_str = field_config.get("format", "%Y-%m-%d %H:%M:%S")
                result[field_name] = datetime.now().strftime(format_str)
                
            elif generator_type == "uuid":
                # 生成器类型2：UUID v4（全局唯一标识符）
                # 格式：550e8400-e29b-41d4-a716-446655440000
                result[field_name] = str(uuid.uuid4())
                
            elif "value" in field_config:
                # 生成器类型3：常量或模板值
                value = field_config["value"]
                # 如果值是字符串，支持变量插值
                # 例如："Report for {{company_name}}"
                if isinstance(value, str):
                    result[field_name] = self.context.interpolate_string(value)
                else:
                    result[field_name] = value
                
            else:
                raise VariableExecutionError(
                    self.variable_name,
                    f"Unknown generator type or missing value for field '{field_name}'"
                )
        
        # 优化返回格式：单字段直接返回值，不包装为对象
        if len(result) == 1:
            return list(result.values())[0]
        
        return result

