"""Tests for variable executors"""
import pytest
from app.services.context import ExecutionContext
from app.executors.user_input import UserInputExecutor
from app.executors.system import SystemExecutor
from app.core.models import VariableMetadata, VariableSource, VariableStatus, SystemConfig


@pytest.mark.asyncio
async def test_user_input_executor():
    """Test UserInputExecutor"""
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.USER_INPUT,
        description="Test input",
        required=True
    )
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={"test_var": "test_value"},
        metadata={"test_var": metadata}
    )
    
    executor = UserInputExecutor("test_var", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert result.value == "test_value"
    assert context.get_variable("test_var") == "test_value"


@pytest.mark.asyncio
async def test_user_input_with_default():
    """Test UserInputExecutor with default value"""
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.USER_INPUT,
        description="Test input",
        required=False,
        default="default_value"
    )
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={},  # No input provided
        metadata={"test_var": metadata}
    )
    
    executor = UserInputExecutor("test_var", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert result.value == "default_value"


@pytest.mark.asyncio
async def test_system_executor_datetime():
    """Test SystemExecutor with datetime generation"""
    metadata = VariableMetadata(
        type="object",
        source=VariableSource.SYSTEM,
        description="System info",
        required=True,
        system_config=SystemConfig(
            fields={
                "timestamp": {
                    "generator": "datetime",
                    "format": "%Y-%m-%d %H:%M:%S"
                }
            }
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"sys_var": metadata})
    
    executor = SystemExecutor("sys_var", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, str)
    # Should match format YYYY-MM-DD HH:MM:SS
    assert len(result.value) == 19


@pytest.mark.asyncio
async def test_system_executor_uuid():
    """Test SystemExecutor with UUID generation"""
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.SYSTEM,
        description="UUID",
        required=True,
        system_config=SystemConfig(
            fields={
                "id": {
                    "generator": "uuid"
                }
            }
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"uuid_var": metadata})
    
    executor = SystemExecutor("uuid_var", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, str)
    # UUID should have dashes
    assert '-' in result.value


@pytest.mark.asyncio
async def test_system_executor_constant():
    """Test SystemExecutor with constant value"""
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.SYSTEM,
        description="Version",
        required=True,
        system_config=SystemConfig(
            fields={
                "version": {
                    "value": "1.0.0"
                }
            }
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"version_var": metadata})
    
    executor = SystemExecutor("version_var", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert result.value == "1.0.0"

