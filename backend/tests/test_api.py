from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"


def test_get_nonexistent_document():
    response = client.get(
        "/api/v1/documents/does-not-exist.pdf"
    )

    assert response.status_code == 404

    data = response.json()

    assert "detail" in data