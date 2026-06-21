"""API tests for the analyze endpoints (mocked models, real DB for persistence)."""
import pytest


def test_analyze_rejects_non_image(client):
    r = client.post(
        "/api/analyze",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400
    assert "image" in r.json()["detail"].lower()


def test_analyze_rejects_corrupt_image(client):
    # content_type says image but bytes are not decodable -> 400 (ValueError path)
    r = client.post(
        "/api/analyze",
        files={"file": ("broken.png", b"not-a-real-png", "image/png")},
    )
    assert r.status_code == 400


@pytest.mark.integration
def test_analyze_happy_path(client, png_bytes):
    r = client.post(
        "/api/analyze",
        files={"file": ("seed.png", png_bytes, "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["total_seeds"] == 2
    assert "batch_id" in body
    assert len(body["bounding_boxes"]) == 2
    box = body["bounding_boxes"][0]
    for key in ("x1", "y1", "x2", "y2", "quality", "color", "seed_type"):
        assert key in box
    # statistics consistency
    stats = body["statistics"]
    assert stats["good_seeds"] + stats["bad_seeds"] == body["total_seeds"]
    assert stats["good_percentage"] + stats["bad_percentage"] == pytest.approx(100.0, abs=0.05)


@pytest.mark.integration
def test_analyze_response_has_no_duplicate_keys(client, png_bytes):
    """JSON cannot express dup keys, but the source dict literal should not define one twice.

    We assert the rendered box still carries a correct seed_type value as a guard.
    """
    r = client.post("/api/analyze", files={"file": ("seed.png", png_bytes, "image/png")})
    assert r.status_code == 200
    box = r.json()["bounding_boxes"][0]
    assert box["seed_type"] in {"maize", "coffee"}


@pytest.mark.integration
def test_analyze_batch_happy_path(client, png_bytes):
    files = [
        ("files", ("a.png", png_bytes, "image/png")),
        ("files", ("b.png", png_bytes, "image/png")),
    ]
    r = client.post("/api/analyze-batch", files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_images"] == 2
    assert body["total_seeds_all_images"] == 4
    assert len(body["results"]) == 2


@pytest.mark.integration
def test_analyze_batch_rejects_non_image(client, png_bytes):
    files = [
        ("files", ("a.png", png_bytes, "image/png")),
        ("files", ("b.txt", b"x", "text/plain")),
    ]
    r = client.post("/api/analyze-batch", files=files)
    assert r.status_code == 400
