"""Tests for ExecutionContext"""
import pytest
from app.services.context import ExecutionContext
from app.core.models import VariableMetadata, VariableSource


def test_context_creation():
    """Test creating execution context"""
    metadata = {
        "var1": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Test variable",
            required=True
        )
    }
    
    context = ExecutionContext(
        task_id="task_123",
        template_id="tpl_456",
        user_inputs={"var1": "test_value"},
        metadata=metadata
    )
    
    assert context.task_id == "task_123"
    assert context.template_id == "tpl_456"
    assert context.user_inputs == {"var1": "test_value"}


def test_set_and_get_variable():
    """Test setting and getting variables"""
    context = ExecutionContext("task_1", "tpl_1", {}, {})
    
    context.set_variable("test_var", "test_value")
    assert context.has_variable("test_var")
    assert context.get_variable("test_var") == "test_value"


def test_interpolate_string():
    """Test string interpolation"""
    context = ExecutionContext("task_1", "tpl_1", {}, {})
    context.set_variable("name", "Alice")
    context.set_variable("age", 30)
    
    result = context.interpolate_string("Hello {{name}}, you are {{age}} years old")
    assert result == "Hello Alice, you are 30 years old"


def test_interpolate_dict():
    """Test dictionary interpolation"""
    context = ExecutionContext("task_1", "tpl_1", {}, {})
    context.set_variable("city", "Beijing")
    
    data = {
        "location": "{{city}}",
        "nested": {
            "place": "{{city}}"
        }
    }
    
    result = context.interpolate_dict(data)
    assert result["location"] == "Beijing"
    assert result["nested"]["place"] == "Beijing"


def test_dependencies():
    """Test dependency checking"""
    metadata = {
        "var1": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Base variable",
            required=True
        ),
        "var2": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="Dependent variable",
            required=True,
            dependencies=["var1"]
        )
    }
    
    context = ExecutionContext("task_1", "tpl_1", {}, metadata)
    
    # var2 depends on var1
    ready, missing = context.check_dependencies_ready("var2")
    assert not ready
    assert "var1" in missing
    
    # After setting var1
    context.set_variable("var1", "value1")
    ready, missing = context.check_dependencies_ready("var2")
    assert ready
    assert len(missing) == 0

