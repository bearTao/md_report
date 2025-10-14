"""SQL variable executor - P0"""
from typing import Any
from app.executors.base import BaseVariableExecutor
from app.connectors.database import db_connector
from app.core.exceptions import SqlExecutionError


class SqlExecutor(BaseVariableExecutor):
    """Executes SQL type variables"""
    
    async def _execute_impl(self) -> Any:
        """
        Execute SQL query and return results
        """
        if not self.metadata.sql_config:
            raise SqlExecutionError(
                self.variable_name,
                "sql_config not provided"
            )
        
        config = self.metadata.sql_config
        
        # Interpolate dependencies into SQL query
        try:
            query = self.context.interpolate_string(config.query)
        except Exception as e:
            raise SqlExecutionError(
                self.variable_name,
                f"Failed to interpolate SQL query: {str(e)}",
                e
            )
        
        # Prepare parameters if needed
        parameters = {}
        if config.parameters:
            for param_name in config.parameters:
                if self.context.has_variable(param_name):
                    parameters[param_name] = self.context.get_variable(param_name)
        
        # Execute query
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
        
        # Return based on expected type
        if self.metadata.type == "object" and len(results) > 0:
            # Return first row as object
            return results[0]
        elif self.metadata.type == "array":
            # Return all rows
            return results
        elif len(results) > 0:
            # Single value: return first column of first row
            first_row = results[0]
            if first_row:
                return list(first_row.values())[0]
            return None
        
        return None

