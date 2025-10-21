"""SQL variable executor - P0"""
from typing import Any
from app.executors.base import BaseVariableExecutor
from app.connectors.database import db_connector
from app.core.exceptions import SqlExecutionError
from app.core.models import SqlResultMode


class SqlExecutor(BaseVariableExecutor):
    """
    Executes SQL type variables
    
    Supports multiple result modes:
    - first_row: 返回第一行作为对象 {col1: val1, col2: val2}
    - all_rows: 返回所有行作为数组 [{row1}, {row2}, ...]
    - first_value: 返回第一行第一列的值（标量）
    - first_column: 返回第一列的所有值 [val1, val2, ...]
    - auto: 根据type自动判断（默认）
    """
    
    async def _execute_impl(self) -> Any:
        """
        Execute SQL query and return results based on result_mode
        
        Supports hybrid scenarios:
        - {{variable}}: String interpolation for SQL structure (table names, columns, etc.)
        - :param_name: Parameterized queries for data values (safe, prevents SQL injection)
        """
        if not self.metadata.sql_config:
            raise SqlExecutionError(
                self.variable_name,
                "sql_config not provided"
            )
        
        config = self.metadata.sql_config
        
        # Step 1: Interpolate {{variable}} patterns for SQL structure
        # This allows dynamic table names, column lists, JOIN clauses, etc.
        # Note: :param_name placeholders will be preserved for parameterized queries
        try:
            query = self.context.interpolate_string(config.query)
        except Exception as e:
            raise SqlExecutionError(
                self.variable_name,
                f"Failed to interpolate SQL query: {str(e)}",
                e
            )
        
        # Step 2: Prepare parameters for :param_name placeholders
        # These will be safely passed to the database driver
        parameters = {}
        if config.parameters:
            for param_name in config.parameters:
                if self.context.has_variable(param_name):
                    parameters[param_name] = self.context.get_variable(param_name)
        
        # Step 3: Execute query with both interpolated SQL and parameters
        # The database driver will handle proper escaping and type conversion
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
        
        # Handle empty results
        if not results:
            return self.metadata.default if self.metadata.default is not None else None
        
        # Get result_mode (default to AUTO if not specified)
        result_mode = config.result_mode if config.result_mode else SqlResultMode.AUTO
        
        # Return data based on result_mode
        if result_mode == SqlResultMode.FIRST_ROW:
            # 返回第一行
            return results[0]
        
        elif result_mode == SqlResultMode.ALL_ROWS:
            # 返回所有行
            return results
        
        elif result_mode == SqlResultMode.FIRST_VALUE:
            # 返回第一行第一列
            first_row = results[0]
            if first_row:
                values = list(first_row.values())
                return values[0] if values else None
            return None
        
        elif result_mode == SqlResultMode.FIRST_COLUMN:
            # 返回第一列的所有值
            if results and results[0]:
                column_name = list(results[0].keys())[0]
                return [row[column_name] for row in results if column_name in row]
            return []
        
        else:  # SqlResultMode.AUTO or other
            # 自动模式：基于type和实际数据智能判断
            if self.metadata.type == "array":
                # 明确要求array，返回所有行
                return results
            
            elif self.metadata.type == "object":
                # object类型：
                # - 单行：返回对象
                # - 多行：返回数组（避免丢数据）
                if len(results) == 1:
                    return results[0]
                else:
                    # 多行数据，返回数组而不是只返回第一行
                    return results
            
            elif self.metadata.type in ("string", "number", "boolean"):
                # 标量类型：返回第一行第一列
                first_row = results[0]
                if first_row:
                    values = list(first_row.values())
                    return values[0] if values else None
                return None
            
            else:
                # 默认返回所有数据
                return results

