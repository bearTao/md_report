"""Tests for constant variable type"""
import pytest
from app.core.models import VariableMetadata, VariableSource
from app.executors.constant import ConstantExecutor
from app.services.context import ExecutionContext


class TestConstantExecutor:
    """Test constant variable executor"""
    
    @pytest.mark.asyncio
    async def test_number_constant(self):
        """Test number constant variable"""
        metadata = VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="Test number constant",
            value=15000
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("min_salary", metadata, context)
        
        result = await executor.execute()
        
        assert result.value == 15000
        assert isinstance(result.value, int)
    
    @pytest.mark.asyncio
    async def test_string_constant(self):
        """Test string constant variable"""
        metadata = VariableMetadata(
            type="string",
            source=VariableSource.CONSTANT,
            description="Test string constant",
            value="XX科技有限公司"
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("company_name", metadata, context)
        
        result = await executor.execute()
        
        assert result.value == "XX科技有限公司"
        assert isinstance(result.value, str)
    
    @pytest.mark.asyncio
    async def test_boolean_constant(self):
        """Test boolean constant variable"""
        metadata = VariableMetadata(
            type="boolean",
            source=VariableSource.CONSTANT,
            description="Test boolean constant",
            value=True
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("is_active", metadata, context)
        
        result = await executor.execute()
        
        assert result.value is True
        assert isinstance(result.value, bool)
    
    @pytest.mark.asyncio
    async def test_float_constant(self):
        """Test float constant variable"""
        metadata = VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="Test float constant",
            value=0.13
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("vat_rate", metadata, context)
        
        result = await executor.execute()
        
        assert result.value == 0.13
        assert isinstance(result.value, float)
    
    @pytest.mark.asyncio
    async def test_array_constant(self):
        """Test array constant variable"""
        metadata = VariableMetadata(
            type="array",
            source=VariableSource.CONSTANT,
            description="Test array constant",
            value=["北京", "上海", "深圳", "杭州"]
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("major_cities", metadata, context)
        
        result = await executor.execute()
        
        assert result.value == ["北京", "上海", "深圳", "杭州"]
        assert isinstance(result.value, list)
    
    @pytest.mark.asyncio
    async def test_object_constant(self):
        """Test object constant variable"""
        metadata = VariableMetadata(
            type="object",
            source=VariableSource.CONSTANT,
            description="Test object constant",
            value={
                "host": "10.10.20.10",
                "port": 5000,
                "protocol": "http"
            }
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("api_config", metadata, context)
        
        result = await executor.execute()
        
        assert result.value["host"] == "10.10.20.10"
        assert result.value["port"] == 5000
        assert isinstance(result.value, dict)
    
    @pytest.mark.asyncio
    async def test_missing_value_field(self):
        """Test error when value field is missing"""
        metadata = VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="Test missing value",
            value=None  # Missing value
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("bad_constant", metadata, context)
        
        result = await executor.execute()
        
        # Should fail and use default if available
        assert result.status.value == "failed"
        assert "must have a 'value' field" in result.error
    
    @pytest.mark.asyncio
    async def test_constant_with_default(self):
        """Test constant with default value"""
        metadata = VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="Test constant with default",
            value=None,  # Missing value
            default=10000  # But has default
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("salary", metadata, context)
        
        result = await executor.execute()
        
        # Should use default value
        assert result.value == 10000
    
    @pytest.mark.asyncio
    async def test_constant_in_context(self):
        """Test that constant is stored in context"""
        metadata = VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="Test",
            value=15000
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("min_salary", metadata, context)
        
        await executor.execute()
        
        # Should be in context
        assert context.has_variable("min_salary")
        assert context.get_variable("min_salary") == 15000
    
    @pytest.mark.asyncio
    async def test_zero_value_allowed(self):
        """Test that zero value is valid (not treated as None)"""
        metadata = VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="Test zero value",
            value=0
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("initial_count", metadata, context)
        
        result = await executor.execute()
        
        assert result.value == 0
        assert result.status.value == "success"
    
    @pytest.mark.asyncio
    async def test_false_value_allowed(self):
        """Test that False value is valid (not treated as None)"""
        metadata = VariableMetadata(
            type="boolean",
            source=VariableSource.CONSTANT,
            description="Test false value",
            value=False
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("is_disabled", metadata, context)
        
        result = await executor.execute()
        
        assert result.value is False
        assert result.status.value == "success"
    
    @pytest.mark.asyncio
    async def test_empty_string_allowed(self):
        """Test that empty string is valid (not treated as None)"""
        metadata = VariableMetadata(
            type="string",
            source=VariableSource.CONSTANT,
            description="Test empty string",
            value=""
        )
        
        context = ExecutionContext("test_task", "test_template", {}, {})
        executor = ConstantExecutor("empty_field", metadata, context)
        
        result = await executor.execute()
        
        assert result.value == ""
        assert result.status.value == "success"


class TestConstantInDependencies:
    """Test using constants in other variables"""
    
    @pytest.mark.asyncio
    async def test_constant_referenced_by_other_variable(self):
        """Test constant used as dependency"""
        # First execute constant
        const_metadata = VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="Minimum salary",
            value=15000
        )
        
        all_metadata = {
            "min_salary": const_metadata
        }
        
        context = ExecutionContext("test_task", "test_template", {}, all_metadata)
        const_executor = ConstantExecutor("min_salary", const_metadata, context)
        
        await const_executor.execute()
        
        # Verify it's in context and can be used by other variables
        assert context.has_variable("min_salary")
        assert context.get_variable("min_salary") == 15000
        
        # Simulate API body interpolation
        body = {
            "min_salary": "{{min_salary}}",
            "message": "Minimum salary is {{min_salary}}"
        }
        
        result = context.interpolate_dict(body)
        
        # Should preserve type for pure variable
        assert result["min_salary"] == 15000
        assert isinstance(result["min_salary"], int)
        # Template string returns string
        assert result["message"] == "Minimum salary is 15000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

