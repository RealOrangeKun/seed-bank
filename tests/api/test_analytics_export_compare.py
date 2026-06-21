"""API tests for the analytics, export, and compare features (require DB)."""
import csv
import io

import pytest


def _make_batch(client, png_bytes):
    r = client.post("/api/analyze", files={"file": ("seed.png", png_bytes, "image/png")})
    assert r.status_code == 200, r.text
    return r.json()["batch_id"]


@pytest.mark.integration
def test_analytics_shape_after_analysis(client, png_bytes):
    _make_batch(client, png_bytes)
    r = client.get("/api/analytics")
    assert r.status_code == 200, r.text
    a = r.json()["analytics"]
    for key in ("totals", "daily_trend", "seed_type_split",
                "size_distribution", "confidence_distribution", "top_batches"):
        assert key in a
    assert a["totals"]["seeds"] >= 2
    # good + bad == seeds
    assert a["totals"]["good"] + a["totals"]["bad"] == a["totals"]["seeds"]
    # seed-type split sums to total seeds
    assert sum(s["total"] for s in a["seed_type_split"]) == a["totals"]["seeds"]
    # histograms are well-formed: len(counts) == len(bins) - 1 (or empty)
    sd = a["size_distribution"]
    if sd["counts"]:
        assert len(sd["bins"]) == len(sd["counts"]) + 1


@pytest.mark.integration
def test_analytics_always_well_formed(client):
    # The endpoint must always return 200 with the full payload shape, even with a
    # days filter and regardless of whether the user has history.
    r = client.get("/api/analytics", params={"days": 7})
    assert r.status_code == 200
    a = r.json()["analytics"]
    assert isinstance(a["totals"]["batches"], int)
    assert isinstance(a["daily_trend"], list)
    assert a["period"]["days"] == 7


@pytest.mark.integration
def test_export_csv(client, png_bytes):
    batch_id = _make_batch(client, png_bytes)
    r = client.get(f"/api/batches/{batch_id}/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert len(rows) == 2
    assert "seed_type" in reader.fieldnames
    assert rows[0]["quality"] in {"GOOD", "BAD"}


@pytest.mark.integration
def test_export_json(client, png_bytes):
    batch_id = _make_batch(client, png_bytes)
    r = client.get(f"/api/batches/{batch_id}/export.json")
    assert r.status_code == 200
    body = r.json()
    assert body["total_detections"] == 2
    assert len(body["detections"]) == 2


@pytest.mark.integration
def test_export_unknown_batch_404(client, png_bytes):
    # Establish a user, then request a batch id that cannot belong to them.
    _make_batch(client, png_bytes)
    r = client.get("/api/batches/987654321/export.csv")
    assert r.status_code == 404


@pytest.mark.integration
def test_compare_batches(client, png_bytes):
    b1 = _make_batch(client, png_bytes)
    b2 = _make_batch(client, png_bytes)
    r = client.post("/api/compare", json={"batch_ids": [b1, b2]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 2
    ids = {b["id"] for b in body["batches"]}
    assert ids == {b1, b2}
    for b in body["batches"]:
        assert b["good_seeds_count"] + b["bad_seeds_count"] == b["total_seeds"]
        assert "seed_types" in b


@pytest.mark.integration
def test_compare_requires_batch_ids(client):
    r = client.post("/api/compare", json={})
    assert r.status_code == 400


@pytest.mark.integration
def test_compare_rejects_too_many(client):
    r = client.post("/api/compare", json={"batch_ids": list(range(1, 30))})
    assert r.status_code == 400
