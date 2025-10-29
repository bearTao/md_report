"""Tests for debug API"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_debug_render_simple():
    """Test debug rendering with simple user input variables"""
    request_data = {
        "template_content": "# {{title}}\n\n{{content}}",
        "metadata_yaml": """title:
  type: string
  source: user_input
  required: true
  description: 标题
  ui_config:
    input_type: text

content:
  type: string
  source: user_input
  required: true
  description: 内容
  ui_config:
    input_type: textarea
""",
        "user_inputs": {
            "title": "测试标题",
            "content": "测试内容"
        }
    }
    
    response = client.post("/api/debug/render", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "测试标题" in data["rendered_markdown"]
    assert "测试内容" in data["rendered_markdown"]
    assert len(data["variables"]) == 2


def test_debug_render_invalid_yaml():
    """Test debug rendering with invalid YAML"""
    request_data = {
        "template_content": "# Test",
        "metadata_yaml": "invalid: yaml: content:",  # Invalid YAML
        "user_inputs": {}
    }
    
    response = client.post("/api/debug/render", json=request_data)
    assert response.status_code == 400
    assert "Invalid YAML format" in response.json()["detail"]


def test_debug_render_invalid_metadata():
    """Test debug rendering with invalid metadata structure"""
    request_data = {
        "template_content": "# Test",
        "metadata_yaml": """test_var:
  type: invalid_type  # Invalid type
  source: user_input
""",
        "user_inputs": {}
    }
    
    response = client.post("/api/debug/render", json=request_data)
    assert response.status_code == 400
    assert "Invalid metadata" in response.json()["detail"]


def test_debug_render_template_error():
    """Test debug rendering with template rendering error"""
    request_data = {
        "template_content": "# {{title}}\n\n{{ 10 / 0 }}",  # Division by zero error
        "metadata_yaml": """title:
  type: string
  source: user_input
  required: true
  description: 标题
  ui_config:
    input_type: text
""",
        "user_inputs": {"title": "测试"}
    }
    
    response = client.post("/api/debug/render", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is False
    assert data["error"] is not None
    assert "Template rendering failed" in data["error"]


def test_debug_render_with_dependencies():
    """Test debug rendering with variable dependencies"""
    request_data = {
        "template_content": "# {{title}}\n\n数字1: {{num1}}\n数字2: {{num2}}",
        "metadata_yaml": """title:
  type: string
  source: user_input
  required: true
  description: 标题
  ui_config:
    input_type: text

num1:
  type: number
  source: user_input
  required: true
  description: 数字1
  ui_config:
    input_type: number

num2:
  type: number
  source: user_input
  required: true
  description: 数字2
  dependencies:
    - num1
  ui_config:
    input_type: number
""",
        "user_inputs": {
            "title": "测试依赖",
            "num1": 10,
            "num2": 20
        }
    }
    
    response = client.post("/api/debug/render", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "数字1: 10" in data["rendered_markdown"]
    assert "数字2: 20" in data["rendered_markdown"]


def test_debug_render_empty_user_inputs():
    """Test debug rendering with no user inputs required"""
    request_data = {
        "template_content": "# Static Content",
        "metadata_yaml": "{}",
        "user_inputs": {}
    }
    
    response = client.post("/api/debug/render", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "Static Content" in data["rendered_markdown"]
    assert len(data["variables"]) == 0


def test_debug_render_variable_execution_details():
    """Test that variable execution details are returned correctly"""
    request_data = {
        "template_content": "# {{var1}} {{var2}}",
        "metadata_yaml": """var1:
  type: string
  source: user_input
  required: true
  description: Variable 1

var2:
  type: string
  source: user_input
  required: true
  description: Variable 2
""",
        "user_inputs": {
            "var1": "Value1",
            "var2": "Value2"
        }
    }
    
    response = client.post("/api/debug/render", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["variables"]) == 2
    
    for var in data["variables"]:
        assert "variable_name" in var
        assert "status" in var
        assert "value" in var
        assert "duration_ms" in var
        assert var["status"] == "success"
        assert var["duration_ms"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

