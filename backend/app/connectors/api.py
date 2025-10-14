"""API connector - P0"""
from typing import Any, Dict, Optional
import httpx
import json


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
                     timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Make HTTP request
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL
            headers: Request headers
            params: URL parameters
            json_data: JSON body (for POST/PUT)
            timeout: Request timeout (overrides default)
            
        Returns:
            Response as dictionary
        """
        client = await self._get_client()
        request_timeout = timeout or self.timeout
        
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
            raise Exception(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except httpx.TimeoutException:
            raise Exception(f"Request timeout after {request_timeout}s")
        except httpx.RequestError as e:
            raise Exception(f"Request error: {str(e)}") from e
            
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
        """Extract value from nested dict using dot notation"""
        if not path:
            return data
            
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
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

