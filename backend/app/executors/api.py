"""API variable executor - P0"""
from typing import Any
from app.executors.base import BaseVariableExecutor
from app.connectors.api import api_connector
from app.core.exceptions import ApiExecutionError


class ApiExecutor(BaseVariableExecutor):
    """Executes API type variables"""
    
    async def _execute_impl(self) -> Any:
        """
        Call external API and return mapped response
        """
        if not self.metadata.api_config:
            raise ApiExecutionError(
                self.variable_name,
                "api_config not provided"
            )
        
        config = self.metadata.api_config
        
        # Interpolate endpoint URL
        try:
            url = self.context.interpolate_string(config.endpoint)
        except Exception as e:
            raise ApiExecutionError(
                self.variable_name,
                f"Failed to interpolate API endpoint: {str(e)}",
                e
            )
        
        # Interpolate headers, parameters, and body
        try:
            headers = self.context.interpolate_dict(config.headers or {})
            params = self.context.interpolate_dict(config.parameters or {})
            body = self.context.interpolate_dict(config.body or {}) if config.body else None
        except Exception as e:
            raise ApiExecutionError(
                self.variable_name,
                f"Failed to interpolate API config: {str(e)}",
                e
            )
        
        # Make API call
        try:
            response = await api_connector.request(
                method=config.method,
                url=url,
                headers=headers,
                params=params,
                json_data=body,
                timeout=config.timeout or 10
            )
        except Exception as e:
            raise ApiExecutionError(
                self.variable_name,
                f"API call failed: {str(e)}",
                e
            )
        
        # Map response data
        if config.response_mapping:
            try:
                mapped_data = api_connector.map_response(response, config.response_mapping)
                return mapped_data
            except Exception as e:
                raise ApiExecutionError(
                    self.variable_name,
                    f"Failed to map response: {str(e)}",
                    e
                )
        
        # Return raw response if no mapping
        return response

