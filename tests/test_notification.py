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

from src.services.notification_service import NotificationService, play_sound


class TestNotificationService(unittest.TestCase):
    """Test case for Notification Service"""

    def setUp(self):
        """Set up test environment"""
        self.platform_patcher = patch("platform.system", return_value="Test")
        self.platform_patcher.start()
        self.notification = NotificationService("Test App")

    def tearDown(self):
        """Clean up test environment"""
        self.platform_patcher.stop()

    def test_init(self):
        """Test notification service initialization"""
        self.assertEqual(self.notification.app_name, "Test App")
        self.assertEqual(self.notification.system, "Test")

    @patch.object(NotificationService, "_send_via_plyer", return_value=False)
    @patch("src.services.notification_service.logger")
    def test_fallback_notification(self, mock_logger, _mock_plyer):
        """Test fallback notification (when platform is unknown)"""
        self.notification.send_notification("Test Title", "Test Message")
        mock_logger.info.assert_called()

    @patch("platform.system", return_value="Windows")
    @patch.object(NotificationService, "_send_via_plyer", return_value=False)
    @patch("subprocess.run")
    def test_windows_notification(self, mock_run, _mock_plyer, _):
        """Test Windows notification fallback via subprocess."""
        service = NotificationService("Test App")
        service.send_notification("Test Title", "Test Message")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("powershell", cmd[0])

    @patch("platform.system", return_value="Darwin")
    @patch.object(NotificationService, "_send_via_plyer", return_value=False)
    @patch("subprocess.run")
    def test_macos_notification(self, mock_run, _mock_plyer, _):
        """Test macOS notification fallback via osascript."""
        service = NotificationService("Test App")
        service.send_notification("Test Title", "Test Message")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("osascript", cmd[0])

    @patch("platform.system", return_value="Linux")
    @patch.object(NotificationService, "_send_via_plyer", return_value=False)
    @patch("subprocess.run")
    def test_linux_notification(self, mock_run, _mock_plyer, _):
        """Test Linux notification fallback via notify-send."""
        service = NotificationService("Test App")
        service.send_notification("Test Title", "Test Message")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("notify-send", cmd[0])

    @patch("platform.system", return_value="Darwin")
    @patch("subprocess.run")
    def test_macos_sound(self, mock_run, _):
        """Test macOS sound"""
        play_sound("notification")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("afplay", cmd[0])

    @patch("platform.system", return_value="Linux")
    @patch("subprocess.run")
    def test_linux_sound(self, mock_run, _):
        """Test Linux sound"""
        play_sound("notification")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("canberra-gtk-play", cmd[0])

    @patch("platform.system", return_value="Unknown")
    def test_unknown_sound(self, _):
        """Test sound on unknown platform"""
        play_sound("notification")

    @patch.object(NotificationService, "_send_via_plyer", return_value=True)
    def test_plyer_success_short_circuit(self, _mock_plyer):
        """When plyer succeeds, platform fallbacks are not used."""
        with patch.object(
            NotificationService, "_send_windows_notification"
        ) as mock_windows:
            self.notification.send_notification("Title", "Message")
            mock_windows.assert_not_called()

    @patch.object(NotificationService, "_send_via_plyer", return_value=False)
    @patch("subprocess.run", side_effect=OSError("spawn failed"))
    def test_windows_notification_os_error(self, _mock_run, _mock_plyer):
        """Windows fallback logs when subprocess fails."""
        with patch("platform.system", return_value="Windows"):
            service = NotificationService("Test App")
            service.send_notification("Title", "Message")

    @patch("plyer.notification.notify")
    def test_plyer_with_icon(self, mock_notify):
        """plyer path includes icon when file exists."""
        with patch("os.path.exists", return_value=True):
            service = NotificationService("Test App")
            result = service._send_via_plyer("Title", "Message", "/tmp/icon.png")
            assert result
            mock_notify.assert_called_once()

    @patch("plyer.notification.notify", side_effect=RuntimeError("plyer down"))
    def test_plyer_failure_returns_false(self, _mock_notify):
        """plyer failures return False to trigger fallback."""
        service = NotificationService("Test App")
        assert not service._send_via_plyer("Title", "Message")

    @patch("platform.system", return_value="Linux")
    @patch("subprocess.run", side_effect=OSError("notify failed"))
    def test_linux_notification_os_error(self, _mock_run, _):
        """Linux fallback logs when subprocess fails."""
        service = NotificationService("Test App")
        with patch.object(service, "_send_via_plyer", return_value=False):
            service.send_notification("Title", "Message")

    @patch("platform.system", return_value="Darwin")
    @patch("subprocess.run", side_effect=OSError("osascript failed"))
    def test_macos_notification_os_error(self, _mock_run, _):
        """macOS fallback logs when subprocess fails."""
        service = NotificationService("Test App")
        with patch.object(service, "_send_via_plyer", return_value=False):
            service.send_notification("Title", "Message")

    @patch("platform.system", return_value="Linux")
    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_linux_notification_with_icon(self, mock_run, _mock_exists, _):
        """Linux notifications include icon path when available."""
        service = NotificationService("Test App")
        with patch.object(service, "_send_via_plyer", return_value=False):
            service.send_notification("Title", "Message", "/tmp/icon.png")
        cmd = mock_run.call_args[0][0]
        self.assertIn("-i", cmd)

    @patch("platform.system", return_value="Windows")
    @patch("winsound.MessageBeep")
    def test_windows_sound(self, mock_beep, _):
        """Test Windows sound via winsound."""
        play_sound("error")
        mock_beep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
