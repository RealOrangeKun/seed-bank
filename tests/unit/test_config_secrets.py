"""Verify file-based secrets loading via Pydantic ``secrets_dir``.

The prod overlay (`compose.prod.yaml`) mounts each secret at
`/run/secrets/<field_name>`. The actual mechanism is
pydantic-settings: when `secrets_dir` is set, it reads every file
under it whose name matches a `Settings` field (case-insensitive) and
treats the file contents as the value.

This test exercises that contract on a tmp dir so we don't need to
mount anything to verify the wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from seedbank.core.config import Settings


def test_jwt_secret_read_from_secrets_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Drop a file whose stem matches the Pydantic field name. Pydantic
    # strips the trailing newline; we keep the value bare to mirror the
    # `printf '%s' ...` recipe in `secrets/README.md`.
    (tmp_path / "jwt_secret").write_text("from-file-secret")

    # Make sure no env var beats the file. `JWT_SECRET` from the host
    # `.env` would otherwise win (env > secrets_dir > defaults).
    monkeypatch.delenv("JWT_SECRET", raising=False)

    # `_secrets_dir` is the documented init-kwarg override in
    # pydantic-settings v2.x. Don't load the host .env so the test is
    # hermetic.
    settings = Settings(_secrets_dir=str(tmp_path), _env_file=None)

    assert settings.jwt_secret.get_secret_value() == "from-file-secret"


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "http://minio:9000", "https://x:9000", "localhost:9000/bucket"],
)
def test_minio_public_endpoint_rejects_malformed(bad: str) -> None:
    """The public endpoint signs browser-facing URLs, so a scheme or path is a
    misconfig that must fail fast instead of minting URLs that 404 at the
    client."""
    with pytest.raises(ValidationError):
        Settings(minio_public_endpoint=bad, _env_file=None)


def test_minio_public_endpoint_accepts_bare_host_and_trims() -> None:
    s = Settings(minio_public_endpoint="minio.example.com:9000", _env_file=None)
    assert s.minio_public_endpoint == "minio.example.com:9000"
    s2 = Settings(minio_public_endpoint="  localhost:9000  ", _env_file=None)
    assert s2.minio_public_endpoint == "localhost:9000"
