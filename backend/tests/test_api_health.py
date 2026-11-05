from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Advisory output. Final decision rests with the human reviewer." in data["advisory"]
    assert "tesseract_detected" in data


def test_capabilities_endpoint():
    response = client.get("/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["system_mode"] == "offline"
    features = {c["feature"]: c["status"] for c in data["capabilities"]}
    assert "Deterministic Rules (D1)" in features
    assert features["LLM / Generative AI Reasoning"] == "unsupported"
    assert features["UIDAI Cryptographic PKI Signature Verification"] == "unsupported"
