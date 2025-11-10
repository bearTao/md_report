"""
SQL变量执行器模块

功能说明：
- 执行SQL查询并返回结果
- 支持多种结果模式（单行、多行、单值、单列）
- 支持变量插值和参数化查询
- 自动类型转换和结果格式化
"""
from typing import Any
from app.executors.base import BaseVariableExecutor
from app.connectors.database import db_connector
from app.core.exceptions import SqlExecutionError
from app.core.models import SqlResultMode


class SqlExecutor(BaseVariableExecutor):
    """
    SQL执行器
    
    功能：
    1. 执行SQL查询语句
    2. 支持混合查询模式：
       - {{variable}}: 用于SQL结构插值（表名、字段名等）
       - :param_name: 用于参数化查询（数据值，防SQL注入）
    3. 支持多种结果返回模式
    
    支持的结果模式：
    - first_row: 返回第一行作为对象 {col1: val1, col2: val2}
    - all_rows: 返回所有行作为数组 [{row1}, {row2}, ...]
    - first_value: 返回第一行第一列的值（标量）
    - first_column: 返回第一列的所有值 [val1, val2, ...]
    - auto: 根据type自动判断（默认）
    """
    
    async def _execute_impl(self) -> Any:
        """
        执行SQL查询并根据result_mode返回结果
        
        执行流程：
        1. 插值{{variable}}模式（用于SQL结构：表名、字段等）
        2. 准备:param_name参数（用于数据值，防SQL注入）
        3. 执行查询
        4. 根据result_mode格式化结果
        
        混合查询示例：
            SELECT {{columns}} FROM {{table_name}} WHERE id = :user_id
            - {{columns}}, {{table_name}}: 结构插值（不防注入，谨慎使用）
            - :user_id: 参数化查询（安全，防注入）
        
        Returns:
            Any: 根据result_mode返回不同格式的结果
        """
        if not self.metadata.sql_config:
            raise SqlExecutionError(
                self.variable_name,
                "sql_config not provided"
            )
        
        config = self.metadata.sql_config
        
        # 步骤1：插值 {{variable}} 模式，用于SQL结构部分
        # 允许动态表名、字段列表、JOIN子句等
        # 注意：:param_name占位符会被保留，用于后续参数化查询
        try:
            query = self.context.interpolate_string(config.query)
        except Exception as e:
            raise SqlExecutionError(
                self.variable_name,
                f"Failed to interpolate SQL query: {str(e)}",
                e
            )
        
        # 步骤2：准备 :param_name 参数
        # 这些参数会安全地传递给数据库驱动，防止SQL注入
        parameters = {}
        if config.parameters:
            for param_name in config.parameters:
                if self.context.has_variable(param_name):
                    parameters[param_name] = self.context.get_variable(param_name)
        
        # 步骤3：执行查询（同时使用插值后的SQL和参数）
        # 数据库驱动会处理适当的转义和类型转换
        try:
            results = await db_connector.execute_query(
                connection_name=config.connection,
                query=query,
                parameters=parameters if parameters else None,
                timeout=config.timeout or 10
            )
        except Exception as e:
            raise SqlExecutionError(
                self.variable_name,
                f"SQL execution failed: {str(e)}",
                e
            )
        
        # 处理空结果：返回默认值或None
        if not results:
            return self.metadata.default if self.metadata.default is not None else None
        
        # 获取结果模式（默认为AUTO）
        result_mode = config.result_mode if config.result_mode else SqlResultMode.AUTO
        
        # 步骤4：根据result_mode返回格式化的数据
        if result_mode == SqlResultMode.FIRST_ROW:
            # 模式1：返回第一行作为对象
            # 示例：{id: 1, name: "Alice", age: 25}
            return results[0]
        
        elif result_mode == SqlResultMode.ALL_ROWS:
            # 模式2：返回所有行作为数组
            # 示例：[{id: 1, name: "Alice"}, {id: 2, name: "Bob"}]
            return results
        
        elif result_mode == SqlResultMode.FIRST_VALUE:
            # 模式3：返回第一行第一列（单个标量值）
            # 示例：42 或 "Alice"
            first_row = results[0]
            if first_row:
                values = list(first_row.values())
                return values[0] if values else None
            return None
        
        elif result_mode == SqlResultMode.FIRST_COLUMN:
            # 模式4：返回第一列的所有值作为数组
            # 示例：[1, 2, 3, 4, 5]
            if results and results[0]:
                column_name = list(results[0].keys())[0]
                return [row[column_name] for row in results if column_name in row]
            return []
        
        else:  # SqlResultMode.AUTO or other
            # 模式5：自动模式 - 基于变量的type智能判断返回格式
            if self.metadata.type == "array":
                # 变量类型为array，返回所有行
                return results
            
            elif self.metadata.type == "object":
                # 变量类型为object
                # - 单行结果：返回对象
                # - 多行结果：返回数组（避免丢失数据）
                if len(results) == 1:
                    return results[0]
                else:
                    # 多行数据，返回数组而不是只返回第一行
                    return results
            
            elif self.metadata.type in ("string", "number", "boolean"):
                # 变量类型为标量（字符串、数字、布尔值）
                # 返回第一行第一列的值
                first_row = results[0]
                if first_row:
                    values = list(first_row.values())
                    return values[0] if values else None
                return None
            
            else:
                # 未指定类型，默认返回所有数据
                return results

