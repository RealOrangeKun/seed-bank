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

from seedbank.core.config import Settings


def test_jwt_secret_read_from_secrets_dir(tmp_path: Path, monkeypatch) -> None:
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
    settings = Settings(_secrets_dir=str(tmp_path), _env_file=None)  # type: ignore[call-arg]

    assert settings.jwt_secret.get_secret_value() == "from-file-secret"
