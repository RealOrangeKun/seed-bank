"""Security/behavior tests for image-serving endpoints."""
import pytest


@pytest.mark.integration
def test_serve_image_path_traversal_blocked(client, png_bytes):
    # Create a batch so a user exists for this fingerprint.
    r = client.post("/api/analyze", files={"file": ("seed.png", png_bytes, "image/png")})
    batch_id = r.json()["batch_id"]

    # A '..' filename segment must be rejected by the explicit guard (400) and never
    # escape the batch directory. (Encoded-slash payloads simply 404/405 on the route,
    # which is also a safe rejection.)
    r = client.get(f"/api/images/{batch_id}/..")
    assert r.status_code in (400, 404, 405)
    # Backslash / dotdot embedded in a single segment hits the explicit guard.
    r = client.get(f"/api/images/{batch_id}/..%5c..%5cetc")
    assert r.status_code in (400, 404, 405)


@pytest.mark.integration
def test_serve_image_unknown_user_404(client):
    # No analyze performed under this fresh path; user lookup should 404.
    # (TestClient reuses a fingerprint, so use a batch id that cannot belong to anyone.)
    r = client.get("/api/images/987654321/image_0.png")
    assert r.status_code in (403, 404)
