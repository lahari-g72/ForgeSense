from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_unauthorized_telemetry_access():
    """Ensure unauthenticated users cannot view telemetry data"""
    response = client.get("/telemetry/")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

def test_login_invalid_credentials():
    """Ensure the API rejects bad passwords properly"""
    response = client.post(
        "/token", 
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_alerts_endpoint_structure():
    """Ensure alerts endpoint enforces auth rules"""
    response = client.get("/alerts/")
    assert response.status_code == 401