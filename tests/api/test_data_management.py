"""Tests for data management: delete, bulk delete, search/sort, fast persistence (#7 #18 #19)."""
import pytest


def _make_batch(client, png_bytes):
    r = client.post("/api/analyze", files={"file": ("seed.png", png_bytes, "image/png")})
    assert r.status_code == 200, r.text
    return r.json()["batch_id"]


@pytest.mark.integration
def test_delete_batch(client, png_bytes):
    bid = _make_batch(client, png_bytes)
    r = client.delete(f"/api/batches/{bid}")
    assert r.status_code == 200
    assert r.json()["deleted"] == bid
    # Now it's gone.
    assert client.get(f"/api/batches/{bid}").status_code == 404
    # Deleting again -> 404.
    assert client.delete(f"/api/batches/{bid}").status_code == 404


@pytest.mark.integration
def test_bulk_delete(client, png_bytes):
    b1 = _make_batch(client, png_bytes)
    b2 = _make_batch(client, png_bytes)
    r = client.post("/api/batches/delete", json={"batch_ids": [b1, b2, 999999999]})
    assert r.status_code == 200
    body = r.json()
    assert set(body["deleted"]) == {b1, b2}
    assert 999999999 in body["not_found"]
    assert body["deleted_count"] == 2


@pytest.mark.integration
def test_bulk_delete_requires_ids(client):
    assert client.post("/api/batches/delete", json={}).status_code == 400


@pytest.mark.integration
def test_search_sort_params_accepted(client, png_bytes):
    _make_batch(client, png_bytes)
    # sort by total_seeds asc
    r = client.get("/api/batches", params={"sort": "total_seeds", "order": "asc"})
    assert r.status_code == 200
    # good_percentage sort path (computed expression)
    r = client.get("/api/batches", params={"sort": "good_percentage", "order": "desc"})
    assert r.status_code == 200
    # min_seeds filter
    r = client.get("/api/batches", params={"min_seeds": 1})
    assert r.status_code == 200
    # invalid sort rejected by the pattern -> 422
    assert client.get("/api/batches", params={"sort": "bogus"}).status_code == 422


@pytest.mark.integration
def test_date_filter(client, png_bytes):
    _make_batch(client, png_bytes)
    # A far-future lower bound should return zero batches.
    r = client.get("/api/batches", params={"date_from": "2999-01-01"})
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 0


@pytest.mark.integration
def test_fast_endpoint_persists(client, png_bytes, monkeypatch):
    """/api/analyze/fast now persists and returns a batch_id (#7)."""
    import main

    # Configure Roboflow + stub the HTTP call so detection returns one maize box.
    monkeypatch.setattr(main, "ROBOFLOW_URL", "http://stub.local/detect")

    class _Resp:
        status_code = 200

        def json(self):
            return {"predictions": [{"x": 60, "y": 60, "width": 30, "height": 30,
                                     "confidence": 0.9, "class": "maize"}]}

    monkeypatch.setattr(main.requests, "post", lambda *a, **k: _Resp())

    r = client.post("/api/analyze/fast", files={"file": ("seed.png", png_bytes, "image/png")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "batch_id" in body and body["batch_id"]
    # The batch is now retrievable from history.
    assert client.get(f"/api/batches/{body['batch_id']}").status_code == 200
