#!/usr/bin/env python3
"""
FreeSMS Application - Main Entry Point
"""

import argparse
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

# Add the project root to the Python path if it's not already there
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

from src.cli.cli import main as cli_main
from src.gui.app import SMSApplication
from src.services.config_service import ConfigService
from src.services.notification_service import NotificationService
from src.utils.logger import setup_logger
from src.utils.paths import get_log_dir, migrate_legacy_data


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="FreeSMS")
    parser.add_argument(
        "--minimized", action="store_true", help="Start application minimized"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", type=str, help="Path to custom config file")
    parser.add_argument("--cli", action="store_true", help="Run in command line mode")

    args, _ = parser.parse_known_args()
    return args


def main() -> int | None:
    """Main entry point for the FreeSMS application"""
    migrate_legacy_data()

    args = parse_arguments()

    log_level = logging.DEBUG if args.debug else logging.INFO
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"freesms_{today}.log"
    logger = setup_logger("freesms", log_level, log_file=str(log_file))
    logger.info("Starting FreeSMS application")

    if args.cli:
        logger.info("Running in CLI mode")
        if "--cli" in sys.argv:
            sys.argv.remove("--cli")
        return cli_main()

    logger.info("Running in GUI mode")

    config = ConfigService("freesms", config_path=args.config)
    notification = NotificationService("FreeSMS")

    start_minimized = args.minimized or config.get("general.start_minimized", False)

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("FreeSMS")
    qt_app.setApplicationVersion("1.0")

    try:
        from PySide6.QtGui import QIcon

        icon_path = os.path.join(
            os.path.dirname(__file__), "gui", "assets", "sms_icon.png"
        )
        if os.path.exists(icon_path):
            qt_app.setWindowIcon(QIcon(icon_path))
    except (ImportError, OSError, RuntimeError) as exc:
        logger.warning("Failed to set application icon: %s", exc)

    main_window = SMSApplication(config=config, notification=notification)

    if start_minimized:
        main_window.hide()
        notification.send_notification(
            "FreeSMS",
            "Application started and running in background",
        )
    else:
        main_window.show()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
