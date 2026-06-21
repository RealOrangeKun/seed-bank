"""Unit tests for the export router serialization (``/batches/{id}/export.*``).

The CSV/JSON column order, decimal formatting, and download headers live in
the router, not the service. We pin them here with a minimal app that mounts
only ``batches.router`` and overrides the service + current-user deps — no DB,
Redis, or MinIO, so this stays in the unit tier.

What's asserted:
- CSV header row matches the fixed ``_EXPORT_COLUMNS`` order.
- Decimal columns serialize as strings (``"0.9234"``), matching JSON.
- ``Content-Disposition: attachment`` with a ``batch-<id>`` filename on both.
- The JSON export is wrapped in the standard ``Envelope``.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from seedbank.api.deps import batch_service, current_user
from seedbank.api.v1 import batches as batches_module
from seedbank.api.v1.batches import _EXPORT_COLUMNS
from seedbank.domain.user import AuthenticatedUser, Role

pytestmark = pytest.mark.unit


def _detection(**overrides: object) -> SimpleNamespace:
    """A stand-in detection ORM row — only the columns ``SeedDetectionOut``
    reads are needed. Decimals mirror the DB's ``NUMERIC`` precision."""
    base = {
        "id": uuid4(),
        "seed_type_id": uuid4(),
        "quality": "good",
        "confidence": Decimal("0.9234"),
        "detection_confidence": Decimal("0.8800"),
        "box_x_norm": Decimal("0.100000"),
        "box_y_norm": Decimal("0.200000"),
        "box_w_norm": Decimal("0.300000"),
        "box_h_norm": Decimal("0.400000"),
        "area_px": 1234,
        "width_px": 40,
        "height_px": 30,
        "aspect_ratio": Decimal("1.3333"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_app(detections: list[SimpleNamespace]) -> FastAPI:
    """Minimal app: only the batches router, with the service + auth deps
    overridden so the export path runs with no infrastructure."""
    app = FastAPI()
    app.include_router(batches_module.router, prefix="/api/v1")

    async def _fake_detections_for_export(*, batch_id: UUID, actor: object) -> list[SimpleNamespace]:
        return detections

    service_stub = SimpleNamespace(detections_for_export=_fake_detections_for_export)

    app.dependency_overrides[batch_service] = lambda: service_stub
    app.dependency_overrides[current_user] = lambda: AuthenticatedUser(
        id=uuid4(),
        email="x@y.com",
        role=Role.END_USER,
        is_active=True,
        is_verified=True,
        scopes=frozenset(),
        auth_method="jwt",
    )
    return app


async def _client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://t")


class TestCsvExport:
    async def test_header_row_matches_fixed_column_order(self) -> None:
        app = _build_app([_detection()])
        async with await _client(app) as client:
            r = await client.get(f"/api/v1/batches/{uuid4()}/export.csv")

        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/csv")
        rows = list(csv.reader(io.StringIO(r.text)))
        assert tuple(rows[0]) == _EXPORT_COLUMNS

    async def test_decimals_serialize_as_strings(self) -> None:
        det = _detection(confidence=Decimal("0.9234"))
        app = _build_app([det])
        async with await _client(app) as client:
            r = await client.get(f"/api/v1/batches/{uuid4()}/export.csv")

        reader = csv.DictReader(io.StringIO(r.text))
        row = next(reader)
        assert row["confidence"] == "0.9234"
        assert row["box_x_norm"] == "0.100000"
        assert row["quality"] == "good"

    async def test_attachment_filename_carries_batch_id(self) -> None:
        batch_id = uuid4()
        app = _build_app([_detection()])
        async with await _client(app) as client:
            r = await client.get(f"/api/v1/batches/{batch_id}/export.csv")

        cd = r.headers["content-disposition"]
        assert "attachment" in cd
        assert f"batch-{batch_id}.csv" in cd

    async def test_empty_batch_emits_header_only(self) -> None:
        app = _build_app([])
        async with await _client(app) as client:
            r = await client.get(f"/api/v1/batches/{uuid4()}/export.csv")

        rows = [r for r in csv.reader(io.StringIO(r.text)) if r]
        assert len(rows) == 1  # header, no data rows
        assert tuple(rows[0]) == _EXPORT_COLUMNS


class TestJsonExport:
    async def test_envelope_shape_and_decimal_strings(self) -> None:
        det = _detection(confidence=Decimal("0.9234"))
        app = _build_app([det])
        async with await _client(app) as client:
            r = await client.get(f"/api/v1/batches/{uuid4()}/export.json")

        assert r.status_code == 200, r.text
        body = r.json()
        assert "data" in body
        assert len(body["data"]) == 1
        assert body["data"][0]["confidence"] == "0.9234"

    async def test_attachment_filename_carries_batch_id(self) -> None:
        batch_id = uuid4()
        app = _build_app([_detection()])
        async with await _client(app) as client:
            r = await client.get(f"/api/v1/batches/{batch_id}/export.json")

        assert f"batch-{batch_id}.json" in r.headers["content-disposition"]
