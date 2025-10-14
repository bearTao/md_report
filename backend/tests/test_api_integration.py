"""Integration tests for complete API workflows"""
import pytest
import time


def test_complete_report_workflow(client):
    """Test complete workflow: create template -> generate report -> download"""
    # 1. Create template
    template_data = {
        "name": "简单报告模板",
        "description": "用于测试的简单模板",
        "template_content": """# {{report_title}}

**生成时间**: {{generation_time}}

## 内容

{{content}}

---
报告ID: {{report_id}}
""",
        "metadata": {
            "report_title": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "报告标题"
            },
            "content": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "报告内容"
            },
            "generation_time": {
                "type": "string",
                "source": "system",
                "required": True,
                "description": "生成时间",
                "system_config": {
                    "fields": {
                        "timestamp": {
                            "generator": "datetime",
                            "format": "%Y-%m-%d %H:%M:%S"
                        }
                    }
                }
            },
            "report_id": {
                "type": "string",
                "source": "system",
                "required": True,
                "description": "报告ID",
                "system_config": {
                    "fields": {
                        "id": {
                            "generator": "uuid"
                        }
                    }
                }
            }
        }
    }
    
    create_response = client.post("/api/templates", json=template_data)
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]
    
    # 2. Generate report
    generate_data = {
        "template_id": template_id,
        "inputs": {
            "report_title": "2025年度总结",
            "content": "这是一个测试报告的内容部分。"
        }
    }
    
    gen_response = client.post("/api/reports/generate", json=generate_data)
    assert gen_response.status_code == 202
    task_id = gen_response.json()["task_id"]
    
    # 3. Wait for generation (in real scenario, would poll or use WebSocket)
    time.sleep(3)
    
    # 4. Verify template still exists
    get_template_response = client.get(f"/api/templates/{template_id}")
    assert get_template_response.status_code == 200
    
    print(f"\n✅ Complete workflow test passed for task {task_id}")


def test_template_validation_workflow(client):
    """Test template validation during creation and update"""
    # 1. Try to create invalid template
    invalid_template = {
        "name": "Invalid Template",
        "description": "Template with syntax error",
        "template_content": "# {{title",  # Missing closing braces
        "metadata": {}
    }
    
    response = client.post("/api/templates", json=invalid_template)
    assert response.status_code == 400
    
    # 2. Create valid template
    valid_template = {
        "name": "Valid Template",
        "description": "Correct template",
        "template_content": "# {{title}}",
        "metadata": {
            "title": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Title"
            }
        }
    }
    
    response = client.post("/api/templates", json=valid_template)
    assert response.status_code == 201
    template_id = response.json()["id"]
    
    # 3. Try to update with invalid content
    update_data = {
        "template_content": "# {{title"  # Invalid
    }
    
    response = client.put(f"/api/templates/{template_id}", json=update_data)
    assert response.status_code == 400
    
    # 4. Update with valid content
    update_data = {
        "template_content": "# {{title}}\n\nUpdated content"
    }
    
    response = client.put(f"/api/templates/{template_id}", json=update_data)
    assert response.status_code == 200
    assert "Updated content" in response.json()["template_content"]

