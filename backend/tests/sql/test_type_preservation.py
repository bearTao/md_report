"""Tests for type preservation in variable interpolation"""
import pytest
from app.services.context import ExecutionContext
from app.core.models import VariableMetadata, VariableSource


class TestTypePreservation:
    """Test type preservation in interpolation"""
    
    def test_pure_number_preserves_type(self):
        """Test that pure number variable reference preserves type"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {"count": 15, "price": 99.99}
        
        data = {"count": "{{count}}", "price": "{{price}}"}
        result = context.interpolate_dict(data)
        
        assert result["count"] == 15
        assert isinstance(result["count"], int)
        assert result["price"] == 99.99
        assert isinstance(result["price"], float)
    
    def test_pure_boolean_preserves_type(self):
        """Test that pure boolean variable reference preserves type"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {"active": True, "completed": False}
        
        data = {"active": "{{active}}", "completed": "{{completed}}"}
        result = context.interpolate_dict(data)
        
        assert result["active"] is True
        assert isinstance(result["active"], bool)
        assert result["completed"] is False
        assert isinstance(result["completed"], bool)
    
    def test_pure_string_preserves_type(self):
        """Test that pure string variable reference preserves type"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {"name": "Alice", "city": "Beijing"}
        
        data = {"name": "{{name}}", "city": "{{city}}"}
        result = context.interpolate_dict(data)
        
        assert result["name"] == "Alice"
        assert isinstance(result["name"], str)
        assert result["city"] == "Beijing"
    
    def test_template_string_returns_string(self):
        """Test that template strings return strings"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {"count": 15, "name": "Alice", "price": 99.99}
        
        data = {
            "message1": "Total: {{count}}",
            "message2": "Hello, {{name}}!",
            "message3": "Price is {{price}} yuan"
        }
        result = context.interpolate_dict(data)
        
        assert result["message1"] == "Total: 15"
        assert isinstance(result["message1"], str)
        assert result["message2"] == "Hello, Alice!"
        assert isinstance(result["message2"], str)
        assert result["message3"] == "Price is 99.99 yuan"
        assert isinstance(result["message3"], str)
    
    def test_nested_attribute_access(self):
        """Test type preservation with nested attribute access"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {
            "user": {
                "name": "Alice",
                "age": 30,
                "active": True,
                "salary": 15000.50
            }
        }
        
        data = {
            "name": "{{user.name}}",
            "age": "{{user.age}}",
            "active": "{{user.active}}",
            "salary": "{{user.salary}}"
        }
        result = context.interpolate_dict(data)
        
        assert result["name"] == "Alice"
        assert isinstance(result["name"], str)
        assert result["age"] == 30
        assert isinstance(result["age"], int)
        assert result["active"] is True
        assert isinstance(result["active"], bool)
        assert result["salary"] == 15000.50
        assert isinstance(result["salary"], float)
    
    def test_array_type_preservation(self):
        """Test type preservation in arrays"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {
            "count": 15,
            "price": 99.99,
            "active": True,
            "name": "Alice"
        }
        
        data = {
            "items": [
                "{{count}}",
                "{{price}}",
                "{{active}}",
                "{{name}}",
                "Prefix: {{count}}"  # Template string
            ]
        }
        result = context.interpolate_dict(data)
        
        assert result["items"][0] == 15
        assert isinstance(result["items"][0], int)
        assert result["items"][1] == 99.99
        assert isinstance(result["items"][1], float)
        assert result["items"][2] is True
        assert isinstance(result["items"][2], bool)
        assert result["items"][3] == "Alice"
        assert result["items"][4] == "Prefix: 15"
        assert isinstance(result["items"][4], str)
    
    def test_nested_dict_type_preservation(self):
        """Test type preservation in nested dictionaries"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {
            "min_salary": 15000,
            "department": "技术部",
            "active": True
        }
        
        data = {
            "query": {
                "filters": {
                    "min_salary": "{{min_salary}}",
                    "department": "{{department}}",
                    "active": "{{active}}"
                }
            }
        }
        result = context.interpolate_dict(data)
        
        assert result["query"]["filters"]["min_salary"] == 15000
        assert isinstance(result["query"]["filters"]["min_salary"], int)
        assert result["query"]["filters"]["department"] == "技术部"
        assert result["query"]["filters"]["active"] is True
    
    def test_filter_returns_string(self):
        """Test that filters force string return"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {"items": [1, 2, 3, 4, 5]}
        
        data = {"count": "{{items | length}}"}
        result = context.interpolate_dict(data)
        
        # With filter, should return string
        assert result["count"] == "5"
        assert isinstance(result["count"], str)
    
    def test_none_value_handling(self):
        """Test handling of None values"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {"value": None}
        
        data = {"field": "{{value}}"}
        result = context.interpolate_dict(data)
        
        # None should be preserved
        assert result["field"] is None
    
    def test_complex_objects_preserved(self):
        """Test that complex objects (lists, dicts) are preserved"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {
            "items": [1, 2, 3, 4, 5],
            "config": {"host": "localhost", "port": 8080}
        }
        
        data = {
            "items": "{{items}}",
            "config": "{{config}}"
        }
        result = context.interpolate_dict(data)
        
        assert result["items"] == [1, 2, 3, 4, 5]
        assert isinstance(result["items"], list)
        assert result["config"] == {"host": "localhost", "port": 8080}
        assert isinstance(result["config"], dict)
    
    def test_backward_compatibility(self):
        """Test that existing behavior is preserved"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {
            "name": "Alice",
            "age": 30,
            "items": [1, 2, 3]
        }
        
        # Old style: template strings should work as before
        data = {
            "greeting": "Hello {{name}}, you are {{age}} years old",
            "summary": "You have {{items | length}} items"
        }
        result = context.interpolate_dict(data)
        
        assert result["greeting"] == "Hello Alice, you are 30 years old"
        assert isinstance(result["greeting"], str)
        assert result["summary"] == "You have 3 items"
        assert isinstance(result["summary"], str)
    
    def test_whitespace_handling(self):
        """Test that whitespace around variables is handled correctly"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {"count": 15}
        
        data = {
            "field1": "{{ count }}",  # Spaces inside
            "field2": "  {{count}}  ",  # Spaces outside
            "field3": " {{ count }} "  # Spaces both
        }
        result = context.interpolate_dict(data)
        
        # All should preserve type (pure variable)
        assert result["field1"] == 15
        assert result["field2"] == 15
        assert result["field3"] == 15
    
    def test_api_body_real_scenario(self):
        """Test real API body scenario"""
        metadata = {}
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        context.variables = {
            "department_name": "技术部",
            "min_salary_value": 15000,
            "is_active": True,
            "page_size": 20
        }
        
        # Simulate API body
        body = {
            "department": "{{department_name}}",
            "min_salary": "{{min_salary_value}}",
            "active": "{{is_active}}",
            "page_size": "{{page_size}}",
            "message": "查询{{department_name}}员工"
        }
        
        result = context.interpolate_dict(body)
        
        # Pure variables preserve type
        assert result["department"] == "技术部"
        assert isinstance(result["department"], str)
        assert result["min_salary"] == 15000
        assert isinstance(result["min_salary"], int)
        assert result["active"] is True
        assert isinstance(result["active"], bool)
        assert result["page_size"] == 20
        assert isinstance(result["page_size"], int)
        
        # Template string returns string
        assert result["message"] == "查询技术部员工"
        assert isinstance(result["message"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

