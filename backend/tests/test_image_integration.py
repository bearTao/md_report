"""Integration tests for image functionality"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.core.models import VariableMetadata, ImageConfig, VisionAiConfig, VariableSource


@pytest.fixture
def image_report_metadata():
    """Metadata for a report with image and vision AI"""
    return {
        "product_id": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Product ID",
            required=True
        ),
        "product_image": VariableMetadata(
            type="image",
            source=VariableSource.IMAGE,
            description="Product photo",
            dependencies=["product_id"],
            image_config=ImageConfig(
                endpoint="https://api.example.com/products/{{product_id}}/photo",
                output_format="url",
                timeout=30
            )
        ),
        "quality_analysis": VariableMetadata(
            type="string",
            source=VariableSource.VISION_AI,
            description="AI quality analysis",
            dependencies=["product_image"],
            vision_ai_config=VisionAiConfig(
                model="gpt-4o",
                image_source="product_image",
                prompt_template="请对这个产品进行质量分析，识别任何缺陷。",
                temperature=0.3,
                max_tokens=500
            )
        )
    }


@pytest.mark.asyncio
async def test_complete_image_workflow(image_report_metadata):
    """Test complete workflow: fetch image -> analyze with AI"""
    
    # 创建执行上下文
    context = ExecutionContext(
        task_id="task_integration_test",
        template_id="tpl_image_test",
        user_inputs={"product_id": "PROD-001"},
        metadata=image_report_metadata
    )
    
    # 设置用户输入
    context.set_variable("product_id", "PROD-001")
    
    # Mock image API connector
    mock_image_result = {
        "data": "https://example.com/products/PROD-001/photo",
        "mime_type": "image/jpeg",
        "size": 102400,
        "url": "https://example.com/products/PROD-001/photo",
        "markdown": "![产品](https://example.com/products/PROD-001/photo)"
    }
    
    # Mock vision AI response
    mock_ai_response = MagicMock()
    mock_ai_response.content = "产品外观良好，未发现明显缺陷。表面光滑，颜色均匀。"
    
    with patch('app.executors.image.image_api_connector') as mock_img_connector, \
         patch('langchain_openai.ChatOpenAI') as mock_llm_class:
        
        # 配置 mocks
        mock_img_connector.fetch_image = AsyncMock(return_value=mock_image_result)
        
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_ai_response)
        mock_llm_class.return_value = mock_llm
        
        # 创建调度器并执行
        scheduler = ExecutionScheduler(openai_api_key="test_key")
        results = await scheduler.execute_all(context)
        
        # 验证结果
        assert len(results) == 3  # product_id, product_image, quality_analysis
        
        # 验证图片变量
        image_result = results["product_image"]
        assert image_result.status.value == "success"
        assert context.get_variable("product_image") == mock_image_result
        
        # 验证AI分析变量
        ai_result = results["quality_analysis"]
        assert ai_result.status.value == "success"
        assert context.get_variable("quality_analysis") == "产品外观良好，未发现明显缺陷。表面光滑，颜色均匀。"


@pytest.mark.asyncio
async def test_multiple_images_workflow():
    """Test workflow with multiple images"""
    
    metadata = {
        "site_id": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Site ID"
        ),
        "site_photos": VariableMetadata(
            type="array",
            source=VariableSource.IMAGE,
            description="Site photos",
            dependencies=["site_id"],
            image_config=ImageConfig(
                endpoint="https://api.example.com/sites/{{site_id}}/photos",
                output_format="url",
                multiple=True
            )
        ),
        "safety_report": VariableMetadata(
            type="string",
            source=VariableSource.VISION_AI,
            description="Safety analysis",
            dependencies=["site_photos"],
            vision_ai_config=VisionAiConfig(
                model="gpt-4o",
                image_source="site_photos",
                prompt_template="分析这些现场照片，识别安全隐患。"
            )
        )
    }
    
    context = ExecutionContext(
        task_id="task_multi_image",
        template_id="tpl_multi",
        user_inputs={"site_id": "SITE-001"},
        metadata=metadata
    )
    
    context.set_variable("site_id", "SITE-001")
    
    # Mock multiple images
    mock_images = [
        {"url": "https://example.com/site/photo1.jpg", "mime_type": "image/jpeg"},
        {"url": "https://example.com/site/photo2.jpg", "mime_type": "image/jpeg"},
        {"url": "https://example.com/site/photo3.jpg", "mime_type": "image/jpeg"}
    ]
    
    mock_ai_response = MagicMock()
    mock_ai_response.content = "发现3处安全隐患：1. 防护栏缺失 2. 安全标识不足 3. 堆放杂乱"
    
    with patch('app.executors.image.image_api_connector') as mock_connector, \
         patch('langchain_openai.ChatOpenAI') as mock_llm_class:
        
        mock_connector.fetch_multiple_images = AsyncMock(return_value=mock_images)
        
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_ai_response)
        mock_llm_class.return_value = mock_llm
        
        scheduler = ExecutionScheduler(openai_api_key="test_key")
        results = await scheduler.execute_all(context)
        
        # 验证
        assert len(results) == 3
        
        assert results["site_photos"].status.value == "success"
        photos = context.get_variable("site_photos")
        assert len(photos) == 3
        
        assert results["safety_report"].status.value == "success"
        safety_report = context.get_variable("safety_report")
        assert "安全隐患" in safety_report


@pytest.mark.asyncio
async def test_image_error_handling():
    """Test error handling in image workflow"""
    
    metadata = {
        "product_image": VariableMetadata(
            type="image",
            source=VariableSource.IMAGE,
            description="Product image",
            image_config=ImageConfig(
                endpoint="https://invalid.example.com/image.jpg",
                output_format="base64"
            )
        )
    }
    
    context = ExecutionContext(
        task_id="task_error",
        template_id="tpl_error",
        user_inputs={},
        metadata=metadata
    )
    
    # Mock image fetch failure
    with patch('app.executors.image.image_api_connector') as mock_connector:
        mock_connector.fetch_image = AsyncMock(
            side_effect=Exception("Failed to fetch image: HTTP 404")
        )
        
        scheduler = ExecutionScheduler()
        
        # 图片获取失败会抛出异常（因为是required变量）
        # 或者返回失败结果（如果是optional）
        try:
            results = await scheduler.execute_all(context)
            # 如果没有抛出异常，检查结果
            image_result = results["product_image"]
            assert image_result.status.value == "failed"
            assert "Failed to fetch image" in str(image_result.error)
        except Exception as e:
            # 如果抛出异常，验证异常信息
            assert "Failed to fetch image" in str(e)


@pytest.mark.asyncio
async def test_dependency_resolution():
    """Test that dependencies are resolved correctly"""
    
    metadata = {
        "user_id": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="User ID"
        ),
        "profile_photo": VariableMetadata(
            type="image",
            source=VariableSource.IMAGE,
            description="Profile photo",
            dependencies=["user_id"],
            image_config=ImageConfig(
                endpoint="https://api.example.com/users/{{user_id}}/photo"
            )
        ),
        "photo_analysis": VariableMetadata(
            type="string",
            source=VariableSource.VISION_AI,
            description="Photo analysis",
            dependencies=["profile_photo"],
            vision_ai_config=VisionAiConfig(
                model="gpt-4o",
                image_source="profile_photo",
                prompt_template="Describe the photo"
            )
        )
    }
    
    context = ExecutionContext(
        task_id="task_deps",
        template_id="tpl_deps",
        user_inputs={"user_id": "USER123"},
        metadata=metadata
    )
    
    # Mock responses
    with patch('app.executors.image.image_api_connector') as mock_img, \
         patch('langchain_openai.ChatOpenAI') as mock_llm_class:
        
        mock_img.fetch_image = AsyncMock(return_value={
            "url": "https://example.com/users/USER123/photo",
            "data": "https://example.com/users/USER123/photo",
            "mime_type": "image/jpeg",
            "size": 1024,
            "markdown": "![照片](https://example.com/users/USER123/photo)"
        })
        
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "A profile photo"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_class.return_value = mock_llm
        
        scheduler = ExecutionScheduler(openai_api_key="test_key")
        
        # 构建DAG
        dag = scheduler.build_dag(metadata)
        batches = scheduler.get_execution_batches(dag)
        
        # 验证执行顺序
        assert len(batches) == 3
        assert "user_id" in batches[0]
        assert "profile_photo" in batches[1]
        assert "photo_analysis" in batches[2]
        
        # 执行
        results = await scheduler.execute_all(context)
        assert all(r.status.value == "success" for r in results.values())

