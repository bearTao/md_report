"""Integration tests for CONSTANT variable type with type preservation"""
import pytest
from app.core.models import VariableMetadata, VariableSource
from app.executors.constant import ConstantExecutor
from app.services.context import ExecutionContext


class TestConstantWithTypePreservation:
    """Test that constants work correctly with type preservation"""
    
    @pytest.mark.asyncio
    async def test_constant_used_in_api_body(self):
        """Test constant variable used in API body with type preservation"""
        # Define constant metadata
        constant_metadata = {
            "min_salary_standard": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Minimum salary standard",
                value=15000
            ),
            "max_salary_standard": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Maximum salary standard",
                value=50000
            ),
            "department_name": VariableMetadata(
                type="string",
                source=VariableSource.CONSTANT,
                description="Department name",
                value="技术部"
            ),
            "is_active": VariableMetadata(
                type="boolean",
                source=VariableSource.CONSTANT,
                description="Active status",
                value=True
            ),
            "vat_rate": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="VAT rate",
                value=0.13
            )
        }
        
        # Create context
        context = ExecutionContext("test_task", "test_template", {}, constant_metadata)
        
        # Execute all constants
        for var_name, metadata in constant_metadata.items():
            executor = ConstantExecutor(var_name, metadata, context)
            await executor.execute()
        
        # Simulate API body that uses constants
        api_body = {
            "department": "{{department_name}}",           # String constant
            "min_salary": "{{min_salary_standard}}",       # Number constant
            "max_salary": "{{max_salary_standard}}",       # Number constant
            "active": "{{is_active}}",                     # Boolean constant
            "vat_rate": "{{vat_rate}}",                    # Float constant
            "message": "查询{{department_name}}的员工"     # Template string
        }
        
        # Interpolate with type preservation
        result = context.interpolate_dict(api_body)
        
        # Verify types are preserved for pure variable references
        assert result["department"] == "技术部"
        assert isinstance(result["department"], str)
        
        assert result["min_salary"] == 15000
        assert isinstance(result["min_salary"], int)
        
        assert result["max_salary"] == 50000
        assert isinstance(result["max_salary"], int)
        
        assert result["active"] is True
        assert isinstance(result["active"], bool)
        
        assert result["vat_rate"] == 0.13
        assert isinstance(result["vat_rate"], float)
        
        # Template string returns string
        assert result["message"] == "查询技术部的员工"
        assert isinstance(result["message"], str)
    
    @pytest.mark.asyncio
    async def test_constant_array_used_in_api(self):
        """Test constant array used in API with type preservation"""
        constant_metadata = {
            "major_cities": VariableMetadata(
                type="array",
                source=VariableSource.CONSTANT,
                description="Major cities",
                value=["北京", "上海", "深圳", "杭州"]
            ),
            "page_size": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Page size",
                value=20
            )
        }
        
        context = ExecutionContext("test_task", "test_template", {}, constant_metadata)
        
        # Execute constants
        for var_name, metadata in constant_metadata.items():
            executor = ConstantExecutor(var_name, metadata, context)
            await executor.execute()
        
        # API body with array and nested structure
        api_body = {
            "filters": {
                "cities": "{{major_cities}}",      # Array constant
                "page_size": "{{page_size}}"       # Number constant
            }
        }
        
        result = context.interpolate_dict(api_body)
        
        # Verify array is preserved
        assert result["filters"]["cities"] == ["北京", "上海", "深圳", "杭州"]
        assert isinstance(result["filters"]["cities"], list)
        
        # Verify number is preserved
        assert result["filters"]["page_size"] == 20
        assert isinstance(result["filters"]["page_size"], int)
    
    @pytest.mark.asyncio
    async def test_constant_object_used_in_api(self):
        """Test constant object used in API with type preservation"""
        constant_metadata = {
            "default_pagination": VariableMetadata(
                type="object",
                source=VariableSource.CONSTANT,
                description="Default pagination",
                value={
                    "page": 1,
                    "page_size": 20,
                    "max_page_size": 100
                }
            )
        }
        
        context = ExecutionContext("test_task", "test_template", {}, constant_metadata)
        
        # Execute constant
        executor = ConstantExecutor("default_pagination", constant_metadata["default_pagination"], context)
        await executor.execute()
        
        # API body with object constant
        api_body = {
            "pagination": "{{default_pagination}}"
        }
        
        result = context.interpolate_dict(api_body)
        
        # Verify object is preserved
        assert result["pagination"] == {
            "page": 1,
            "page_size": 20,
            "max_page_size": 100
        }
        assert isinstance(result["pagination"], dict)
    
    @pytest.mark.asyncio
    async def test_constant_nested_access_with_type_preservation(self):
        """Test accessing nested properties of constant objects"""
        constant_metadata = {
            "api_config": VariableMetadata(
                type="object",
                source=VariableSource.CONSTANT,
                description="API configuration",
                value={
                    "host": "10.10.20.10",
                    "port": 5000,
                    "timeout": 30,
                    "secure": False
                }
            )
        }
        
        context = ExecutionContext("test_task", "test_template", {}, constant_metadata)
        
        # Execute constant
        executor = ConstantExecutor("api_config", constant_metadata["api_config"], context)
        await executor.execute()
        
        # Access nested properties
        api_body = {
            "host": "{{api_config.host}}",          # String from object
            "port": "{{api_config.port}}",          # Number from object
            "timeout": "{{api_config.timeout}}",    # Number from object
            "secure": "{{api_config.secure}}",      # Boolean from object
            "url": "http://{{api_config.host}}:{{api_config.port}}"  # Template string
        }
        
        result = context.interpolate_dict(api_body)
        
        # Verify nested access with type preservation
        assert result["host"] == "10.10.20.10"
        assert isinstance(result["host"], str)
        
        assert result["port"] == 5000
        assert isinstance(result["port"], int)
        
        assert result["timeout"] == 30
        assert isinstance(result["timeout"], int)
        
        assert result["secure"] is False
        assert isinstance(result["secure"], bool)
        
        # Template string returns string
        assert result["url"] == "http://10.10.20.10:5000"
        assert isinstance(result["url"], str)
    
    @pytest.mark.asyncio
    async def test_multiple_constants_in_complex_body(self):
        """Test real-world scenario with multiple constants"""
        constant_metadata = {
            "min_salary": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Minimum salary",
                value=15000
            ),
            "max_salary": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Maximum salary",
                value=50000
            ),
            "company_name": VariableMetadata(
                type="string",
                source=VariableSource.CONSTANT,
                description="Company name",
                value="XX科技有限公司"
            ),
            "enable_cache": VariableMetadata(
                type="boolean",
                source=VariableSource.CONSTANT,
                description="Enable cache",
                value=True
            ),
            "major_cities": VariableMetadata(
                type="array",
                source=VariableSource.CONSTANT,
                description="Major cities",
                value=["北京", "上海", "深圳"]
            )
        }
        
        context = ExecutionContext("test_task", "test_template", {}, constant_metadata)
        
        # Execute all constants
        for var_name, metadata in constant_metadata.items():
            executor = ConstantExecutor(var_name, metadata, context)
            await executor.execute()
        
        # Complex API body
        api_body = {
            "query": {
                "company": "{{company_name}}",
                "salary_range": {
                    "min": "{{min_salary}}",
                    "max": "{{max_salary}}"
                },
                "cities": "{{major_cities}}",
                "options": {
                    "cache": "{{enable_cache}}"
                }
            },
            "metadata": {
                "description": "查询{{company_name}}的员工信息"
            }
        }
        
        result = context.interpolate_dict(api_body)
        
        # Verify complex nested structure with type preservation
        assert result["query"]["company"] == "XX科技有限公司"
        assert result["query"]["salary_range"]["min"] == 15000
        assert isinstance(result["query"]["salary_range"]["min"], int)
        assert result["query"]["salary_range"]["max"] == 50000
        assert isinstance(result["query"]["salary_range"]["max"], int)
        assert result["query"]["cities"] == ["北京", "上海", "深圳"]
        assert isinstance(result["query"]["cities"], list)
        assert result["query"]["options"]["cache"] is True
        assert isinstance(result["query"]["options"]["cache"], bool)
        assert result["metadata"]["description"] == "查询XX科技有限公司的员工信息"
        assert isinstance(result["metadata"]["description"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

