"""Tests for API enhancements: JMESPath, retry logic, and flexible response_mapping"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.connectors.api import api_connector, ApiConnector
from app.core.models import ApiConfig, VariableMetadata, VariableSource
from app.executors.api import ApiExecutor
from app.services.context import ExecutionContext


class TestJMESPathExtraction:
    """Test JMESPath path extraction functionality"""
    
    def test_simple_path(self):
        """Test simple dot notation path"""
        data = {"data": {"user": {"name": "Alice"}}}
        result = api_connector._extract_path(data, "data.user.name")
        assert result == "Alice"
    
    def test_array_index(self):
        """Test array indexing"""
        data = {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
        result = api_connector._extract_path(data, "items[1].id")
        assert result == 2
    
    def test_array_slice(self):
        """Test array slicing"""
        data = {"items": [1, 2, 3, 4, 5]}
        result = api_connector._extract_path(data, "items[:3]")
        assert result == [1, 2, 3]
    
    def test_array_projection(self):
        """Test array projection (extract all)"""
        data = {
            "products": [
                {"name": "A", "price": 10},
                {"name": "B", "price": 20}
            ]
        }
        result = api_connector._extract_path(data, "products[*].name")
        assert result == ["A", "B"]
    
    def test_filter_expression(self):
        """Test filter expression"""
        data = {
            "items": [
                {"name": "A", "price": 50},
                {"name": "B", "price": 150},
                {"name": "C", "price": 200}
            ]
        }
        result = api_connector._extract_path(data, "items[?price > `100`]")
        assert len(result) == 2
        assert result[0]["name"] == "B"
        assert result[1]["name"] == "C"
    
    def test_function_length(self):
        """Test JMESPath function"""
        data = {"items": [1, 2, 3, 4, 5]}
        result = api_connector._extract_path(data, "length(items)")
        assert result == 5
    
    def test_fallback_to_simple_dot(self):
        """Test fallback to simple dot notation for backward compatibility"""
        data = {"a": {"b": {"c": "value"}}}
        result = api_connector._extract_path(data, "a.b.c")
        assert result == "value"
    
    def test_empty_path_returns_full_data(self):
        """Test that empty path returns full data"""
        data = {"key": "value"}
        result = api_connector._extract_path(data, "")
        assert result == data


class TestResponseMappingModes:
    """Test three modes of response_mapping"""
    
    @pytest.mark.asyncio
    async def test_mode1_no_mapping(self):
        """Test Mode 1: No mapping - return full response"""
        metadata = VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="Test",
            api_config=ApiConfig(
                endpoint="http://example.com/api",
                method="GET",
                response_mapping=None  # No mapping
            )
        )
        
        context = ExecutionContext(task_id="test", template_id="test", metadata={})
        executor = ApiExecutor("test_var", metadata, context)
        
        mock_response = {"status": "ok", "data": {"value": 123}}
        
        with patch.object(api_connector, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await executor._execute_impl()
            assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_mode2_string_path(self):
        """Test Mode 2: String path - extract single path"""
        metadata = VariableMetadata(
            type="array",
            source=VariableSource.API,
            description="Test",
            api_config=ApiConfig(
                endpoint="http://example.com/api",
                method="GET",
                response_mapping="data.items"  # String path
            )
        )
        
        context = ExecutionContext(task_id="test", template_id="test", metadata={})
        executor = ApiExecutor("test_var", metadata, context)
        
        mock_response = {
            "status": "ok",
            "data": {
                "items": [{"id": 1}, {"id": 2}]
            }
        }
        
        with patch.object(api_connector, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await executor._execute_impl()
            assert result == [{"id": 1}, {"id": 2}]
    
    @pytest.mark.asyncio
    async def test_mode3_dict_mapping(self):
        """Test Mode 3: Dict mapping - map multiple fields"""
        metadata = VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="Test",
            api_config=ApiConfig(
                endpoint="http://example.com/api",
                method="GET",
                response_mapping={  # Dict mapping
                    "temp": "data.temperature",
                    "condition": "data.weather.condition"
                }
            )
        )
        
        context = ExecutionContext(task_id="test", template_id="test", metadata={})
        executor = ApiExecutor("test_var", metadata, context)
        
        mock_response = {
            "data": {
                "temperature": 22.5,
                "weather": {"condition": "Sunny"}
            }
        }
        
        with patch.object(api_connector, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await executor._execute_impl()
            assert result == {"temp": 22.5, "condition": "Sunny"}


class TestRetryLogic:
    """Test retry functionality"""
    
    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        """Test that no retry occurs on successful request"""
        connector = ApiConnector()
        
        with patch.object(connector, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "ok"}
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = await connector.request(
                method="GET",
                url="http://example.com",
                retry_count=3
            )
            
            assert result == {"result": "ok"}
            # Should only call once (no retries)
            assert mock_client.request.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_500_error(self):
        """Test retry on 500 error"""
        connector = ApiConnector()
        
        with patch.object(connector, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # First two calls fail with 500, third succeeds
            mock_response_fail = MagicMock()
            mock_response_fail.status_code = 500
            mock_response_fail.text = "Internal Server Error"
            mock_response_fail.raise_for_status.side_effect = Exception("HTTP 500")
            
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"result": "ok"}
            
            import httpx
            
            # Simulate 500 errors then success
            call_count = 0
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise httpx.HTTPStatusError(
                        "Server Error",
                        request=MagicMock(),
                        response=mock_response_fail
                    )
                return mock_response_success
            
            mock_client.request.side_effect = side_effect
            
            # Should succeed after retries
            result = await connector.request(
                method="GET",
                url="http://example.com",
                retry_count=3,
                retry_status_codes=[500],
                retry_backoff=0.01  # Short backoff for testing
            )
            
            assert result == {"result": "ok"}
            assert call_count == 3  # 2 failures + 1 success
    
    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        """Test that 404 errors don't trigger retry"""
        connector = ApiConnector()
        
        with patch.object(connector, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            
            import httpx
            
            mock_client.request.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response
            )
            
            with pytest.raises(Exception, match="HTTP 404"):
                await connector.request(
                    method="GET",
                    url="http://example.com",
                    retry_count=3,
                    retry_status_codes=[500, 503]  # 404 not in list
                )
            
            # Should only try once
            assert mock_client.request.call_count == 1


class TestBackwardCompatibility:
    """Test backward compatibility with existing configurations"""
    
    @pytest.mark.asyncio
    async def test_empty_dict_mapping(self):
        """Test that empty dict response_mapping returns full response"""
        metadata = VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="Test",
            api_config=ApiConfig(
                endpoint="http://example.com/api",
                response_mapping={}  # Empty dict
            )
        )
        
        context = ExecutionContext(task_id="test", template_id="test", metadata={})
        executor = ApiExecutor("test_var", metadata, context)
        
        mock_response = {"full": "response"}
        
        with patch.object(api_connector, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await executor._execute_impl()
            assert result == mock_response
    
    def test_parameters_support_any_type(self):
        """Test that parameters now support any type, not just strings"""
        config = ApiConfig(
            endpoint="http://example.com",
            parameters={
                "string_param": "value",
                "number_param": 42,
                "bool_param": True,
                "list_param": [1, 2, 3]
            }
        )
        
        assert config.parameters["string_param"] == "value"
        assert config.parameters["number_param"] == 42
        assert config.parameters["bool_param"] is True
        assert config.parameters["list_param"] == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


