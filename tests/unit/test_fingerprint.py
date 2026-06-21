"""Unit tests for device-fingerprint generation in app.crud."""
import hashlib

from app.crud import generate_device_fingerprint


def test_deterministic_for_same_inputs():
    a = generate_device_fingerprint("UA/1.0", "1.2.3.4")
    b = generate_device_fingerprint("UA/1.0", "1.2.3.4")
    assert a == b


def test_differs_for_different_inputs():
    a = generate_device_fingerprint("UA/1.0", "1.2.3.4")
    b = generate_device_fingerprint("UA/2.0", "1.2.3.4")
    c = generate_device_fingerprint("UA/1.0", "9.9.9.9")
    assert a != b
    assert a != c


def test_handles_none_inputs():
    fp = generate_device_fingerprint(None, None)
    assert isinstance(fp, str) and len(fp) == 32  # md5 hexdigest


def test_matches_known_md5():
    expected = hashlib.md5(b"UA/1.0:1.2.3.4").hexdigest()
    assert generate_device_fingerprint("UA/1.0", "1.2.3.4") == expected
