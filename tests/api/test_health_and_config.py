"""API tests for non-persisting endpoints (health/config) with a mocked model manager."""


def test_root_health(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "running"
    assert body["models_loaded"] is True


def test_config(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert "detection_model" in body
    assert "quality_models" in body
    assert body["image_size"] == 224


def test_models_config(client):
    r = client.get("/api/models/config")
    assert r.status_code == 200
    body = r.json()
    assert set(body["seed_types"]) == {"maize", "coffee"}
