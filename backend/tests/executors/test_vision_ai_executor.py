"""Unit tests for VisionAiExecutor"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.executors.vision_ai import VisionAiExecutor
from app.core.models import VariableMetadata, VisionAiConfig, VariableSource
from app.services.context import ExecutionContext


@pytest.fixture
def mock_context_with_image():
    """Mock execution context with image data"""
    metadata = {
        "product_image": VariableMetadata(
            type="image",
            source=VariableSource.IMAGE,
            description="Product image"
        ),
        "quality_check": VariableMetadata(
            type="string",
            source=VariableSource.VISION_AI,
            description="Quality analysis",
            dependencies=["product_image"],
            vision_ai_config=VisionAiConfig(
                model="gpt-4o",
                image_source="product_image",
                prompt_template="请检查这个产品的外观质量"
            )
        )
    }
    
    context = ExecutionContext(
        task_id="task_123",
        template_id="tpl_1",
        user_inputs={},
        metadata=metadata
    )
    
    # 设置图片数据
    context.set_variable("product_image", {
        "data": "base64_encoded_data",
        "mime_type": "image/png",
        "url": "https://example.com/product.png",
        "markdown": "![产品](https://example.com/product.png)"
    })
    
    return context


@pytest.mark.asyncio
async def test_vision_ai_executor_basic(mock_context_with_image):
    """Test basic vision AI execution"""
    var_name = "quality_check"
    metadata = mock_context_with_image.metadata[var_name]
    
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = "产品外观良好，未发现明显缺陷。"
    
    with patch('langchain_openai.ChatOpenAI') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_class.return_value = mock_llm
        
        executor = VisionAiExecutor(
            var_name,
            metadata,
            mock_context_with_image,
            openai_api_key="test_key"
        )
        
        result = await executor._execute_impl()
        
        assert result == "产品外观良好，未发现明显缺陷。"
        mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_vision_ai_extract_image_urls_from_dict(mock_context_with_image):
    """Test extracting image URLs from dict format"""
    metadata = mock_context_with_image.metadata["quality_check"]
    executor = VisionAiExecutor("quality_check", metadata, mock_context_with_image)
    
    # Test with dict containing URL
    image_data = {
        "url": "https://example.com/image.png",
        "mime_type": "image/png"
    }
    urls = executor._extract_image_urls(image_data)
    assert urls == ["https://example.com/image.png"]
    
    # Test with dict containing base64
    image_data = {
        "data": "base64string",
        "mime_type": "image/jpeg"
    }
    urls = executor._extract_image_urls(image_data)
    assert len(urls) == 1
    assert urls[0].startswith("data:image/jpeg;base64,")


@pytest.mark.asyncio
async def test_vision_ai_extract_image_urls_from_string(mock_context_with_image):
    """Test extracting image URLs from string"""
    metadata = mock_context_with_image.metadata["quality_check"]
    executor = VisionAiExecutor("quality_check", metadata, mock_context_with_image)
    
    # Test HTTP URL
    urls = executor._extract_image_urls("https://example.com/image.png")
    assert urls == ["https://example.com/image.png"]
    
    # Test data URI
    data_uri = "data:image/png;base64,iVBORw0KGgo..."
    urls = executor._extract_image_urls(data_uri)
    assert urls == [data_uri]


@pytest.mark.asyncio
async def test_vision_ai_extract_image_urls_from_list(mock_context_with_image):
    """Test extracting image URLs from list"""
    metadata = mock_context_with_image.metadata["quality_check"]
    executor = VisionAiExecutor("quality_check", metadata, mock_context_with_image)
    
    image_list = [
        {"url": "https://example.com/1.png"},
        {"url": "https://example.com/2.png"},
        "https://example.com/3.png"
    ]
    
    urls = executor._extract_image_urls(image_list)
    assert len(urls) == 3
    assert "https://example.com/1.png" in urls
    assert "https://example.com/2.png" in urls
    assert "https://example.com/3.png" in urls


@pytest.mark.asyncio
async def test_vision_ai_with_system_prompt(mock_context_with_image):
    """Test with system prompt"""
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.VISION_AI,
        description="Quality check with system prompt",
        dependencies=["product_image"],
        vision_ai_config=VisionAiConfig(
            model="gpt-4o",
            image_source="product_image",
            prompt_template="检查质量",
            system_prompt="你是专业的质检专家"
        )
    )
    
    mock_response = MagicMock()
    mock_response.content = "专业质检结果"
    
    with patch('langchain_openai.ChatOpenAI') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_class.return_value = mock_llm
        
        executor = VisionAiExecutor(
            "test_var",
            metadata,
            mock_context_with_image,
            openai_api_key="test_key"
        )
        
        result = await executor._execute_impl()
        
        assert result == "专业质检结果"
        
        # 验证调用参数包含system message
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert len(call_args) == 2  # SystemMessage + HumanMessage


@pytest.mark.asyncio
async def test_vision_ai_missing_image_source(mock_context_with_image):
    """Test with missing image source variable"""
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.VISION_AI,
        description="Test missing source",
        vision_ai_config=VisionAiConfig(
            model="gpt-4o",
            image_source="nonexistent_image",
            prompt_template="Analyze"
        )
    )
    
    executor = VisionAiExecutor("test_var", metadata, mock_context_with_image)
    
    with pytest.raises(Exception) as exc_info:
        await executor._execute_impl()
    
    assert "not found in context" in str(exc_info.value)


@pytest.mark.asyncio
async def test_vision_ai_missing_config(mock_context_with_image):
    """Test with missing vision_ai_config"""
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.VISION_AI,
        description="Test"
        # vision_ai_config is None
    )
    
    executor = VisionAiExecutor("test_var", metadata, mock_context_with_image)
    
    with pytest.raises(Exception) as exc_info:
        await executor._execute_impl()
    
    assert "Missing vision_ai_config" in str(exc_info.value)


@pytest.mark.asyncio
async def test_vision_ai_with_prompt_interpolation(mock_context_with_image):
    """Test prompt template interpolation"""
    mock_context_with_image.set_variable("product_type", "手机")
    
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.VISION_AI,
        description="Test prompt interpolation",
        dependencies=["product_image", "product_type"],
        vision_ai_config=VisionAiConfig(
            model="gpt-4o",
            image_source="product_image",
            prompt_template="请检查这个{{product_type}}的外观质量"
        )
    )
    
    mock_response = MagicMock()
    mock_response.content = "手机外观完好"
    
    with patch('langchain_openai.ChatOpenAI') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_class.return_value = mock_llm
        
        executor = VisionAiExecutor(
            "test_var",
            metadata,
            mock_context_with_image,
            openai_api_key="test_key"
        )
        
        result = await executor._execute_impl()
        
        assert result == "手机外观完好"
        
        # 验证prompt被正确插值
        call_args = mock_llm.ainvoke.call_args[0][0]
        message_content = call_args[-1].content  # Last message (HumanMessage)
        assert any("请检查这个手机的外观质量" in str(item) for item in message_content)

