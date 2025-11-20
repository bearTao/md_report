"""Unit tests for ImageExecutor"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.executors.image import ImageExecutor
from app.core.models import VariableMetadata, ImageConfig, VariableSource
from app.services.context import ExecutionContext


@pytest.fixture
def mock_context():
    """Mock execution context"""
    metadata = {
        "test_var": VariableMetadata(
            type="image",
            source=VariableSource.IMAGE,
            description="Test image",
            image_config=ImageConfig(
                endpoint="https://picsum.photos/400/300",
                output_format="base64"
            )
        )
    }
    context = ExecutionContext(
        task_id="task_123",
        template_id="tpl_1",
        user_inputs={},
        metadata=metadata
    )
    return context


@pytest.mark.asyncio
async def test_image_executor_single_base64(mock_context):
    """Test fetching single image as base64"""
    # 准备测试数据
    var_name = "test_var"
    metadata = mock_context.metadata[var_name]
    
    # Mock image_api_connector
    mock_result = {
        "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "mime_type": "image/png",
        "size": 68,
        "url": "https://example.com/image.png",
        "markdown": "![图片](data:image/png;base64,...)"
    }
    
    with patch('app.executors.image.image_api_connector') as mock_connector:
        mock_connector.fetch_image = AsyncMock(return_value=mock_result)
        
        # 执行
        executor = ImageExecutor(var_name, metadata, mock_context)
        result = await executor._execute_impl()
        
        # 验证
        assert result == mock_result
        assert result["mime_type"] == "image/png"
        assert result["size"] == 68
        mock_connector.fetch_image.assert_called_once()


@pytest.mark.asyncio
async def test_image_executor_with_headers(mock_context):
    """Test image executor with custom headers"""
    # 更新配置
    metadata = VariableMetadata(
        type="image",
        source=VariableSource.IMAGE,
        description="Test",
        image_config=ImageConfig(
            endpoint="https://api.example.com/image",
            headers={"Authorization": "Bearer token123"},
            output_format="url"
        )
    )
    
    mock_result = {
        "data": "https://api.example.com/image",
        "mime_type": "image/jpeg",
        "size": 1024,
        "url": "https://api.example.com/image",
        "markdown": "![图片](https://api.example.com/image)"
    }
    
    with patch('app.executors.image.image_api_connector') as mock_connector:
        mock_connector.fetch_image = AsyncMock(return_value=mock_result)
        
        executor = ImageExecutor("test_var", metadata, mock_context)
        result = await executor._execute_impl()
        
        assert result["data"] == "https://api.example.com/image"
        mock_connector.fetch_image.assert_called_once()
        
        # 验证headers传递
        call_args = mock_connector.fetch_image.call_args
        assert call_args.kwargs['headers'] == {"Authorization": "Bearer token123"}


@pytest.mark.asyncio
async def test_image_executor_multiple_images(mock_context):
    """Test fetching multiple images"""
    # 配置多张图片
    metadata = VariableMetadata(
        type="array",
        source=VariableSource.IMAGE,
        description="Test",
        image_config=ImageConfig(
            endpoint="{{image_urls}}",
            multiple=True,
            output_format="url"
        )
    )
    
    # 在context中设置图片URLs
    mock_context.set_variable("image_urls", [
        "https://example.com/1.png",
        "https://example.com/2.png"
    ])
    
    mock_results = [
        {"data": "https://example.com/1.png", "mime_type": "image/png", "size": 100, "url": "https://example.com/1.png", "markdown": "![图片](https://example.com/1.png)"},
        {"data": "https://example.com/2.png", "mime_type": "image/png", "size": 200, "url": "https://example.com/2.png", "markdown": "![图片](https://example.com/2.png)"}
    ]
    
    with patch('app.executors.image.image_api_connector') as mock_connector:
        mock_connector.fetch_multiple_images = AsyncMock(return_value=mock_results)
        
        executor = ImageExecutor("test_var", metadata, mock_context)
        result = await executor._execute_impl()
        
        assert len(result) == 2
        assert result[0]["url"] == "https://example.com/1.png"
        assert result[1]["url"] == "https://example.com/2.png"


@pytest.mark.asyncio
async def test_image_executor_error_handling(mock_context):
    """Test error handling"""
    metadata = mock_context.metadata["test_var"]
    
    with patch('app.executors.image.image_api_connector') as mock_connector:
        mock_connector.fetch_image = AsyncMock(side_effect=Exception("Network error"))
        
        executor = ImageExecutor("test_var", metadata, mock_context)
        
        with pytest.raises(Exception) as exc_info:
            await executor._execute_impl()
        
        assert "Failed to fetch image" in str(exc_info.value)


@pytest.mark.asyncio
async def test_image_executor_missing_config(mock_context):
    """Test with missing image_config"""
    metadata = VariableMetadata(
        type="image",
        source=VariableSource.IMAGE,
        description="Test"
        # image_config is None
    )
    
    executor = ImageExecutor("test_var", metadata, mock_context)
    
    with pytest.raises(Exception) as exc_info:
        await executor._execute_impl()
    
    assert "Missing image_config" in str(exc_info.value)

