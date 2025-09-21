#!/usr/bin/env python3
"""
Test script for FreeSMS services
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.services.config_service import ConfigService
from src.services.notification_service import NotificationService
from src.utils.formatters import format_phone_number, format_delivery_time
from src.utils.logger import setup_logger

class TestConfigService(unittest.TestCase):
    """Test case for Config Service"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for config files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Patch the home directory to use our temp directory
        self.home_patcher = patch('pathlib.Path.home', return_value=Path(self.temp_dir.name))
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

class TestNotificationService(unittest.TestCase):
    """Test case for Notification Service"""
    
    def setUp(self):
        """Set up test environment"""
        # Create notification service
        self.notification = NotificationService("Test App")
    
    @patch('platform.system')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.system')
    def test_windows_notification(self, mock_system, mock_tempfile, mock_platform):
        """Test sending Windows notification"""
        # Set platform to Windows
        mock_platform.return_value = 'Windows'
        
        # Mock the temporary file
        mock_temp = MagicMock()
        mock_temp.name = 'C:\\temp\\test.ps1'
        mock_tempfile.return_value.__enter__.return_value = mock_temp
        
        # Send notification but mock os.system to prevent actual execution
        mock_system.return_value = 0
        self.notification.send_notification("Test Title", "Test Message")
        
        # Verify os.system was called with PowerShell command
        mock_system.assert_called_once()
        cmd = mock_system.call_args[0][0]
        self.assertIn('powershell', cmd)
        self.assertIn(mock_temp.name, cmd)
    
    @patch('platform.system')
    @patch('os.system')
    def test_linux_notification(self, mock_system, mock_platform):
        """Test sending Linux notification on Linux platform"""
        # Set platform to Linux
        mock_platform.return_value = 'Linux'
        
        # Send notification directly 
        self.notification.send_notification("Test Title", "Test Message")
        
        # Verify os.system was called with notify-send
        mock_system.assert_called_once()
    
    @patch('platform.system')
    @patch('os.system')
    def test_macos_notification(self, mock_system, mock_platform):
        """Test sending macOS notification on macOS platform"""
        # Set platform to macOS
        mock_platform.return_value = 'Darwin'
        
        # Send notification directly
        self.notification.send_notification("Test Title", "Test Message")
        
        # Verify os.system was called
        mock_system.assert_called_once()

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