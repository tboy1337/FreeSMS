"""
Application path utilities and legacy data migration.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger("freesms.paths")

APP_NAME = "freesms"
LEGACY_DIRS = ("sms_sender", "message_master")


def get_app_dir() -> Path:
    """Return the canonical application data directory."""
    return Path.home() / f".{APP_NAME}"


def get_config_path() -> Path:
    """Return path to config.json."""
    return get_app_dir() / "config.json"


def get_db_path() -> Path:
    """Return path to the SQLite database."""
    return get_app_dir() / "freesms.db"


def get_log_dir() -> Path:
    """Return path to the log directory."""
    return get_app_dir() / "logs"


def migrate_legacy_data() -> None:
    """
    Copy data from legacy app directories into ~/.freesms/ if the new dir is empty.
    """
    target = get_app_dir()
    if target.exists() and any(target.iterdir()):
        return

    target.mkdir(parents=True, exist_ok=True)

    for legacy_name in LEGACY_DIRS:
        legacy_dir = Path.home() / f".{legacy_name}"
        if not legacy_dir.exists():
            continue

        logger.info("Migrating legacy data from %s to %s", legacy_dir, target)
        for item in legacy_dir.iterdir():
            dest = target / item.name
            if dest.exists():
                continue
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Map legacy database filenames to freesms.db
        legacy_db_names = ("sms_sender.db", "message_master.db")
        for db_name in legacy_db_names:
            legacy_db = legacy_dir / db_name
            freesms_db = target / "freesms.db"
            if legacy_db.exists() and not freesms_db.exists():
                shutil.copy2(legacy_db, freesms_db)
                logger.info("Migrated database from %s", legacy_db)
