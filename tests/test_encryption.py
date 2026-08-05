"""Tests for credential encryption utilities."""

import json

from src.security.encryption import (
    ENCRYPTED_PREFIX,
    decrypt_credentials,
    encrypt_credentials,
    is_legacy_plaintext,
    parse_legacy_credentials,
)


def test_encrypt_decrypt_round_trip() -> None:
    """Encrypted credentials should decrypt to the original dict."""
    original = {"account_sid": "sid", "auth_token": "token", "phone_number": "+1"}
    encrypted = encrypt_credentials(original)
    assert encrypted.startswith(ENCRYPTED_PREFIX)
    decrypted = decrypt_credentials(encrypted)
    assert decrypted == original


def test_legacy_plaintext_detection() -> None:
    """Legacy JSON credentials should be detected as plaintext."""
    legacy = json.dumps({"api_key": "test"})
    assert is_legacy_plaintext(legacy)
    assert parse_legacy_credentials(legacy) == {"api_key": "test"}


def test_decrypt_invalid_returns_none() -> None:
    """Invalid encrypted values should return None."""
    assert decrypt_credentials("not-valid-data") is None


def test_decrypt_empty_returns_none() -> None:
    """Empty stored values return None."""
    assert decrypt_credentials("") is None


def test_decrypt_corrupt_encrypted_token_returns_none() -> None:
    """Corrupt encrypted tokens return None."""
    assert decrypt_credentials(f"{ENCRYPTED_PREFIX}not-a-token") is None


def test_is_legacy_plaintext_encrypted_prefix() -> None:
    """Encrypted values are not legacy plaintext."""
    encrypted = encrypt_credentials({"api_key": "test"})
    assert not is_legacy_plaintext(encrypted)


def test_is_legacy_plaintext_invalid_json() -> None:
    """Non-JSON strings are not legacy plaintext."""
    assert not is_legacy_plaintext("plain-text")


def test_parse_legacy_credentials_invalid() -> None:
    """Invalid legacy JSON returns None."""
    assert parse_legacy_credentials("not-json") is None
