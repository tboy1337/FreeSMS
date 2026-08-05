"""Tests for application path utilities and legacy migration."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.paths import (
    APP_NAME,
    get_app_dir,
    get_config_path,
    get_db_path,
    get_log_dir,
    migrate_legacy_data,
)


@pytest.fixture
def temp_home(tmp_path):
    """Use an isolated home directory for path tests."""
    with patch.object(Path, "home", return_value=tmp_path):
        yield tmp_path


def test_get_app_dir(temp_home):
    """Canonical app directory is ~/.freesms/."""
    assert get_app_dir() == temp_home / f".{APP_NAME}"


def test_get_config_path(temp_home):
    """Config path resolves under the app directory."""
    assert get_config_path() == temp_home / f".{APP_NAME}" / "config.json"


def test_get_db_path(temp_home):
    """Database path resolves under the app directory."""
    assert get_db_path() == temp_home / f".{APP_NAME}" / "freesms.db"


def test_get_log_dir(temp_home):
    """Log directory resolves under the app directory."""
    assert get_log_dir() == temp_home / f".{APP_NAME}" / "logs"


def test_migrate_legacy_data_skips_when_target_populated(temp_home):
    """Migration does not run when ~/.freesms/ already has data."""
    target = get_app_dir()
    target.mkdir(parents=True)
    (target / "existing.txt").write_text("data", encoding="utf-8")

    legacy = temp_home / ".sms_sender"
    legacy.mkdir()
    (legacy / "config.json").write_text("{}", encoding="utf-8")

    migrate_legacy_data()
    assert not (target / "config.json").exists()


def test_migrate_legacy_data_copies_legacy_files(temp_home):
    """Migration copies files from legacy directories when target is empty."""
    legacy = temp_home / ".sms_sender"
    legacy.mkdir()
    (legacy / "config.json").write_text('{"general": {}}', encoding="utf-8")

    migrate_legacy_data()

    target = get_app_dir()
    assert (target / "config.json").read_text(encoding="utf-8") == '{"general": {}}'


def test_migrate_legacy_data_copies_legacy_database(temp_home):
    """Migration maps legacy SQLite files to freesms.db."""
    legacy = temp_home / ".message_master"
    legacy.mkdir()
    legacy_db = legacy / "message_master.db"
    legacy_db.write_bytes(b"sqlite-db-content")

    migrate_legacy_data()

    freesms_db = get_db_path()
    assert freesms_db.exists()
    assert freesms_db.read_bytes() == b"sqlite-db-content"


def test_migrate_legacy_data_copies_legacy_subdirectory(temp_home):
    """Migration copies legacy subdirectories via copytree."""
    legacy = temp_home / ".sms_sender"
    subdir = legacy / "logs"
    subdir.mkdir(parents=True)
    (subdir / "app.log").write_text("log line", encoding="utf-8")

    migrate_legacy_data()

    target = get_app_dir()
    assert (target / "logs" / "app.log").read_text(encoding="utf-8") == "log line"


def test_migrate_legacy_data_skips_existing_dest_items(temp_home):
    """Migration does not overwrite files that already exist in target."""
    legacy = temp_home / ".sms_sender"
    legacy.mkdir()
    (legacy / "config.json").write_text('{"legacy": true}', encoding="utf-8")

    target = get_app_dir()
    target.mkdir(parents=True)
    (target / "config.json").write_text('{"existing": true}', encoding="utf-8")

    migrate_legacy_data()
    assert (target / "config.json").read_text(encoding="utf-8") == '{"existing": true}'


def test_migrate_legacy_data_skips_duplicate_items_across_legacy_dirs(temp_home):
    """Second legacy directory does not overwrite files copied from the first."""
    first_legacy = temp_home / ".sms_sender"
    first_legacy.mkdir()
    (first_legacy / "shared.txt").write_text("from-sms-sender", encoding="utf-8")

    second_legacy = temp_home / ".message_master"
    second_legacy.mkdir()
    (second_legacy / "shared.txt").write_text("from-message-master", encoding="utf-8")

    migrate_legacy_data()

    target = get_app_dir()
    assert (target / "shared.txt").read_text(encoding="utf-8") == "from-sms-sender"
