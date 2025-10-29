"""API connector - P0 - Enhanced with JMESPath and retry support"""
from typing import Any, Dict, Optional
import httpx
import json
import asyncio
import jmespath
import logging

logger = logging.getLogger(__name__)


class ApiConnector:
    """
    HTTP API client
    Supports GET, POST, PUT, DELETE with timeout and basic retry
    """
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
        
    async def request(self, 
                     method: str,
                     url: str,
                     headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, Any]] = None,
                     json_data: Optional[Dict[str, Any]] = None,
                     timeout: Optional[int] = None,
                     retry_count: int = 0,
                     retry_status_codes: Optional[list] = None,
                     retry_backoff: float = 1.0) -> Dict[str, Any]:
        """
        Make HTTP request with retry support
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL
            headers: Request headers
            params: URL parameters
            json_data: JSON body (for POST/PUT)
            timeout: Request timeout (overrides default)
            retry_count: Number of retries (0 means no retry)
            retry_status_codes: HTTP status codes to retry on
            retry_backoff: Backoff factor in seconds
            
        Returns:
            Response as dictionary
        """
        client = await self._get_client()
        request_timeout = timeout or self.timeout
        max_attempts = 1 + retry_count
        retry_codes = retry_status_codes or [429, 500, 502, 503, 504]
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    timeout=request_timeout
                )
                
                # Raise for HTTP errors (4xx, 5xx)
                response.raise_for_status()
                
                # Try to parse JSON response
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # Return text if not JSON
                    return {"_text": response.text, "_status": response.status_code}
                    
            except httpx.HTTPStatusError as e:
                last_exception = e
                # Check if we should retry
                if attempt < max_attempts - 1 and e.response.status_code in retry_codes:
                    wait_time = retry_backoff * (attempt + 1)
                    logger.warning(
                        f"HTTP {e.response.status_code} error on attempt {attempt + 1}/{max_attempts}. "
                        f"Retrying in {wait_time}s... URL: {url}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                # No more retries or status code not in retry list
                raise Exception(f"HTTP {e.response.status_code}: {e.response.text}") from e
                
            except httpx.TimeoutException as e:
                last_exception = e
                # Retry on timeout
                if attempt < max_attempts - 1:
                    wait_time = retry_backoff * (attempt + 1)
                    logger.warning(
                        f"Timeout on attempt {attempt + 1}/{max_attempts}. "
                        f"Retrying in {wait_time}s... URL: {url}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise Exception(f"Request timeout after {request_timeout}s") from e
                
            except httpx.RequestError as e:
                last_exception = e
                raise Exception(f"Request error: {str(e)}") from e
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise Exception("Unexpected error in request retry logic")
            
    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """GET request"""
        return await self.request("GET", url, **kwargs)
        
    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """POST request"""
        return await self.request("POST", url, **kwargs)
        
    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """PUT request"""
        return await self.request("PUT", url, **kwargs)
        
    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """DELETE request"""
        return await self.request("DELETE", url, **kwargs)
        
    def map_response(self, response_data: Dict[str, Any], 
                    mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Map response data using JMESPath-like simple path extraction
        
        Args:
            response_data: Response JSON
            mapping: Dict of {target_field: source_path}
            
        Returns:
            Mapped data
        """
        result = {}
        for target_field, source_path in mapping.items():
            # Simple dot notation path extraction
            value = self._extract_path(response_data, source_path)
            result[target_field] = value
        return result
        
    def _extract_path(self, data: Any, path: str) -> Any:
        """
        Extract value from nested data using JMESPath (with fallback to simple dot notation)
        
        Supports JMESPath syntax:
        - Simple paths: "data.items"
        - Array indexing: "items[0]", "data.products[0].name"
        - Array slicing: "items[:3]", "items[1:5]"
        - Projections: "items[*].name" (extract all names)
        - Filters: "items[?price > `100`]" (filter by condition)
        - Functions: "length(items)", "sum(items[*].price)"
        
        Args:
            data: Source data (dict, list, or primitive)
            path: JMESPath expression or simple dot notation
            
        Returns:
            Extracted value (can be any type: dict, list, str, number, bool, None)
        """
        if not path:
            return data
        
        # Try JMESPath first for powerful path extraction
        try:
            result = jmespath.search(path, data)
            return result
        except (jmespath.exceptions.JMESPathError, Exception) as e:
            # Fallback to simple dot notation for backward compatibility
            logger.debug(f"JMESPath failed for path '{path}': {e}. Falling back to simple dot notation.")
            return self._simple_dot_extract(data, path)
    
    def _simple_dot_extract(self, data: Any, path: str) -> Any:
        """
        Simple dot notation extraction (fallback method)
        Supports: "key1.key2.key3" and "items.0.name"
        """
        if not path:
            return data
            
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if 0 <= index < len(current) else None
            else:
                return None
                
        return current
        
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instance
api_connector = ApiConnector()

