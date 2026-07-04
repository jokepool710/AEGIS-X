from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_platform_status() -> None:
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["platform"] == "AEGIS-X"
