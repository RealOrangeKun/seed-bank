"""Tests for rate limiting + upload guards (#16)."""
import pytest

from app import limits


@pytest.mark.integration
def test_oversized_upload_rejected_413(client, png_bytes, monkeypatch):
    # Shrink the cap so our small PNG is "too big".
    monkeypatch.setattr(limits, "MAX_UPLOAD_BYTES", 10)
    r = client.post("/api/analyze", files={"file": ("big.png", png_bytes, "image/png")})
    assert r.status_code == 413
    assert "limit" in r.json()["detail"].lower()


@pytest.mark.integration
def test_batch_count_rejected_400(client, png_bytes, monkeypatch):
    monkeypatch.setattr(limits, "MAX_BATCH_IMAGES", 2)
    files = [("files", (f"{i}.png", png_bytes, "image/png")) for i in range(3)]
    r = client.post("/api/analyze-batch", files=files)
    assert r.status_code == 400
    assert "max" in r.json()["detail"].lower()


@pytest.mark.integration
def test_rate_limit_returns_429(client, png_bytes, monkeypatch):
    # Force a tiny limit so the 2nd request trips it.
    limits.analyze_limiter.max_requests = 1
    limits.analyze_limiter.window = 60
    limits.analyze_limiter.reset()
    try:
        r1 = client.post("/api/analyze", files={"file": ("a.png", png_bytes, "image/png")})
        assert r1.status_code == 200, r1.text
        r2 = client.post("/api/analyze", files={"file": ("b.png", png_bytes, "image/png")})
        assert r2.status_code == 429
        assert "Retry-After" in r2.headers
    finally:
        # Restore defaults for other tests.
        limits.analyze_limiter.max_requests = limits.RATE_LIMIT_REQUESTS
        limits.analyze_limiter.reset()


def test_limiter_unit_window():
    lim = limits.SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    assert lim.check("k")[0] is True
    assert lim.check("k")[0] is True
    allowed, retry = lim.check("k")
    assert allowed is False and retry >= 1
    # different key is independent
    assert lim.check("other")[0] is True
