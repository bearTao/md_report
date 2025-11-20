"""Tests for constant auto-injection feature"""
import pytest
from app.core.models import VariableMetadata, VariableSource, VariableStatus, ApiConfig
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext


class TestConstantAutoInjection:
    """Test that CONSTANT variables are automatically pre-executed"""
    
    @pytest.mark.asyncio
    async def test_constant_executed_first_without_dependency_declaration(self):
        """Test that constants are executed before other variables without declaring dependencies"""
        
        # Define metadata with constant and API variable
        metadata = {
            "api_base_url": VariableMetadata(
                type="string",
                source=VariableSource.CONSTANT,
                description="API base URL",
                value="http://10.10.20.10:5000"
            ),
            "department_name": VariableMetadata(
                type="string",
                source=VariableSource.USER_INPUT,
                description="Department name",
                required=True
            ),
            "api_result": VariableMetadata(
                type="object",
                source=VariableSource.API,
                description="API call using constant",
                required=False,
                # NOTE: No dependencies declared!
                api_config=ApiConfig(
                    endpoint="{{api_base_url}}/api/test",
                    method="GET"
                )
            )
        }
        
        # Create context
        user_inputs = {"department_name": "技术部"}
        context = ExecutionContext("test_task", "test_template", user_inputs, metadata)
        
        # Create scheduler
        scheduler = ExecutionScheduler()
        
        # Track execution order
        execution_order = []
        
        async def track_callback(var_name, status, result):
            if status == VariableStatus.RUNNING:
                execution_order.append(var_name)
        
        # Execute (will fail on API call since server not running, but that's OK)
        try:
            await scheduler.execute_all(context, progress_callback=track_callback)
        except Exception:
            pass  # Expected to fail on actual API call
        
        # Verify constant was executed first
        assert "api_base_url" in execution_order
        assert execution_order.index("api_base_url") < execution_order.index("api_result")
        
        # Verify constant value is in context
        assert context.has_variable("api_base_url")
        assert context.get_variable("api_base_url") == "http://10.10.20.10:5000"
    
    @pytest.mark.asyncio
    async def test_multiple_constants_executed_in_parallel(self):
        """Test that multiple constants are all pre-executed"""
        
        metadata = {
            "const1": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="First constant",
                value=100
            ),
            "const2": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Second constant",
                value=200
            ),
            "const3": VariableMetadata(
                type="string",
                source=VariableSource.CONSTANT,
                description="Third constant",
                value="test"
            ),
            "user_var": VariableMetadata(
                type="string",
                source=VariableSource.USER_INPUT,
                description="User input",
                required=True
            )
        }
        
        user_inputs = {"user_var": "test_value"}
        context = ExecutionContext("test_task", "test_template", user_inputs, metadata)
        
        scheduler = ExecutionScheduler()
        
        results = await scheduler.execute_all(context)
        
        # All constants should be successful
        assert results["const1"].status == VariableStatus.SUCCESS
        assert results["const1"].value == 100
        assert results["const2"].status == VariableStatus.SUCCESS
        assert results["const2"].value == 200
        assert results["const3"].status == VariableStatus.SUCCESS
        assert results["const3"].value == "test"
        
        # All should be in context
        assert context.get_variable("const1") == 100
        assert context.get_variable("const2") == 200
        assert context.get_variable("const3") == "test"
    
    @pytest.mark.asyncio
    async def test_constant_failure_does_not_stop_execution(self):
        """Test that failed constant doesn't stop other variables"""
        
        metadata = {
            "bad_constant": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Bad constant (no value)",
                # value is None - will fail
            ),
            "good_constant": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Good constant",
                value=100
            ),
            "user_var": VariableMetadata(
                type="string",
                source=VariableSource.USER_INPUT,
                description="User input",
                required=True
            )
        }
        
        user_inputs = {"user_var": "test"}
        context = ExecutionContext("test_task", "test_template", user_inputs, metadata)
        
        scheduler = ExecutionScheduler()
        results = await scheduler.execute_all(context)
        
        # Bad constant should fail
        assert results["bad_constant"].status == VariableStatus.FAILED
        
        # Good constant should succeed
        assert results["good_constant"].status == VariableStatus.SUCCESS
        assert results["good_constant"].value == 100
        
        # User var should still execute
        assert results["user_var"].status == VariableStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_explicit_dependencies(self):
        """Test that explicitly declared constant dependencies still work"""
        
        metadata = {
            "api_base_url": VariableMetadata(
                type="string",
                source=VariableSource.CONSTANT,
                description="API base URL",
                value="http://localhost:5000"
            ),
            "api_result": VariableMetadata(
                type="object",
                source=VariableSource.API,
                description="API call",
                required=False,
                dependencies=["api_base_url"],  # Explicitly declared
                api_config=ApiConfig(
                    endpoint="{{api_base_url}}/api/test",
                    method="GET"
                )
            )
        }
        
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        scheduler = ExecutionScheduler()
        
        # Should not raise error even with explicit dependency
        try:
            await scheduler.execute_all(context)
        except Exception:
            pass  # Expected to fail on actual API call
        
        # Constant should still be executed and available
        assert context.has_variable("api_base_url")
        assert context.get_variable("api_base_url") == "http://localhost:5000"
    
    @pytest.mark.asyncio
    async def test_only_constants_in_metadata(self):
        """Test execution when metadata contains only constants"""
        
        metadata = {
            "const1": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Constant 1",
                value=42
            ),
            "const2": VariableMetadata(
                type="string",
                source=VariableSource.CONSTANT,
                description="Constant 2",
                value="hello"
            )
        }
        
        context = ExecutionContext("test_task", "test_template", {}, metadata)
        scheduler = ExecutionScheduler()
        
        results = await scheduler.execute_all(context)
        
        # Both constants should execute successfully
        assert len(results) == 2
        assert results["const1"].status == VariableStatus.SUCCESS
        assert results["const1"].value == 42
        assert results["const2"].status == VariableStatus.SUCCESS
        assert results["const2"].value == "hello"
    
    @pytest.mark.asyncio
    async def test_constants_available_in_dependent_variables(self):
        """Test that constants are available for interpolation in dependent variables"""
        
        metadata = {
            "min_salary": VariableMetadata(
                type="number",
                source=VariableSource.CONSTANT,
                description="Minimum salary",
                value=15000
            ),
            "department": VariableMetadata(
                type="string",
                source=VariableSource.USER_INPUT,
                description="Department",
                required=True
            ),
            # API variable that uses both constant and user input
            "user_query": VariableMetadata(
                type="object",
                source=VariableSource.API,
                description="User query",
                required=False,
                dependencies=["department"],  # Only need to declare non-constant dependency
                api_config=ApiConfig(
                    endpoint="http://localhost:5000/api/users",
                    method="POST",
                    body={
                        "min_salary": "{{min_salary}}",  # Constant - auto-available
                        "department": "{{department}}"   # User input - declared
                    }
                )
            )
        }
        
        user_inputs = {"department": "技术部"}
        context = ExecutionContext("test_task", "test_template", user_inputs, metadata)
        scheduler = ExecutionScheduler()
        
        try:
            await scheduler.execute_all(context)
        except Exception:
            pass  # Expected to fail on actual API call
        
        # Verify constant is in context and available
        assert context.has_variable("min_salary")
        assert context.get_variable("min_salary") == 15000
        
        # Verify interpolation would work (constant value should be preserved as number)
        body = {"min_salary": "{{min_salary}}", "department": "{{department}}"}
        interpolated = context.interpolate_dict(body)
        assert interpolated["min_salary"] == 15000  # Number type preserved
        assert interpolated["department"] == "技术部"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

