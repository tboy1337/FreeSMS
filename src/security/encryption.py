"""
Credential encryption utilities using Fernet and OS keyring.
"""

import json
from typing import Any

import keyring
from cryptography.fernet import Fernet, InvalidToken

from src.utils.logger import get_logger

logger = get_logger("freesms.encryption")

KEYRING_SERVICE = "freesms"
KEYRING_KEY_NAME = "encryption_key"
ENCRYPTED_PREFIX = "enc:"


class CredentialEncryptionError(Exception):
    """Raised when credential encryption or keyring access fails."""


def _get_or_create_key() -> bytes:
    """Load encryption key from keyring or create and store a new one."""
    try:
        if stored := keyring.get_password(KEYRING_SERVICE, KEYRING_KEY_NAME):
            return stored.encode("utf-8")

        key = Fernet.generate_key()
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY_NAME, key.decode("utf-8"))
        logger.info("Generated new encryption key in keyring")
        return key
    except (keyring.errors.KeyringError, OSError) as exc:
        logger.error("Keyring access failed: %s", exc)
        raise CredentialEncryptionError(
            "Unable to access the OS credential store for encryption. "
            "Ensure a keyring backend is available or run in an interactive session."
        ) from exc


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the keyring-backed key."""
    return Fernet(_get_or_create_key())


def encrypt_credentials(credentials: dict[str, Any]) -> str:
    """
    Encrypt a credentials dictionary for database storage.

    Returns a string prefixed with ENCRYPTED_PREFIX followed by Fernet token.
    """
    payload = json.dumps(credentials).encode("utf-8")
    token = _get_fernet().encrypt(payload).decode("utf-8")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_credentials(stored_value: str) -> dict[str, Any] | None:
    """
    Decrypt stored credentials.

    Returns None if decryption fails for non-legacy values.
    """
    if not stored_value:
        return None

    if stored_value.startswith(ENCRYPTED_PREFIX):
        token = stored_value[len(ENCRYPTED_PREFIX) :]
        try:
            decrypted = _get_fernet().decrypt(token.encode("utf-8"))
            result: dict[str, Any] = json.loads(decrypted.decode("utf-8"))
            return result
        except (InvalidToken, json.JSONDecodeError) as exc:
            logger.error("Failed to decrypt credentials: %s", exc)
            return None

    return None


def is_legacy_plaintext(stored_value: str) -> bool:
    """Return True if stored value appears to be legacy plaintext JSON."""
    if stored_value.startswith(ENCRYPTED_PREFIX):
        return False
    try:
        json.loads(stored_value)
        return True
    except json.JSONDecodeError:
        return False


def parse_legacy_credentials(stored_value: str) -> dict[str, Any] | None:
    """Parse legacy plaintext JSON credentials."""
    try:
        result: dict[str, Any] = json.loads(stored_value)
        return result
    except json.JSONDecodeError:
        return None
