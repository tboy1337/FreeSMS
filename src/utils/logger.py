"""
Logging utilities for SMS application
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.utils.paths import get_log_dir


def setup_logger(
    name: str = "freesms",
    log_level: int = logging.INFO,
    level: int | None = None,
    log_file: str | None = None,
) -> logging.Logger:
    """
    Set up a logger with console and file handlers

    Args:
        name: Logger name (default: "freesms")
        log_level: Logging level (default: logging.INFO)
        level: Alternative parameter name for log_level (for compatibility)
        log_file: Optional specific log file path (overrides default location)

    Returns:
        Configured logger instance
    """
    if level is not None:
        log_level = level

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if logger.handlers:
        return logger

    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(log_level)
        if hasattr(console_handler.stream, "reconfigure"):
            try:
                console_handler.stream.reconfigure(encoding="utf-8")
            except (AttributeError, OSError, ValueError):
                pass
        logger.addHandler(console_handler)
    except OSError as exc:
        print(f"Warning: Could not create console handler: {exc}")

    try:
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            log_dir = get_log_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            log_path = log_dir / f"freesms_{today}.log"

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as exc:
        print(f"Warning: Could not create file handler: {exc}")
    except Exception as exc:
        print(f"Warning: Unexpected error creating file handler: {exc}")

    return logger


def get_logger(name: str = "freesms") -> logging.Logger:
    """
    Get an existing logger or create a new one

    Args:
        name: Logger name (default: "freesms")

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger = setup_logger(name)

    return logger
