#!/usr/bin/env python3
"""
Test script for FreeSMS notification service
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.services.notification_service import NotificationService, play_sound

class TestNotificationService(unittest.TestCase):
    """Test case for Notification Service"""
    
    def setUp(self):
        """Set up test environment"""
        # Create notification service but patch platform.system to always return 'Test'
        self.platform_patcher = patch('platform.system', return_value='Test')
        self.platform_mock = self.platform_patcher.start()
        
        # Create the notification service with a mocked platform
        self.notification = NotificationService("Test App")
    
    def tearDown(self):
        """Clean up test environment"""
        self.platform_patcher.stop()
    
    def test_init(self):
        """Test notification service initialization"""
        self.assertEqual(self.notification.app_name, "Test App")
        self.assertEqual(self.notification.system, "Test")
    
    @patch('builtins.print')
    def test_fallback_notification(self, mock_print):
        """Test fallback notification (when platform is unknown)"""
        # Send notification (should fall back to print)
        self.notification.send_notification("Test Title", "Test Message")
        
        # Verify print was called
        mock_print.assert_called_once_with("Test Title: Test Message")
    
    @patch('platform.system', return_value='Windows')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.system')
    def test_windows_notification(self, mock_system, mock_tempfile, _):
        """Test Windows notification"""
        # Create a new service with Windows platform
        service = NotificationService("Test App")
        
        # Mock the temporary file
        mock_file = MagicMock()
        mock_file.name = r'C:\temp\test.ps1'
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        # Send notification
        service.send_notification("Test Title", "Test Message")
        
        # Verify os.system was called with PowerShell command
        mock_system.assert_called_once()
        cmd = mock_system.call_args[0][0]
        self.assertIn('powershell', cmd)
        self.assertIn(mock_file.name, cmd)
    
    @patch('platform.system', return_value='Darwin')
    @patch('os.system')
    def test_macos_notification(self, mock_system, _):
        """Test macOS notification"""
        # Create a new service with macOS platform
        service = NotificationService("Test App")
        
        # Send notification
        service.send_notification("Test Title", "Test Message")
        
        # Verify os.system was called with osascript
        mock_system.assert_called_once()
        cmd = mock_system.call_args[0][0]
        self.assertIn('osascript', cmd)
        self.assertIn('display notification', cmd)
    
    @patch('platform.system', return_value='Linux')
    @patch('os.system')
    def test_linux_notification(self, mock_system, _):
        """Test Linux notification"""
        # Create a new service with Linux platform
        service = NotificationService("Test App")
        
        # Send notification
        service.send_notification("Test Title", "Test Message")
        
        # Verify os.system was called with notify-send
        mock_system.assert_called_once()
        cmd = mock_system.call_args[0][0]
        self.assertIn('notify-send', cmd)
    
    @patch('platform.system', return_value='Darwin')
    @patch('os.system')
    def test_macos_sound(self, mock_system, _):
        """Test macOS sound"""
        # Play notification sound on macOS
        play_sound("notification")
        
        # Verify os.system was called with afplay
        mock_system.assert_called_once()
        cmd = mock_system.call_args[0][0]
        self.assertIn('afplay', cmd)
    
    @patch('platform.system', return_value='Linux')
    @patch('os.system')
    def test_linux_sound(self, mock_system, _):
        """Test Linux sound"""
        # Play notification sound on Linux
        play_sound("notification")
        
        # Verify os.system was called with canberra-gtk-play
        mock_system.assert_called_once()
        cmd = mock_system.call_args[0][0]
        self.assertIn('canberra-gtk-play', cmd)
    
    @patch('platform.system', return_value='Unknown')
    def test_unknown_sound(self, _):
        """Test sound on unknown platform"""
        # This should not raise any exceptions
        play_sound("notification")

if __name__ == "__main__":
    unittest.main() 