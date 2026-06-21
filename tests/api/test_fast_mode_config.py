"""Fast (Roboflow) endpoints must fail gracefully when not configured (#3)."""


def test_fast_single_returns_503_without_key(client, png_bytes):
    # No ROBOFLOW_API_KEY in the test env -> 503, not a crash or hardcoded-key call.
    r = client.post("/api/analyze/fast", files={"file": ("seed.png", png_bytes, "image/png")})
    assert r.status_code == 503
    assert "ROBOFLOW_API_KEY" in r.json()["detail"]


def test_fast_batch_returns_503_without_key(client, png_bytes):
    files = [("files", ("a.png", png_bytes, "image/png"))]
    r = client.post("/api/analyze-batch/fast", files=files)
    assert r.status_code == 503
