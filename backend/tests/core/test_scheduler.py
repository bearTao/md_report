"""Tests for execution scheduler"""
import pytest
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.core.models import VariableMetadata, VariableSource, SystemConfig
from app.core.exceptions import DependencyError


def test_build_dag_simple():
    """Test building simple DAG"""
    metadata = {
        "var1": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Base",
            required=True
        ),
        "var2": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="Dependent",
            required=True,
            dependencies=["var1"]
        )
    }
    
    scheduler = ExecutionScheduler()
    dag = scheduler.build_dag(metadata)
    
    assert dag.number_of_nodes() == 2
    assert dag.has_edge("var1", "var2")


def test_build_dag_circular_dependency():
    """Test detecting circular dependencies"""
    metadata = {
        "var1": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Var1",
            required=True,
            dependencies=["var2"]
        ),
        "var2": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Var2",
            required=True,
            dependencies=["var1"]
        )
    }
    
    scheduler = ExecutionScheduler()
    
    with pytest.raises(DependencyError, match="Circular dependency"):
        scheduler.build_dag(metadata)


def test_get_execution_batches():
    """Test getting execution batches"""
    metadata = {
        "var1": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Base 1",
            required=True
        ),
        "var2": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="Base 2",
            required=True
        ),
        "var3": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="Dependent on 1 and 2",
            required=True,
            dependencies=["var1", "var2"]
        )
    }
    
    scheduler = ExecutionScheduler()
    dag = scheduler.build_dag(metadata)
    batches = scheduler.get_execution_batches(dag)
    
    # Should have 2 batches
    assert len(batches) == 2
    
    # First batch should have var1 and var2 (can be executed in parallel)
    assert set(batches[0]) == {"var1", "var2"}
    
    # Second batch should have var3 (depends on first batch)
    assert batches[1] == ["var3"]


@pytest.mark.asyncio
async def test_execute_all():
    """Test executing all variables"""
    metadata = {
        "user_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="User name",
            required=True
        ),
        "timestamp": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="Timestamp",
            required=True,
            system_config=SystemConfig(
                fields={
                    "ts": {
                        "generator": "datetime",
                        "format": "%Y-%m-%d"
                    }
                }
            )
        )
    }
    
    context = ExecutionContext(
        "task_1",
        "tpl_1",
        user_inputs={"user_name": "Alice"},
        metadata=metadata
    )
    
    scheduler = ExecutionScheduler()
    
    # Track progress
    progress_events = []
    
    async def progress_callback(var_name, status, result):
        progress_events.append((var_name, status))
    
    results = await scheduler.execute_all(context, progress_callback)
    
    # Should have 2 successful results
    assert len(results) == 2
    assert all(r.status.value == "success" for r in results.values())
    
    # Check context has variables
    assert context.has_variable("user_name")
    assert context.has_variable("timestamp")
    assert context.get_variable("user_name") == "Alice"
    
    # Check progress events
    assert len(progress_events) > 0

