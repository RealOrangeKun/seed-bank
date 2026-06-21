"""Tests for report features: shareable links + annotated image download (#20 #21)."""
import pytest


def _make_batch(client, png_bytes):
    r = client.post("/api/analyze", files={"file": ("seed.png", png_bytes, "image/png")})
    assert r.status_code == 200, r.text
    return r.json()["batch_id"]


@pytest.mark.integration
def test_share_and_fetch_public_report(client, png_bytes):
    bid = _make_batch(client, png_bytes)
    r = client.post(f"/api/batches/{bid}/share")
    assert r.status_code == 200
    token = r.json()["share_token"]
    assert token

    # Public fetch works without any fingerprint coupling.
    r = client.get(f"/api/shared/{token}")
    assert r.status_code == 200
    batch = r.json()["batch"]
    assert batch["id"] == bid
    assert "detections" in batch and "images" in batch

    # Idempotent: sharing again returns the same token.
    r2 = client.post(f"/api/batches/{bid}/share")
    assert r2.json()["share_token"] == token


@pytest.mark.integration
def test_revoke_share(client, png_bytes):
    bid = _make_batch(client, png_bytes)
    token = client.post(f"/api/batches/{bid}/share").json()["share_token"]
    r = client.delete(f"/api/batches/{bid}/share")
    assert r.status_code == 200
    # Token no longer resolves.
    assert client.get(f"/api/shared/{token}").status_code == 404


@pytest.mark.integration
def test_shared_unknown_token_404(client):
    assert client.get("/api/shared/nope-not-a-real-token").status_code == 404


@pytest.mark.integration
def test_annotated_image_png(client, png_bytes):
    bid = _make_batch(client, png_bytes)
    # Find the image id from batch detail.
    detail = client.get(f"/api/batches/{bid}").json()["batch"]
    image_id = detail["images"][0]["id"]
    r = client.get(f"/api/batches/{bid}/images/{image_id}/annotated.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic


@pytest.mark.integration
def test_annotated_image_unknown_404(client, png_bytes):
    bid = _make_batch(client, png_bytes)
    assert client.get(f"/api/batches/{bid}/images/999999/annotated.png").status_code == 404
