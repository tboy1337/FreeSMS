#!/usr/bin/env python3
"""
Test script for FreeSMS services
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.services.config_service import ConfigService
from src.services.notification_service import NotificationService
from src.utils.formatters import format_delivery_time, format_phone_number
from src.utils.logger import setup_logger


class TestConfigService(unittest.TestCase):
    """Test case for Config Service"""

    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for config files
        self.temp_dir = tempfile.TemporaryDirectory()

        # Patch the home directory to use our temp directory
        self.home_patcher = patch(
            "pathlib.Path.home", return_value=Path(self.temp_dir.name)
        )
        self.mock_home = self.home_patcher.start()

        # Create config service
        self.config = ConfigService("test_app")

    def tearDown(self):
        """Clean up test environment"""
        # Stop the patchers
        self.home_patcher.stop()

        # Clean up temp directory
        self.temp_dir.cleanup()

    def test_default_settings(self):
        """Test default settings"""
        # Check default settings
        self.assertEqual(self.config.get("general.start_minimized"), False)
        self.assertEqual(self.config.get("ui.window_width"), 900)
        self.assertEqual(self.config.get("ui.window_height"), 700)

    def test_set_get(self):
        """Test setting and getting values"""
        # Set a value
        self.config.set("test.key", "test_value")

        # Get the value
        value = self.config.get("test.key")
        self.assertEqual(value, "test_value")

        # Set nested values
        self.config.set("test.nested.key1", 123)
        self.config.set("test.nested.key2", True)

        # Get nested values
        self.assertEqual(self.config.get("test.nested.key1"), 123)
        self.assertEqual(self.config.get("test.nested.key2"), True)

        # Get with default
        self.assertEqual(self.config.get("nonexistent", "default"), "default")

    def test_save_load(self):
        """Test saving and loading config"""
        # Set some values
        self.config.set("test.key1", "value1")
        self.config.set("test.key2", 42)

        # Save config
        self.config.save()

        # Create a new config service
        new_config = ConfigService("test_app")

        # Check if values were loaded
        self.assertEqual(new_config.get("test.key1"), "value1")
        self.assertEqual(new_config.get("test.key2"), 42)

    def test_reset(self):
        """Test resetting config to defaults"""
        # Set some values
        self.config.set("ui.window_width", 1200)
        self.config.set("general.start_minimized", True)

        # Reset all settings
        self.config.reset()

        # Check if values were reset
        self.assertEqual(self.config.get("ui.window_width"), 900)
        self.assertEqual(self.config.get("general.start_minimized"), False)

    def test_custom_config_path(self):
        """Custom config path is honored."""
        custom_path = Path(self.temp_dir.name) / "custom.json"
        config = ConfigService("test_app", config_path=str(custom_path))
        config.set("custom.key", "value")
        config.save()
        assert custom_path.exists()

    def test_corrupt_config_file(self):
        """Corrupt JSON config files are replaced with defaults."""
        self.config.config_file.write_text("{bad json", encoding="utf-8")
        reloaded = ConfigService("test_app")
        self.assertEqual(reloaded.get("ui.window_width"), 900)

    def test_save_os_error(self):
        """Save failures return False when the file cannot be written."""
        with patch("builtins.open", side_effect=OSError("denied")):
            self.assertFalse(self.config.save())

    def test_reset_invalid_section(self):
        """Resetting an unknown section returns False."""
        self.assertFalse(self.config.reset("nonexistent_section"))

    def test_get_all(self):
        """get_all returns a copy of settings."""
        self.config.set("test.key", "value")
        all_settings = self.config.get_all()
        self.assertEqual(all_settings["test"]["key"], "value")
        all_settings["test"]["key"] = "changed"
        self.assertEqual(self.config.get("test.key"), "value")

    """Test case for Notification Service"""

    @patch("platform.system")
    @patch.object(NotificationService, "_send_via_plyer", return_value=False)
    @patch("subprocess.run")
    def test_windows_notification(self, mock_run, _mock_plyer, mock_platform):
        """Test sending Windows notification"""
        mock_platform.return_value = "Windows"
        notification = NotificationService("Test App")
        notification.send_notification("Test Title", "Test Message")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("powershell", cmd[0])

    @patch("platform.system")
    @patch.object(NotificationService, "_send_via_plyer", return_value=False)
    @patch("subprocess.run")
    def test_linux_notification(self, mock_run, _mock_plyer, mock_platform):
        """Test sending Linux notification on Linux platform"""
        mock_platform.return_value = "Linux"
        notification = NotificationService("Test App")
        notification.send_notification("Test Title", "Test Message")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("notify-send", cmd[0])

    @patch("platform.system")
    @patch.object(NotificationService, "_send_via_plyer", return_value=False)
    @patch("subprocess.run")
    def test_macos_notification(self, mock_run, _mock_plyer, mock_platform):
        """Test sending macOS notification on macOS platform"""
        mock_platform.return_value = "Darwin"
        notification = NotificationService("Test App")
        notification.send_notification("Test Title", "Test Message")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("osascript", cmd[0])


class TestUtils(unittest.TestCase):
    """Test case for utility functions"""

    def test_format_phone_number(self):
        """Test phone number formatting"""
        # Test with valid US number (using real function)
        success, formatted = format_phone_number("+12125551234")
        self.assertTrue(success)
        self.assertEqual(formatted, "+12125551234")

        # Test with invalid input directly (no mocking)
        success, formatted = format_phone_number("invalid")
        self.assertFalse(success)
        self.assertIsNone(formatted)

    def test_format_delivery_time(self):
        """Test delivery time formatting"""
        # Test with valid timestamp
        formatted = format_delivery_time("2023-01-01 12:30:45")
        self.assertEqual(formatted, "2023-01-01 12:30")

        # Test with invalid timestamp
        formatted = format_delivery_time("invalid")
        self.assertEqual(formatted, "invalid")

        # Test with None
        formatted = format_delivery_time(None)
        self.assertEqual(formatted, "N/A")

    def test_logger_setup(self):
        """Test logger setup"""
        # Set up logger
        logger = setup_logger("test_logger")

        # Check logger properties
        self.assertEqual(logger.name, "test_logger")

        # Set up logger with debug level
        import logging

        debug_logger = setup_logger("debug_logger", logging.DEBUG)

        # Check logger level
        self.assertEqual(debug_logger.level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
