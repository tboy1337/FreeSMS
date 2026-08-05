"""Pytest configuration and shared fixtures for FreeSMS tests."""

import gc

import pytest


@pytest.fixture(autouse=True)
def cleanup_qapplication():
    """Destroy any QApplication instance left by GUI tests."""
    yield
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.quit()
            app.deleteLater()
    except (ImportError, RuntimeError, AttributeError):
        pass
    gc.collect()


@pytest.fixture(scope="session", autouse=True)
def mock_keyring() -> None:
    """Provide in-memory keyring for credential encryption tests."""
    key_store: dict[str, str] = {}

    def get_password(service: str, key: str) -> str | None:
        return key_store.get(f"{service}:{key}")

    def set_password(service: str, key: str, value: str) -> None:
        key_store[f"{service}:{key}"] = value

    import keyring

    keyring.get_password = get_password
    keyring.set_password = set_password
