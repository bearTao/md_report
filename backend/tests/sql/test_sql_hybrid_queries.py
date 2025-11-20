"""
Tests for SQL hybrid queries (string interpolation + parameterized queries)
Tests the fix for SQL injection risk and proper quote handling
"""
import pytest
from decimal import Decimal
from sqlalchemy import text
from app.services.context import ExecutionContext
from app.executors.sql import SqlExecutor
from app.core.models import (
    VariableMetadata, VariableSource, VariableStatus, 
    SqlConfig, SqlResultMode
)
from app.connectors.database import db_connector


@pytest.mark.asyncio
async def test_parameterized_query_with_string(db_session):
    """
    Test: Parameterized query with string value
    Scenario: WHERE wgid = :wgid should properly quote string values
    Expected: WHERE wgid = 'ZQGY0174' (with quotes)
    """
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_sites"))
    db_session.execute(text("""
        CREATE TABLE test_sites (
            wgid VARCHAR(50),
            site_name VARCHAR(100),
            latitude DECIMAL(10,6),
            longitude DECIMAL(10,6)
        )
    """))
    db_session.execute(text("""
        INSERT INTO test_sites VALUES 
        ('ZQGY0174', 'Site A', 31.123456, 121.234567),
        ('ZQGY0175', 'Site B', 31.234567, 121.345678),
        ('ZQGY0176', 'Site C', 31.345678, 121.456789)
    """))
    db_session.commit()
    
    # Register connection
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create context with wgid variable
    metadata = {
        "wgid": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="工作组ID"
        ),
        "sites": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="站点列表",
            dependencies=["wgid"],
            sql_config=SqlConfig(
                connection="test_db",
                query="SELECT wgid, site_name, latitude, longitude FROM test_sites WHERE wgid = :wgid",
                parameters=["wgid"],
                result_mode=SqlResultMode.ALL_ROWS
            )
        )
    }
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={"wgid": "ZQGY0174"},
        metadata=metadata
    )
    
    # Set wgid variable first
    context.set_variable("wgid", "ZQGY0174")
    
    # Execute SQL query
    executor = SqlExecutor("sites", metadata["sites"], context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS, f"Query failed: {result.error}"
    assert isinstance(result.value, list)
    assert len(result.value) == 1
    assert result.value[0]["wgid"] == "ZQGY0174"
    assert result.value[0]["site_name"] == "Site A"


@pytest.mark.asyncio
async def test_parameterized_query_with_number(db_session):
    """
    Test: Parameterized query with numeric value
    Scenario: WHERE amount > :min_amount should handle numbers without quotes
    Expected: WHERE amount > 50000 (no quotes)
    """
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_orders"))
    db_session.execute(text("""
        CREATE TABLE test_orders (
            order_id VARCHAR(50),
            amount DECIMAL(10,2),
            status VARCHAR(20)
        )
    """))
    db_session.execute(text("""
        INSERT INTO test_orders VALUES 
        ('ORD001', 25000.00, 'completed'),
        ('ORD002', 75000.50, 'completed'),
        ('ORD003', 120000.00, 'completed'),
        ('ORD004', 30000.00, 'pending')
    """))
    db_session.commit()
    
    # Register connection
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = {
        "min_amount": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="最小金额"
        ),
        "high_value_orders": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="高价值订单",
            dependencies=["min_amount"],
            sql_config=SqlConfig(
                connection="test_db",
                query="SELECT order_id, amount FROM test_orders WHERE amount > :min_amount AND status = :status ORDER BY amount DESC",
                parameters=["min_amount", "status"],
                result_mode=SqlResultMode.ALL_ROWS
            )
        )
    }
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={"min_amount": 50000},
        metadata=metadata
    )
    
    # Set variables
    context.set_variable("min_amount", 50000)
    context.set_variable("status", "completed")
    
    # Execute SQL query
    executor = SqlExecutor("high_value_orders", metadata["high_value_orders"], context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, list)
    assert len(result.value) == 2  # Only ORD002 and ORD003
    assert float(result.value[0]["amount"]) == 120000.00
    assert float(result.value[1]["amount"]) == 75000.50


@pytest.mark.asyncio
async def test_hybrid_dynamic_table_with_params(db_session):
    """
    Test: Hybrid scenario - Dynamic table name + parameterized WHERE
    Scenario: SELECT * FROM {{table_name}} WHERE id = :id
    Expected: Table name via interpolation, id via parameterization
    """
    # Setup test data for multiple tables
    db_session.execute(text("DROP TABLE IF EXISTS users_2024"))
    db_session.execute(text("DROP TABLE IF EXISTS users_2025"))
    
    db_session.execute(text("CREATE TABLE users_2024 (id INT, name VARCHAR(50), year INT)"))
    db_session.execute(text("INSERT INTO users_2024 VALUES (1, 'Alice 2024', 2024)"))
    
    db_session.execute(text("CREATE TABLE users_2025 (id INT, name VARCHAR(50), year INT)"))
    db_session.execute(text("INSERT INTO users_2025 VALUES (1, 'Bob 2025', 2025)"))
    
    db_session.commit()
    
    # Register connection
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata with dynamic table name
    metadata = {
        "year": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="年份"
        ),
        "user_id": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="用户ID"
        ),
        "table_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="表名"
        ),
        "user_data": VariableMetadata(
            type="object",
            source=VariableSource.SQL,
            description="用户数据",
            dependencies=["table_name", "user_id"],
            sql_config=SqlConfig(
                connection="test_db",
                query="SELECT id, name, year FROM {{table_name}} WHERE id = :user_id",
                parameters=["user_id"],
                result_mode=SqlResultMode.FIRST_ROW
            )
        )
    }
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={"year": 2025, "user_id": 1, "table_name": "users_2025"},
        metadata=metadata
    )
    
    # Set variables
    context.set_variable("table_name", "users_2025")
    context.set_variable("user_id", 1)
    
    # Execute SQL query
    executor = SqlExecutor("user_data", metadata["user_data"], context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, dict)
    assert result.value["name"] == "Bob 2025"
    assert result.value["year"] == 2025


@pytest.mark.asyncio
async def test_hybrid_dynamic_columns_with_params(db_session):
    """
    Test: Hybrid scenario - Dynamic column list + parameterized filter
    Scenario: SELECT id, name, {{extra_columns}} FROM table WHERE status = :status
    Expected: Columns via interpolation, status via parameterization
    """
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_employees"))
    db_session.execute(text("""
        CREATE TABLE test_employees (
            id INT,
            name VARCHAR(50),
            department VARCHAR(50),
            salary DECIMAL(10,2),
            status VARCHAR(20)
        )
    """))
    db_session.execute(text("""
        INSERT INTO test_employees VALUES 
        (1, 'Alice', 'Engineering', 80000, 'active'),
        (2, 'Bob', 'Sales', 60000, 'active'),
        (3, 'Charlie', 'Engineering', 90000, 'inactive')
    """))
    db_session.commit()
    
    # Register connection
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = {
        "user_role": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="用户角色"
        ),
        "extra_columns": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="额外列"
        ),
        "employee_list": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="员工列表",
            dependencies=["extra_columns"],
            sql_config=SqlConfig(
                connection="test_db",
                query="SELECT id, name, {{extra_columns}} FROM test_employees WHERE status = :status ORDER BY id",
                parameters=["status"],
                result_mode=SqlResultMode.ALL_ROWS
            )
        )
    }
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={"user_role": "admin", "extra_columns": "department, salary"},
        metadata=metadata
    )
    
    # Set variables
    context.set_variable("extra_columns", "department, salary")
    context.set_variable("status", "active")
    
    # Execute SQL query
    executor = SqlExecutor("employee_list", metadata["employee_list"], context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, list)
    assert len(result.value) == 2  # Only active employees
    assert "department" in result.value[0]
    assert "salary" in result.value[0]


@pytest.mark.asyncio
async def test_hybrid_dynamic_order_with_params(db_session):
    """
    Test: Hybrid scenario - Dynamic ORDER BY + parameterized filter
    Scenario: SELECT * FROM table WHERE category = :category ORDER BY {{sort_field}} {{sort_order}}
    Expected: ORDER BY via interpolation, category via parameterization
    """
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_products"))
    db_session.execute(text("""
        CREATE TABLE test_products (
            id INT,
            name VARCHAR(50),
            category VARCHAR(50),
            price DECIMAL(10,2),
            stock INT
        )
    """))
    db_session.execute(text("""
        INSERT INTO test_products VALUES 
        (1, 'Laptop', 'Electronics', 1200.00, 5),
        (2, 'Mouse', 'Electronics', 25.00, 50),
        (3, 'Desk', 'Furniture', 300.00, 10),
        (4, 'Chair', 'Furniture', 150.00, 20),
        (5, 'Monitor', 'Electronics', 350.00, 15)
    """))
    db_session.commit()
    
    # Register connection
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = {
        "sort_field": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="排序字段"
        ),
        "sort_order": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="排序方向"
        ),
        "products": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="产品列表",
            dependencies=["sort_field", "sort_order"],
            sql_config=SqlConfig(
                connection="test_db",
                query="SELECT id, name, price, stock FROM test_products WHERE category = :category ORDER BY {{sort_field}} {{sort_order}}",
                parameters=["category"],
                result_mode=SqlResultMode.ALL_ROWS
            )
        )
    }
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={"sort_field": "price", "sort_order": "DESC"},
        metadata=metadata
    )
    
    # Set variables
    context.set_variable("sort_field", "price")
    context.set_variable("sort_order", "DESC")
    context.set_variable("category", "Electronics")
    
    # Execute SQL query
    executor = SqlExecutor("products", metadata["products"], context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, list)
    assert len(result.value) == 3  # Only Electronics
    # Should be sorted by price DESC
    assert float(result.value[0]["price"]) == 1200.00  # Laptop
    assert float(result.value[1]["price"]) == 350.00   # Monitor
    assert float(result.value[2]["price"]) == 25.00    # Mouse


@pytest.mark.asyncio
async def test_hybrid_dynamic_where_clause_with_params(db_session):
    """
    Test: Hybrid scenario - Dynamic WHERE clause + parameterized values
    Scenario: SELECT * FROM table WHERE 1=1 {{extra_condition}} AND status = :status
    Expected: Extra condition via interpolation, status via parameterization
    """
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_tasks"))
    db_session.execute(text("""
        CREATE TABLE test_tasks (
            id INT,
            title VARCHAR(100),
            owner_id INT,
            status VARCHAR(20),
            priority VARCHAR(20)
        )
    """))
    db_session.execute(text("""
        INSERT INTO test_tasks VALUES 
        (1, 'Task A', 100, 'active', 'high'),
        (2, 'Task B', 100, 'active', 'low'),
        (3, 'Task C', 200, 'active', 'high'),
        (4, 'Task D', 100, 'completed', 'high')
    """))
    db_session.commit()
    
    # Register connection
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = {
        "user_id": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="用户ID"
        ),
        "permission_level": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="权限级别"
        ),
        "permission_where": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="权限条件"
        ),
        "tasks": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="任务列表",
            dependencies=["permission_where"],
            sql_config=SqlConfig(
                connection="test_db",
                query="SELECT id, title, owner_id, priority FROM test_tasks WHERE 1=1 {{permission_where}} AND status = :status ORDER BY id",
                parameters=["status", "user_id"],
                result_mode=SqlResultMode.ALL_ROWS
            )
        )
    }
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={"user_id": 100, "permission_level": "user"},
        metadata=metadata
    )
    
    # Set variables - simulate user level permission
    context.set_variable("permission_where", "AND owner_id = :user_id")
    context.set_variable("user_id", 100)
    context.set_variable("status", "active")
    
    # Execute SQL query
    executor = SqlExecutor("tasks", metadata["tasks"], context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, list)
    assert len(result.value) == 2  # Only tasks owned by user 100 with active status
    assert all(task["owner_id"] == 100 for task in result.value)


@pytest.mark.asyncio
async def test_sql_injection_prevention(db_session):
    """
    Test: SQL injection prevention with parameterized queries
    Scenario: Malicious input like "'; DROP TABLE users; --" should be safely escaped
    Expected: Query treats the input as a literal string value, not SQL code
    """
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_secure"))
    db_session.execute(text("""
        CREATE TABLE test_secure (
            id INT,
            username VARCHAR(100),
            email VARCHAR(100)
        )
    """))
    db_session.execute(text("""
        INSERT INTO test_secure VALUES 
        (1, 'alice', 'alice@test.com'),
        (2, 'bob', 'bob@test.com')
    """))
    db_session.commit()
    
    # Register connection
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = {
        "username": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="用户名"
        ),
        "user_info": VariableMetadata(
            type="object",
            source=VariableSource.SQL,
            description="用户信息",
            dependencies=["username"],
            sql_config=SqlConfig(
                connection="test_db",
                query="SELECT id, username, email FROM test_secure WHERE username = :username",
                parameters=["username"],
                result_mode=SqlResultMode.FIRST_ROW
            )
        )
    }
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={},
        metadata=metadata
    )
    
    # Try malicious input
    malicious_input = "'; DROP TABLE test_secure; --"
    context.set_variable("username", malicious_input)
    
    # Execute SQL query
    executor = SqlExecutor("user_info", metadata["user_info"], context)
    result = await executor.execute()
    
    # Should not raise an error, just return None (no match found)
    # The table should still exist (not dropped)
    assert result.status == VariableStatus.SUCCESS
    assert result.value is None or isinstance(result.value, dict)
    
    # Verify table still exists
    check_result = db_session.execute(text("SELECT COUNT(*) as cnt FROM test_secure"))
    count = check_result.fetchone()[0]
    assert count == 2  # Table still has 2 rows


@pytest.mark.asyncio
async def test_multiple_params_same_query(db_session):
    """
    Test: Multiple parameters in the same query
    Scenario: WHERE created_at BETWEEN :start_date AND :end_date AND amount > :min_amount
    Expected: All parameters properly handled
    """
    # Setup test data
    db_session.execute(text("DROP TABLE IF EXISTS test_transactions"))
    db_session.execute(text("""
        CREATE TABLE test_transactions (
            id INT,
            created_at DATE,
            amount DECIMAL(10,2),
            type VARCHAR(20)
        )
    """))
    db_session.execute(text("""
        INSERT INTO test_transactions VALUES 
        (1, '2025-01-15', 1000.00, 'sale'),
        (2, '2025-02-20', 5000.00, 'sale'),
        (3, '2025-03-10', 3000.00, 'sale'),
        (4, '2025-01-25', 500.00, 'refund')
    """))
    db_session.commit()
    
    # Register connection
    test_engine = db_session.get_bind()
    db_connector.register_connection("test_db", test_engine)
    
    # Create metadata
    metadata = {
        "start_date": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="开始日期"
        ),
        "end_date": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="结束日期"
        ),
        "min_amount": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="最小金额"
        ),
        "transactions": VariableMetadata(
            type="array",
            source=VariableSource.SQL,
            description="交易记录",
            dependencies=["start_date", "end_date", "min_amount"],
            sql_config=SqlConfig(
                connection="test_db",
                query="""
                    SELECT id, created_at, amount, type 
                    FROM test_transactions 
                    WHERE created_at BETWEEN :start_date AND :end_date 
                      AND amount > :min_amount
                      AND type = :type
                    ORDER BY created_at
                """,
                parameters=["start_date", "end_date", "min_amount", "type"],
                result_mode=SqlResultMode.ALL_ROWS
            )
        )
    }
    
    context = ExecutionContext(
        "task_1", "tpl_1",
        user_inputs={"start_date": "2025-01-01", "end_date": "2025-03-31", "min_amount": 2000},
        metadata=metadata
    )
    
    # Set variables
    context.set_variable("start_date", "2025-01-01")
    context.set_variable("end_date", "2025-03-31")
    context.set_variable("min_amount", 2000)
    context.set_variable("type", "sale")
    
    # Execute SQL query
    executor = SqlExecutor("transactions", metadata["transactions"], context)
    result = await executor.execute()
    
    assert result.status == VariableStatus.SUCCESS
    assert isinstance(result.value, list)
    assert len(result.value) == 2  # Only id=2 and id=3 match all conditions
    assert float(result.value[0]["amount"]) == 5000.00
    assert float(result.value[1]["amount"]) == 3000.00

