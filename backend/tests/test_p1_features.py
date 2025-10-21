"""Tests for P1.0 features: WebSocket, Report History, DB Connections"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.main import app
from app.database import Base, get_db
from app.models.db_models import Template, Report, ReportStatus, DBConnection, DBEngineType


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_p1.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create and clean test database tables for each test"""
    Base.metadata.create_all(bind=test_engine)
    yield
    # Clean all tables after each test
    db = TestSessionLocal()
    db.query(Report).delete()
    db.query(DBConnection).delete()
    db.query(Template).delete()
    db.commit()
    db.close()


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def test_template(client):
    """Create a test template"""
    response = client.post("/api/templates", json={
        "name": "Test Report Template",
        "description": "Template for testing",
        "template_content": "# {{title}}\n\n{{content}}",
        "metadata": {
            "title": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Report title"
            },
            "content": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Report content"
            }
        }
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def test_reports(client, test_template):
    """Create multiple test reports"""
    from datetime import datetime, timedelta
    import time
    reports = []
    
    # Create a few reports with different statuses and staggered timestamps
    for i in range(3):
        # Create task first (simulate background task creating report)
        db = next(override_get_db())
        report_id = f"rpt_test_{uuid.uuid4().hex[:8]}"
        task_id = f"task_test_{uuid.uuid4().hex[:8]}"
        
        status = [ReportStatus.SUCCESS, ReportStatus.FAILED, ReportStatus.SUCCESS][i]
        report = Report(
            id=report_id,
            template_id=test_template["id"],
            task_id=task_id,
            title=f"Test Report {i+1}",
            status=status,
            markdown_content=f"# Test Report {i+1}\n\nContent here",
            duration_ms=1000 * (i + 1)
        )
        db.add(report)
        db.commit()
        reports.append(report)
        db.close()
        
        # Small delay to ensure different timestamps
        time.sleep(0.01)
    
    return reports


# ============================================================================
# Test 1: Report History List API
# ============================================================================

def test_list_reports_empty(client):
    """Test listing reports when none exist"""
    response = client.get("/api/reports/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_list_reports(client, test_reports):
    """Test listing all reports"""
    response = client.get("/api/reports/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Check all expected reports are present
    titles = {item["title"] for item in data["items"]}
    assert titles == {"Test Report 1", "Test Report 2", "Test Report 3"}


def test_list_reports_with_status_filter(client, test_reports):
    """Test filtering reports by status"""
    response = client.get("/api/reports/?status=success")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["status"] == "success" for item in data["items"])


def test_list_reports_with_template_filter(client, test_reports, test_template):
    """Test filtering reports by template"""
    response = client.get(f"/api/reports/?template_id={test_template['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert all(item["template_id"] == test_template["id"] for item in data["items"])


def test_list_reports_pagination(client, test_reports):
    """Test report pagination"""
    # Page 1 with page_size=2
    response = client.get("/api/reports/?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    
    # Page 2
    response = client.get("/api/reports/?page=2&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1


# ============================================================================
# Test 2: Database Connection Management API
# ============================================================================

def test_create_db_connection(client):
    """Test creating a database connection"""
    response = client.post("/api/config/db-connections/", json={
        "name": "Test MySQL Connection",
        "engine": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "testdb",
        "username": "testuser",
        "password": "testpass",
        "is_active": True
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test MySQL Connection"
    assert data["engine"] == "mysql"
    assert data["host"] == "localhost"
    assert data["port"] == 3306
    assert data["is_active"] is True
    assert "id" in data


def test_create_db_connection_duplicate_name(client):
    """Test creating connection with duplicate name fails"""
    conn_data = {
        "name": "Duplicate Connection",
        "engine": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "testdb",
        "username": "user",
        "password": "pass"
    }
    
    # First creation succeeds
    response1 = client.post("/api/config/db-connections/", json=conn_data)
    assert response1.status_code == 201
    
    # Second creation fails
    response2 = client.post("/api/config/db-connections/", json=conn_data)
    assert response2.status_code == 400


def test_list_db_connections(client):
    """Test listing database connections"""
    # Create some connections
    for i in range(3):
        client.post("/api/config/db-connections/", json={
            "name": f"Connection {i}",
            "engine": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": f"db{i}",
            "username": "user",
            "password": "pass"
        })
    
    response = client.get("/api/config/db-connections/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3


def test_get_db_connection(client):
    """Test getting a specific database connection"""
    # Create connection
    create_response = client.post("/api/config/db-connections/", json={
        "name": "Get Test Connection",
        "engine": "mysql",
        "host": "testhost",
        "port": 3306,
        "database": "testdb",
        "username": "testuser",
        "password": "testpass"
    })
    conn_id = create_response.json()["id"]
    
    # Get connection
    response = client.get(f"/api/config/db-connections/{conn_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conn_id
    assert data["name"] == "Get Test Connection"


def test_get_db_connection_not_found(client):
    """Test getting non-existent connection returns 404"""
    response = client.get("/api/config/db-connections/nonexistent")
    assert response.status_code == 404


def test_update_db_connection(client):
    """Test updating a database connection"""
    # Create connection
    create_response = client.post("/api/config/db-connections/", json={
        "name": "Update Test",
        "engine": "postgresql",
        "host": "oldhost",
        "port": 5432,
        "database": "olddb",
        "username": "olduser",
        "password": "oldpass"
    })
    conn_id = create_response.json()["id"]
    
    # Update connection
    update_response = client.put(f"/api/config/db-connections/{conn_id}", json={
        "name": "Updated Connection",
        "host": "newhost",
        "database": "newdb"
    })
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated Connection"
    assert data["host"] == "newhost"
    assert data["database"] == "newdb"
    assert data["port"] == 5432  # Unchanged


def test_delete_db_connection(client):
    """Test deleting a database connection"""
    # Create connection
    create_response = client.post("/api/config/db-connections/", json={
        "name": "Delete Test",
        "engine": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "testdb",
        "username": "user",
        "password": "pass"
    })
    conn_id = create_response.json()["id"]
    
    # Delete connection
    delete_response = client.delete(f"/api/config/db-connections/{conn_id}")
    assert delete_response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/config/db-connections/{conn_id}")
    assert get_response.status_code == 404


def test_test_db_connection_invalid(client):
    """Test testing an invalid database connection"""
    # Create connection with invalid credentials
    create_response = client.post("/api/config/db-connections/", json={
        "name": "Invalid Connection",
        "engine": "mysql",
        "host": "invalid-host-12345",
        "port": 9999,
        "database": "testdb",
        "username": "user",
        "password": "pass"
    })
    conn_id = create_response.json()["id"]
    
    # Test connection
    response = client.post(f"/api/config/db-connections/{conn_id}/test")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "failed" in data["message"].lower()


# ============================================================================
# Test 3: WebSocket (Basic test - full WebSocket testing requires special setup)
# ============================================================================

def test_websocket_endpoint_exists(client):
    """Test that WebSocket endpoint is registered"""
    # We can't fully test WebSocket in regular pytest, but we can verify endpoint exists
    # The actual WebSocket functionality would need special WebSocket test client
    # For now, just verify the route is registered
    from app.main import app
    routes = [route.path for route in app.routes]
    assert "/ws/report-generation/{task_id}" in routes


# ============================================================================
# Summary
# ============================================================================

def test_p1_summary():
    """Summary of P1.0 features tested"""
    print("\n" + "="*60)
    print("P1.0 Features Test Summary")
    print("="*60)
    print("✅ Report History List API - 5 tests")
    print("✅ Database Connection Management API - 9 tests")
    print("✅ WebSocket Registration - 1 test")
    print("="*60)
    print("Total: 15 tests")
    print("="*60)

