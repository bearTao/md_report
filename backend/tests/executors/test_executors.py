"""Tests for variable executors"""
import pytest
from decimal import Decimal
from sqlalchemy import text
from app.services.context import ExecutionContext
from app.executors.user_input import UserInputExecutor
from app.executors.system import SystemExecutor
from app.executors.sql import SqlExecutor
from app.core.models import (
    VariableMetadata, VariableSource, VariableStatus, 
    SystemConfig, SqlConfig, SqlResultMode
)
from app.connectors.database import db_connector


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


@pytest.mark.asyncio
async def test_sql_executor_first_row_mode(db_session):
    """Test SqlExecutor with first_row mode"""
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_users"))
    db_session.execute(text("CREATE TABLE test_users (id INT, name VARCHAR(50), email VARCHAR(50))"))
    db_session.execute(text("INSERT INTO test_users VALUES (1, 'Alice', 'alice@test.com')"))
    db_session.execute(text("INSERT INTO test_users VALUES (2, 'Bob', 'bob@test.com')"))
    db_session.commit()
    
    # Register connection - use the same engine as db_session
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = VariableMetadata(
        type="object",
        source=VariableSource.SQL,
        description="User profile",
        sql_config=SqlConfig(
            connection="test_db",
            query="SELECT id, name, email FROM test_users WHERE id = 1",
            result_mode=SqlResultMode.FIRST_ROW
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"user": metadata})
    executor = SqlExecutor("user", metadata, context)
    result = await executor.execute()
    
    if result.status != VariableStatus.SUCCESS:
        print(f"Execution failed: {result.error}")
    
    assert result.status == VariableStatus.SUCCESS, f"Expected SUCCESS, got {result.status}. Error: {result.error}"
    assert isinstance(result.value, dict)
    assert result.value["name"] == "Alice"
    assert result.value["email"] == "alice@test.com"


@pytest.mark.asyncio
async def test_sql_executor_all_rows_mode(db_session):
    """Test SqlExecutor with all_rows mode"""
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_products"))
    db_session.execute(text("CREATE TABLE test_products (id INT, name VARCHAR(50), price DECIMAL(10,2))"))
    db_session.execute(text("INSERT INTO test_products VALUES (1, 'Product A', 10.50)"))
    db_session.execute(text("INSERT INTO test_products VALUES (2, 'Product B', 20.99)"))
    db_session.execute(text("INSERT INTO test_products VALUES (3, 'Product C', 15.00)"))
    db_session.commit()
    
    # Register connection - use the same engine as db_session
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = VariableMetadata(
        type="array",
        source=VariableSource.SQL,
        description="Product list",
        sql_config=SqlConfig(
            connection="test_db",
            query="SELECT id, name, price FROM test_products ORDER BY id",
            result_mode=SqlResultMode.ALL_ROWS
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"products": metadata})
    executor = SqlExecutor("products", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, list)
    assert len(result.value) == 3
    assert result.value[0]["name"] == "Product A"
    assert result.value[1]["name"] == "Product B"
    assert result.value[2]["name"] == "Product C"


@pytest.mark.asyncio
async def test_sql_executor_first_value_mode(db_session):
    """Test SqlExecutor with first_value mode"""
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_sales"))
    db_session.execute(text("CREATE TABLE test_sales (id INT, amount DECIMAL(10,2))"))
    db_session.execute(text("INSERT INTO test_sales VALUES (1, 100.50)"))
    db_session.execute(text("INSERT INTO test_sales VALUES (2, 200.75)"))
    db_session.execute(text("INSERT INTO test_sales VALUES (3, 150.25)"))
    db_session.commit()
    
    # Register connection - use the same engine as db_session
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = VariableMetadata(
        type="number",
        source=VariableSource.SQL,
        description="Total sales",
        sql_config=SqlConfig(
            connection="test_db",
            query="SELECT SUM(amount) as total FROM test_sales",
            result_mode=SqlResultMode.FIRST_VALUE
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"total_sales": metadata})
    executor = SqlExecutor("total_sales", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, (int, float, Decimal))
    assert float(result.value) == 451.50


@pytest.mark.asyncio
async def test_sql_executor_first_column_mode(db_session):
    """Test SqlExecutor with first_column mode"""
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_active_users"))
    db_session.execute(text("CREATE TABLE test_active_users (id INT, name VARCHAR(50), status VARCHAR(20))"))
    db_session.execute(text("INSERT INTO test_active_users VALUES (1, 'User1', 'active')"))
    db_session.execute(text("INSERT INTO test_active_users VALUES (2, 'User2', 'active')"))
    db_session.execute(text("INSERT INTO test_active_users VALUES (3, 'User3', 'inactive')"))
    db_session.execute(text("INSERT INTO test_active_users VALUES (4, 'User4', 'active')"))
    db_session.commit()
    
    # Register connection - use the same engine as db_session
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = VariableMetadata(
        type="array",
        source=VariableSource.SQL,
        description="Active user IDs",
        sql_config=SqlConfig(
            connection="test_db",
            query="SELECT id FROM test_active_users WHERE status = 'active' ORDER BY id",
            result_mode=SqlResultMode.FIRST_COLUMN
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"user_ids": metadata})
    executor = SqlExecutor("user_ids", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, list)
    assert result.value == [1, 2, 4]


@pytest.mark.asyncio
async def test_sql_executor_auto_mode_object(db_session):
    """Test SqlExecutor with auto mode for object type"""
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_config"))
    db_session.execute(text("CREATE TABLE test_config (id INT, key_name VARCHAR(50), value VARCHAR(50))"))
    db_session.execute(text("INSERT INTO test_config VALUES (1, 'app_name', 'MyApp')"))
    db_session.commit()
    
    # Register connection - use the same engine as db_session
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata with auto mode (default)
    metadata = VariableMetadata(
        type="object",
        source=VariableSource.SQL,
        description="App config",
        sql_config=SqlConfig(
            connection="test_db",
            query="SELECT key_name, value FROM test_config WHERE id = 1",
            result_mode=SqlResultMode.AUTO  # Auto mode
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"config": metadata})
    executor = SqlExecutor("config", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    # Single row with object type should return dict
    assert isinstance(result.value, dict)
    assert result.value["key_name"] == "app_name"


@pytest.mark.asyncio
async def test_sql_executor_auto_mode_array(db_session):
    """Test SqlExecutor with auto mode for array type"""
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_items"))
    db_session.execute(text("CREATE TABLE test_items (id INT, name VARCHAR(50))"))
    db_session.execute(text("INSERT INTO test_items VALUES (1, 'Item1')"))
    db_session.execute(text("INSERT INTO test_items VALUES (2, 'Item2')"))
    db_session.commit()
    
    # Register connection - use the same engine as db_session
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata with auto mode (default)
    metadata = VariableMetadata(
        type="array",
        source=VariableSource.SQL,
        description="Item list",
        sql_config=SqlConfig(
            connection="test_db",
            query="SELECT id, name FROM test_items ORDER BY id",
            result_mode=SqlResultMode.AUTO  # Auto mode
        )
    )
    
    context = ExecutionContext("task_1", "tpl_1", {}, {"items": metadata})
    executor = SqlExecutor("items", metadata, context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    # Array type should return all rows
    assert isinstance(result.value, list)
    assert len(result.value) == 2

