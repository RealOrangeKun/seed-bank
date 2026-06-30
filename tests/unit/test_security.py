"""Unit tests for `core.security` — pure crypto helpers, no I/O."""

from __future__ import annotations

import time

import pytest

from seedbank.core.exceptions import AuthError, ValidationError
from seedbank.core.security import (
    JWT_TYPE_ACCESS,
    JWT_TYPE_REFRESH,
    PASSWORD_MIN_LENGTH,
    decode_jwt,
    encode_jwt,
    enforce_password_policy,
    generate_verification_token,
    hash_password,
    issue_access_token,
    issue_refresh_token,
    sha256_hex,
    verify_password,
)

# ── Password hashing ────────────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self) -> None:
        pwd = "Sup3rStrongPwd!!"
        hashed = hash_password(pwd)
        assert hashed != pwd
        assert verify_password(pwd, hashed) is True

    def test_verify_rejects_wrong_password(self) -> None:
        hashed = hash_password("Sup3rStrongPwd!!")
        assert verify_password("WrongPasswordX1", hashed) is False

    def test_verify_handles_malformed_hash(self) -> None:
        assert verify_password("Whatever123ABC", "not-a-valid-hash") is False


class TestPasswordPolicy:
    def test_too_short_rejected(self) -> None:
        with pytest.raises(ValidationError):
            enforce_password_policy("Aa1" * 3)  # 9 chars

    def test_minimum_length_constant(self) -> None:
        assert PASSWORD_MIN_LENGTH == 12

    def test_requires_lowercase(self) -> None:
        with pytest.raises(ValidationError):
            enforce_password_policy("ABCDEFGHIJ12")

    def test_requires_uppercase(self) -> None:
        with pytest.raises(ValidationError):
            enforce_password_policy("abcdefghij12")

    def test_requires_digit(self) -> None:
        with pytest.raises(ValidationError):
            enforce_password_policy("AbcdefghijKL")

    def test_strong_password_accepted(self) -> None:
        enforce_password_policy("CorrectHorseBattery1")  # no exception


# ── JWT ──────────────────────────────────────────────────────────────────────


class TestJWT:
    def test_encode_decode_roundtrip(self) -> None:
        token = encode_jwt(
            subject="abc-123",
            token_type=JWT_TYPE_ACCESS,
            expires_in_seconds=60,
            extra_claims={"role": "admin"},
        )
        payload = decode_jwt(token, expected_type=JWT_TYPE_ACCESS)
        assert payload["sub"] == "abc-123"
        assert payload["role"] == "admin"
        assert payload["type"] == JWT_TYPE_ACCESS

    def test_expected_type_mismatch_rejected(self) -> None:
        token = issue_access_token(subject="u1", role="end_user")
        with pytest.raises(AuthError):
            decode_jwt(token, expected_type=JWT_TYPE_REFRESH)

    def test_tampered_token_rejected(self) -> None:
        token = issue_access_token(subject="u1", role="end_user")
        # Flip a character in the signature.
        tampered = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
        with pytest.raises(AuthError):
            decode_jwt(tampered)

    def test_expired_token_rejected(self) -> None:
        token = encode_jwt(
            subject="u1",
            token_type=JWT_TYPE_ACCESS,
            expires_in_seconds=-1,
        )
        # Give clock-skew leeway zero by sleeping 1 second.
        time.sleep(0.1)
        with pytest.raises(AuthError):
            decode_jwt(token)

    def test_refresh_token_returns_expiry(self) -> None:
        token, expires_at = issue_refresh_token(subject="u1")
        payload = decode_jwt(token, expected_type=JWT_TYPE_REFRESH)
        assert payload["sub"] == "u1"
        assert expires_at.tzinfo is not None


# ── Verification tokens ──────────────────────────────────────────────────────


class TestVerificationToken:
    def test_returns_plaintext_and_hash(self) -> None:
        plaintext, h = generate_verification_token()
        assert plaintext
        assert h == sha256_hex(plaintext)
