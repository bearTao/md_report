"""Tests for template renderer"""
import pytest
from app.services.renderer import TemplateRenderer


def test_simple_rendering():
    """Test basic template rendering"""
    renderer = TemplateRenderer()
    
    template = "# {{title}}\n\nHello {{name}}!"
    variables = {"title": "Test Report", "name": "Alice"}
    
    result = renderer.render(template, variables)
    assert "# Test Report" in result
    assert "Hello Alice!" in result


def test_conditional_rendering():
    """Test conditional blocks"""
    renderer = TemplateRenderer()
    
    template = """
{% if show_section %}
## Section
Content here
{% endif %}
"""
    
    result1 = renderer.render(template, {"show_section": True})
    assert "## Section" in result1
    
    result2 = renderer.render(template, {"show_section": False})
    assert "## Section" not in result2


def test_loop_rendering():
    """Test loop blocks"""
    renderer = TemplateRenderer()
    
    template = """
{% for item in items %}
- {{item.name}}: {{item.value}}
{% endfor %}
"""
    
    variables = {
        "items": [
            {"name": "Item1", "value": 10},
            {"name": "Item2", "value": 20}
        ]
    }
    
    result = renderer.render(template, variables)
    assert "- Item1: 10" in result
    assert "- Item2: 20" in result


def test_json_filter():
    """Test custom JSON filter"""
    renderer = TemplateRenderer()
    
    template = "```json\n{{data|json}}\n```"
    variables = {"data": {"key": "value", "number": 42}}
    
    result = renderer.render(template, variables)
    assert '"key": "value"' in result
    assert '"number": 42' in result


def test_template_validation():
    """Test template syntax validation"""
    renderer = TemplateRenderer()
    
    # Valid template
    valid, error = renderer.validate_template("# {{title}}")
    assert valid
    assert error == ""
    
    # Invalid template (unclosed tag)
    valid, error = renderer.validate_template("# {{title")
    assert not valid
    assert error != ""

