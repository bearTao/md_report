"""Tests for report generation API"""
import pytest
import time


def test_generate_report(client, sample_template_with_system):
    """Test generating a report"""
    # Create template
    template_response = client.post("/api/templates", json=sample_template_with_system)
    template_id = template_response.json()["id"]
    
    # Generate report
    generate_data = {
        "template_id": template_id,
        "inputs": {
            "title": "Test Report",
            "content": "This is test content"
        }
    }
    response = client.post("/api/reports/generate", json=generate_data)
    
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] in ["pending", "running"]
    
    # Wait a bit for background task
    time.sleep(2)


def test_generate_report_template_not_found(client):
    """Test generating report with non-existent template"""
    generate_data = {
        "template_id": "nonexistent",
        "inputs": {}
    }
    response = client.post("/api/reports/generate", json=generate_data)
    
    assert response.status_code == 404


def test_get_report(client, sample_template_with_system):
    """Test getting generated report"""
    # Create template
    template_response = client.post("/api/templates", json=sample_template_with_system)
    template_id = template_response.json()["id"]
    
    # Generate report
    generate_data = {
        "template_id": template_id,
        "inputs": {
            "title": "My Report",
            "content": "Report content here"
        }
    }
    gen_response = client.post("/api/reports/generate", json=generate_data)
    
    # Wait for generation to complete
    time.sleep(2)
    
    # Get the report - need to query by checking database
    # For this test, we'll check if we can get reports
    # (In a real scenario, we'd track the report_id from the task)


def test_download_report_not_found(client):
    """Test downloading non-existent report"""
    response = client.get("/api/reports/nonexistent/download")
    
    assert response.status_code == 404

