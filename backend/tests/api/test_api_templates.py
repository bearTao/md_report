"""Tests for template management API"""
import pytest


def test_create_template(client, sample_template_data):
    """Test creating a template"""
    response = client.post("/api/templates", json=sample_template_data)
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == sample_template_data["name"]
    assert data["description"] == sample_template_data["description"]
    assert data["template_content"] == sample_template_data["template_content"]


def test_create_template_invalid_syntax(client, sample_template_data):
    """Test creating template with invalid Jinja2 syntax"""
    invalid_data = sample_template_data.copy()
    invalid_data["template_content"] = "# {{title"  # Unclosed tag
    
    response = client.post("/api/templates", json=invalid_data)
    assert response.status_code == 400
    assert "Invalid template syntax" in response.json()["detail"]


def test_list_templates_empty(client):
    """Test listing templates when empty"""
    response = client.get("/api/templates")
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_templates(client, sample_template_data):
    """Test listing templates"""
    # Create two templates
    client.post("/api/templates", json=sample_template_data)
    
    template_2 = sample_template_data.copy()
    template_2["name"] = "Template 2"
    client.post("/api/templates", json=template_2)
    
    # List templates
    response = client.get("/api/templates")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2


def test_list_templates_with_search(client, sample_template_data):
    """Test searching templates"""
    # Create templates
    client.post("/api/templates", json=sample_template_data)
    
    template_2 = sample_template_data.copy()
    template_2["name"] = "Another Template"
    template_2["description"] = "Different description"
    client.post("/api/templates", json=template_2)
    
    # Search for "Another" (should match only second template)
    response = client.get("/api/templates?q=Another")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Another Template"


def test_get_template(client, sample_template_data):
    """Test getting template by ID"""
    # Create template
    create_response = client.post("/api/templates", json=sample_template_data)
    template_id = create_response.json()["id"]
    
    # Get template
    response = client.get(f"/api/templates/{template_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template_id
    assert data["name"] == sample_template_data["name"]


def test_get_template_not_found(client):
    """Test getting non-existent template"""
    response = client.get("/api/templates/nonexistent")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_template(client, sample_template_data):
    """Test updating template"""
    # Create template
    create_response = client.post("/api/templates", json=sample_template_data)
    template_id = create_response.json()["id"]
    
    # Update template
    update_data = {
        "name": "Updated Template",
        "description": "Updated description"
    }
    response = client.put(f"/api/templates/{template_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Template"
    assert data["description"] == "Updated description"
    # template_content should remain unchanged
    assert data["template_content"] == sample_template_data["template_content"]


def test_delete_template(client, sample_template_data):
    """Test deleting template"""
    # Create template
    create_response = client.post("/api/templates", json=sample_template_data)
    template_id = create_response.json()["id"]
    
    # Delete template
    response = client.delete(f"/api/templates/{template_id}")
    
    assert response.status_code == 204
    
    # Verify deletion
    get_response = client.get(f"/api/templates/{template_id}")
    assert get_response.status_code == 404


def test_delete_template_not_found(client):
    """Test deleting non-existent template"""
    response = client.delete("/api/templates/nonexistent")
    
    assert response.status_code == 404

