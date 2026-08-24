import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_tools_endpoint():
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    tools = response.json()
    assert any(t["name"] == "file_manager" for t in tools)
    assert any(t["name"] == "code_executor" for t in tools)


def test_goal_submission_endpoint():
    payload = {
        "goal": "Test API goal execution with mock provider",
        "llm_provider": "mock",
        "max_iterations": 5,
    }
    response = client.post("/api/v1/goals?run_async=false", json=payload)
    assert response.status_code == 200
    run_data = response.json()
    assert run_data["status"] == "completed"
    assert run_data["plan"] is not None
    assert len(run_data["step_records"]) > 0
