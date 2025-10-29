"""API variable executor - P0 - Enhanced with flexible response mapping"""
from typing import Any
from app.executors.base import BaseVariableExecutor
from app.connectors.api import api_connector
from app.core.exceptions import ApiExecutionError


class ApiExecutor(BaseVariableExecutor):
    """Executes API type variables"""
    
    async def _execute_impl(self) -> Any:
        """
        Call external API and return mapped response
        
        Supports three response_mapping modes:
        1. None or {}: Return full API response
        2. str: Extract single path using JMESPath (can return any type)
        3. Dict[str, str]: Map multiple fields to new object
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
        
        # Make API call with retry support
        try:
            response = await api_connector.request(
                method=config.method,
                url=url,
                headers=headers,
                params=params,
                json_data=body,
                timeout=config.timeout or 10,
                retry_count=config.retry_count or 0,
                retry_status_codes=config.retry_status_codes,
                retry_backoff=config.retry_backoff or 1.0
            )
        except Exception as e:
            raise ApiExecutionError(
                self.variable_name,
                f"API call failed: {str(e)}",
                e
            )
        
        # Process response based on response_mapping type
        mapping = config.response_mapping
        
        # Mode 1: No mapping or empty dict - return full response
        if mapping is None or (isinstance(mapping, dict) and not mapping):
            return response
        
        # Mode 2: String path - extract single path (returns any type)
        if isinstance(mapping, str):
            try:
                extracted = api_connector._extract_path(response, mapping)
                return extracted
            except Exception as e:
                raise ApiExecutionError(
                    self.variable_name,
                    f"Failed to extract path '{mapping}': {str(e)}",
                    e
                )
        
        # Mode 3: Dict mapping - map multiple fields to new object
        if isinstance(mapping, dict):
            try:
                mapped_data = api_connector.map_response(response, mapping)
                return mapped_data
            except Exception as e:
                raise ApiExecutionError(
                    self.variable_name,
                    f"Failed to map response: {str(e)}",
                    e
                )
        
        # Fallback: return raw response
        return response

