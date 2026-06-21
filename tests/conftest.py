"""Shared pytest fixtures for the Seed Bank test suite.

Strategy: model weights are not available in CI/dev, so we mock the ModelManager and the
inference functions. DB-backed tests run against a real PostgreSQL (host port 5433 by default,
overridable via TEST_DATABASE_URL) and are marked ``integration`` so they can be skipped.
"""
import os
import sys

import numpy as np
import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://seedbank:seedbank_dev_password@localhost:5433/seedbank_db",
)
# main/app.database read DATABASE_URL at import time.
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)


class FakeModelManager:
    """Stand-in for app.ml.model_manager.ModelManager without real weights."""

    def __init__(self):
        self.detection_model = object()
        self.quality_models = {1: object(), 2: object()}
        self.seed_type_name_to_id = {"maize": 1, "coffee": 2}
        self.seed_type_id_to_name = {1: "maize", 2: "coffee"}

    def get_quality_model(self, seed_type_id):
        return self.quality_models[seed_type_id], 5.0

    def get_detection_threshold(self):
        return 0.0

    def get_seed_type_id(self, name):
        return self.seed_type_name_to_id.get(name)

    def get_seed_type_name(self, seed_type_id):
        return self.seed_type_id_to_name.get(seed_type_id)

    def get_config_summary(self):
        return {
            "detection_model": {"name": "fake-detect", "version": "v1", "threshold": 0.0},
            "quality_models": {
                "maize": {"name": "fake-maize", "version": "v4", "threshold": 5.0},
                "coffee": {"name": "fake-coffee", "version": "v3", "threshold": 0.0},
            },
            "seed_types": ["maize", "coffee"],
        }


def _fake_classified_seed(box, seed_type_id=1, seed_type_name="maize", quality="Good"):
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    return {
        "box": box,
        "detection_confidence": 0.95,
        "seed_type_id": seed_type_id,
        "seed_type_name": seed_type_name,
        "quality": quality,
        "good_percentage": 80.0 if quality == "Good" else 20.0,
        "bad_percentage": 20.0 if quality == "Good" else 80.0,
        "classification_confidence": 90.0,
        "raw_logits": 7.0 if quality == "Good" else 2.0,
        "area": w * h,
        "width": w,
        "height": h,
        "aspect_ratio": round(w / h, 2) if h else 1.0,
        "centroid": {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2},
    }


@pytest.fixture
def fake_seeds():
    """Two detected seeds (one good maize, one bad coffee)."""
    return [
        {"box": (10, 10, 40, 50), "detection_confidence": 0.95, "seed_type_id": 1, "seed_type_name": "maize"},
        {"box": (60, 60, 90, 100), "detection_confidence": 0.91, "seed_type_id": 2, "seed_type_name": "coffee"},
    ]


@pytest.fixture
def client(monkeypatch):
    """FastAPI TestClient with a mocked model manager + patched inference.

    Avoids the startup event (which would try to load real weights) by importing the app
    and overriding globals directly.
    """
    from fastapi.testclient import TestClient
    import main

    fake_mm = FakeModelManager()

    # Neutralize the registered startup model-loading handler so TestClient startup does
    # not try to load real .pth weights. The handler was registered at import time, so we
    # strip startup handlers from the router and install our fake manager directly.
    monkeypatch.setattr(main.app.router, "on_startup", [], raising=False)
    monkeypatch.setattr(main, "model_manager", fake_mm, raising=False)
    monkeypatch.setattr(main, "device", "cpu", raising=False)

    def fake_detect(rgb_img):
        h, w, _ = rgb_img.shape
        return (
            [
                {"box": (10, 10, 40, 50), "detection_confidence": 0.95, "seed_type_id": 1, "seed_type_name": "maize"},
                {"box": (60, 60, 90, 100), "detection_confidence": 0.91, "seed_type_id": 2, "seed_type_name": "coffee"},
            ],
            (h, w),
        )

    def fake_classify(rgb_img, detected_seeds):
        out = []
        for i, s in enumerate(detected_seeds):
            out.append(
                _fake_classified_seed(
                    s["box"],
                    seed_type_id=s.get("seed_type_id") or 1,
                    seed_type_name=s.get("seed_type_name") or "maize",
                    quality="Good" if i % 2 == 0 else "Bad",
                )
            )
        return out

    monkeypatch.setattr(main, "detect_seeds", fake_detect)
    monkeypatch.setattr(main, "classify_seeds", fake_classify)

    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def db_session():
    """A real DB session against the test database (rolled back after the test)."""
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def png_bytes():
    """A small valid PNG encoded in-memory (no external files needed)."""
    import cv2

    img = np.zeros((120, 120, 3), dtype=np.uint8)
    img[:] = (40, 80, 160)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()
