#!/usr/bin/env python3
"""
FreeSMS Application - Main Entry Point
"""
import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import argparse
import logging
from dotenv import load_dotenv

# Add the project root to the Python path if it's not already there
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables from .env file
load_dotenv()

from src.gui.app import SMSApplication
from src.cli.cli import main as cli_main
from src.utils.logger import setup_logger
from src.services.config_service import ConfigService
from src.services.notification_service import NotificationService

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="FreeSMS")
    parser.add_argument("--minimized", action="store_true", help="Start application minimized")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", type=str, help="Path to custom config file")
    parser.add_argument("--cli", action="store_true", help="Run in command line mode")
    
    # Only parse known args to allow for CLI-specific arguments
    args, _ = parser.parse_known_args()
    return args

def main():
    """Main entry point for the FreeSMS application"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger("message_master", log_level)
    logger.info("Starting FreeSMS application")
    
    # If CLI mode is requested, run in CLI mode
    if args.cli:
        logger.info("Running in CLI mode")
        # Remove the --cli flag and call the CLI main function
        if "--cli" in sys.argv:
            sys.argv.remove("--cli")
        return cli_main()
    
    # Otherwise run in GUI mode
    logger.info("Running in GUI mode")
    
    # Initialize services
    config = ConfigService("message_master")
    notification = NotificationService("FreeSMS")
    
    # Get window settings from config
    start_minimized = args.minimized or config.get("general.start_minimized", False)
    
    # Initialize Qt Application
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("FreeSMS")
    qt_app.setApplicationVersion("1.0")
    
    # Set application icon
    try:
        from PySide6.QtGui import QIcon
        icon_path = os.path.join(os.path.dirname(__file__), "gui", "assets", "sms_icon.png")
        if os.path.exists(icon_path):
            qt_app.setWindowIcon(QIcon(icon_path))
    except:
        logger.warning("Failed to set application icon")
    
    # Create the main application window
    main_window = SMSApplication(config=config, notification=notification)
    
    # Show the window unless starting minimized
    if start_minimized:
        main_window.hide()
        notification.send_notification(
            "FreeSMS", 
            "Application started and running in background"
        )
    else:
        main_window.show()
    
    # Start the application event loop
    sys.exit(qt_app.exec())
    
    logger.info("Application shutdown")

if __name__ == "__main__":
    main() 