"""Tests for configuration API"""
import pytest
import os


def test_get_ai_config_not_configured(client, monkeypatch):
    """Test getting AI config when not configured"""
    # Remove environment variable
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    response = client.get("/api/config/ai")
    
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] == False


def test_get_ai_config_from_env(client, monkeypatch):
    """Test getting AI config from environment variable"""
    # Set environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    
    response = client.get("/api/config/ai")
    
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] == True
    assert data["provider"] == "openai"


def test_update_ai_config(client):
    """Test updating AI config"""
    update_data = {
        "provider": "openai",
        "api_key": "sk-new-test-key"
    }
    
    response = client.put("/api/config/ai", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] == True
    assert data["provider"] == "openai"
    
    # Verify it's saved
    get_response = client.get("/api/config/ai")
    assert get_response.json()["configured"] == True

