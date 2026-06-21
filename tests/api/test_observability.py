"""Tests for observability: health/readiness probes + request-id/timing headers (#15)."""
import pytest


def test_health_liveness(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_request_id_and_timing_headers(client):
    r = client.get("/health")
    assert "x-request-id" in r.headers
    assert len(r.headers["x-request-id"]) >= 8
    assert "x-process-time-ms" in r.headers
    # duration parses as a float
    float(r.headers["x-process-time-ms"])


def test_request_id_is_echoed_when_supplied(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123fixed"})
    assert r.headers["x-request-id"] == "abc123fixed"


@pytest.mark.integration
def test_readiness_ok_with_db_and_models(client):
    r = client.get("/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["checks"]["database"] is True
    assert body["checks"]["models"] is True
