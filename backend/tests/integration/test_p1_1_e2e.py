"""End-to-end tests for P1.1 Image Support"""

import os
import pytest
import httpx
import asyncio
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


class TestImageSupport:
    """E2E tests for image functionality"""
    
    @pytest.fixture
    async def client(self):
        """HTTP client fixture"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client
    
    @pytest.fixture
    def image_template_metadata(self) -> Dict[str, Any]:
        """Template metadata with image variables"""
        return {
            "product_id": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "产品ID",
                "ui_config": {
                    "input_type": "text",
                    "placeholder": "输入产品ID"
                }
            },
            "product_photo": {
                "type": "image",
                "source": "image",
                "description": "产品照片",
                "dependencies": ["product_id"],
                "image_config": {
                    "endpoint": "https://picsum.photos/400/300",  # 使用公共测试图片API
                    "method": "GET",
                    "output_format": "url",
                    "timeout": 30
                }
            },
            "quality_check": {
                "type": "string",
                "source": "vision_ai",
                "description": "质量检测报告",
                "dependencies": ["product_photo"],
                "vision_ai_config": {
                    "model": "gpt-4o",
                    "image_source": "product_photo",
                    "prompt_template": "请简要描述这张图片的内容（不超过50字）。",
                    "temperature": 0.3,
                    "max_tokens": 100
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_create_image_template(self, client, image_template_metadata):
        """Test creating template with image variables"""
        
        template_data = {
            "name": "产品质检报告_图片测试",
            "description": "包含图片获取和AI分析的测试模板",
            "template_content": """
# 产品质检报告

## 产品信息
- 产品ID: {{product_id}}

## 产品照片
{{product_photo.markdown}}

## AI质量分析
{{quality_check}}
            """.strip(),
            "metadata": image_template_metadata
        }
        
        response = await client.post(
            f"{BASE_URL}/api/templates/",
            json=template_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "产品质检报告_图片测试"
        assert "template_id" in data
        
        # 验证metadata保存正确
        assert "product_photo" in data["metadata"]
        assert data["metadata"]["product_photo"]["source"] == "image"
        assert "image_config" in data["metadata"]["product_photo"]
        
        return data["template_id"]
    
    @pytest.mark.asyncio
    async def test_generate_report_with_image(self, client, image_template_metadata):
        """Test generating report with image fetching"""
        
        # 1. 先创建模板
        template_data = {
            "name": f"图片测试模板_{asyncio.get_event_loop().time()}",
            "description": "测试图片功能",
            "template_content": "# 报告\n\n产品ID: {{product_id}}\n\n照片: {{product_photo.markdown}}",
            "metadata": {
                k: v for k, v in image_template_metadata.items() 
                if k != "quality_check"  # 暂时不包含AI分析，只测试图片获取
            }
        }
        
        create_resp = await client.post(
            f"{BASE_URL}/api/templates/",
            json=template_data
        )
        assert create_resp.status_code == 201
        template_id = create_resp.json()["template_id"]
        
        # 2. 生成报告
        generate_data = {
            "template_id": template_id,
            "user_inputs": {
                "product_id": "TEST-PROD-001"
            }
        }
        
        gen_resp = await client.post(
            f"{BASE_URL}/api/reports/generate",
            json=generate_data
        )
        
        assert gen_resp.status_code == 200
        gen_data = gen_resp.json()
        assert "task_id" in gen_data
        
        task_id = gen_data["task_id"]
        
        # 3. 等待任务完成
        max_wait = 30
        waited = 0
        task_completed = False
        
        while waited < max_wait:
            status_resp = await client.get(f"{BASE_URL}/api/reports/status/{task_id}")
            assert status_resp.status_code == 200
            
            status_data = status_resp.json()
            
            if status_data["status"] == "completed":
                task_completed = True
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Task failed: {status_data.get('error')}")
            
            await asyncio.sleep(1)
            waited += 1
        
        assert task_completed, "Task did not complete in time"
        
        # 4. 检查变量执行结果
        variables = status_data.get("variables", [])
        
        product_photo_var = next(
            (v for v in variables if v["variable_name"] == "product_photo"),
            None
        )
        
        assert product_photo_var is not None
        assert product_photo_var["status"] == "success"
        
        # 5. 获取生成的报告
        report_resp = await client.get(f"{BASE_URL}/api/reports/{task_id}")
        assert report_resp.status_code == 200
        
        report_data = report_resp.json()
        assert "markdown_content" in report_data
        assert "TEST-PROD-001" in report_data["markdown_content"]
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="需要OpenAI API Key才能测试Vision AI"
    )
    async def test_vision_ai_workflow(self, client, image_template_metadata):
        """Test complete vision AI workflow (requires real API key)"""
        
        # 创建完整模板（包含Vision AI）
        template_data = {
            "name": f"完整图片AI测试_{asyncio.get_event_loop().time()}",
            "description": "测试图片+Vision AI",
            "template_content": """
# 产品质检报告

产品ID: {{product_id}}

## 产品照片
{{product_photo.markdown}}

## AI分析结果
{{quality_check}}
            """.strip(),
            "metadata": image_template_metadata
        }
        
        create_resp = await client.post(
            f"{BASE_URL}/api/templates/",
            json=template_data
        )
        assert create_resp.status_code == 201
        template_id = create_resp.json()["template_id"]
        
        # 生成报告
        generate_data = {
            "template_id": template_id,
            "user_inputs": {
                "product_id": "VISION-TEST-001"
            }
        }
        
        gen_resp = await client.post(
            f"{BASE_URL}/api/reports/generate",
            json=generate_data
        )
        
        assert gen_resp.status_code == 200
        task_id = gen_resp.json()["task_id"]
        
        # 等待完成
        max_wait = 60  # Vision AI可能需要更长时间
        waited = 0
        
        while waited < max_wait:
            status_resp = await client.get(f"{BASE_URL}/api/reports/status/{task_id}")
            status_data = status_resp.json()
            
            if status_data["status"] == "completed":
                # 验证所有变量都执行成功
                variables = status_data["variables"]
                
                photo_var = next(v for v in variables if v["variable_name"] == "product_photo")
                assert photo_var["status"] == "success"
                
                ai_var = next(v for v in variables if v["variable_name"] == "quality_check")
                assert ai_var["status"] == "success"
                
                # 获取报告
                report_resp = await client.get(f"{BASE_URL}/api/reports/{task_id}")
                report_data = report_resp.json()
                
                assert "markdown_content" in report_data
                assert len(report_data["markdown_content"]) > 100  # AI应该生成了内容
                
                return
            
            elif status_data["status"] == "failed":
                pytest.fail(f"Task failed: {status_data.get('error')}")
            
            await asyncio.sleep(2)
            waited += 2
        
        pytest.fail("Task did not complete in time")
    
    @pytest.mark.asyncio
    async def test_image_with_headers(self, client):
        """Test image fetching with custom headers"""
        
        metadata = {
            "auth_token": {
                "type": "string",
                "source": "user_input",
                "description": "认证token"
            },
            "secure_image": {
                "type": "image",
                "source": "image",
                "dependencies": ["auth_token"],
                "image_config": {
                    "endpoint": "https://httpbin.org/image/jpeg",
                    "method": "GET",
                    "headers": {
                        "Authorization": "Bearer {{auth_token}}"
                    },
                    "output_format": "base64"
                }
            }
        }
        
        template_data = {
            "name": f"带认证的图片测试_{asyncio.get_event_loop().time()}",
            "description": "测试带headers的图片请求",
            "template_content": "![图片]({{secure_image.markdown}})",
            "metadata": metadata
        }
        
        create_resp = await client.post(
            f"{BASE_URL}/api/templates/",
            json=template_data
        )
        assert create_resp.status_code == 201
        
        # 生成报告
        template_id = create_resp.json()["template_id"]
        gen_resp = await client.post(
            f"{BASE_URL}/api/reports/generate",
            json={
                "template_id": template_id,
                "user_inputs": {
                    "auth_token": "test_token_123"
                }
            }
        )
        
        assert gen_resp.status_code == 200


import os  # 为skipif导入


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])

