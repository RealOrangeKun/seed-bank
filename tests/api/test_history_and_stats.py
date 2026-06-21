"""API tests for history/stats endpoints (require DB)."""
import pytest


@pytest.mark.integration
def test_full_history_lifecycle(client, png_bytes):
    # 1. Create a batch via analyze
    r = client.post("/api/analyze", files={"file": ("seed.png", png_bytes, "image/png")})
    assert r.status_code == 200, r.text
    batch_id = r.json()["batch_id"]

    # 2. It shows up in the batch list
    r = client.get("/api/batches")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert any(b["id"] == batch_id for b in body["batches"])
    assert "pagination" in body

    # 3. Batch detail
    r = client.get(f"/api/batches/{batch_id}")
    assert r.status_code == 200
    detail = r.json()["batch"]
    assert detail["id"] == batch_id
    assert detail["total_seeds"] == 2
    assert len(detail["images"]) == 1

    # 4. Detections
    r = client.get(f"/api/batches/{batch_id}/detections")
    assert r.status_code == 200
    dets = r.json()
    assert dets["total_detections"] == 2
    assert all("seed_type_name" in d for d in dets["detections"])

    # 5. Quality filter
    r = client.get(f"/api/batches/{batch_id}/detections", params={"quality": "GOOD"})
    assert r.status_code == 200
    assert all(d["quality_label"] == "GOOD" for d in r.json()["detections"])

    # 6. Invalid quality filter -> 400
    r = client.get(f"/api/batches/{batch_id}/detections", params={"quality": "BANANA"})
    assert r.status_code == 400


@pytest.mark.integration
def test_stats_after_analysis(client, png_bytes):
    client.post("/api/analyze", files={"file": ("seed.png", png_bytes, "image/png")})
    r = client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    stats = body["stats"]
    assert stats["total_batches"] >= 1
    assert stats["total_seeds_analyzed"] >= 2
    assert "batches_by_status" in stats


@pytest.mark.integration
def test_get_nonexistent_batch_404(client):
    r = client.get("/api/batches/999999999")
    assert r.status_code == 404


@pytest.mark.integration
def test_batches_pagination_validation(client):
    # page must be >= 1
    r = client.get("/api/batches", params={"page": 0})
    assert r.status_code == 422
    # limit must be <= 100
    r = client.get("/api/batches", params={"limit": 1000})
    assert r.status_code == 422
