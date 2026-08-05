"""
Notification service for SMS application
Provides cross-platform notification functionality
"""

import logging
import os
import platform
import subprocess
from typing import Optional

from src.security.validation import InputValidator
from src.utils.logger import get_logger

logger = get_logger("freesms.notifications")


class NotificationService:
    """Cross-platform notification service"""

    def __init__(self, app_name: str = "FreeSMS") -> None:
        """Initialize the notification service"""
        self.app_name = app_name
        self.system = platform.system()

    def send_notification(
        self,
        title: str,
        message: str,
        icon_path: Optional[str] = None,
    ) -> None:
        """
        Send a system notification

        Args:
            title: Notification title
            message: Notification message
            icon_path: Path to notification icon (optional)
        """
        safe_title = InputValidator.sanitize_text(title)
        safe_message = InputValidator.sanitize_text(message)

        if self._send_via_plyer(safe_title, safe_message, icon_path):
            return

        if self.system == "Windows":
            self._send_windows_notification(safe_title, safe_message, icon_path)
        elif self.system == "Darwin":
            self._send_macos_notification(safe_title, safe_message, icon_path)
        elif self.system == "Linux":
            self._send_linux_notification(safe_title, safe_message, icon_path)
        else:
            logger.info("%s: %s", safe_title, safe_message)

    def _send_via_plyer(
        self,
        title: str,
        message: str,
        icon_path: Optional[str] = None,
    ) -> bool:
        """Send notification using plyer when available."""
        try:
            from plyer import notification

            kwargs: dict[str, str] = {
                "title": title,
                "message": message,
                "app_name": self.app_name,
            }
            if icon_path and os.path.exists(icon_path):
                kwargs["app_icon"] = icon_path

            notification.notify(**kwargs)
            logger.debug("Notification sent via plyer: %s", title)
            return True
        except Exception as exc:
            logger.warning("plyer notification failed, using fallback: %s", exc)
            return False

    def _send_windows_notification(
        self,
        title: str,
        message: str,
        icon_path: Optional[str] = None,
    ) -> None:
        """Send a Windows notification using PowerShell with argument list."""
        try:
            powershell_cmd = (
                "[Windows.UI.Notifications.ToastNotificationManager, "
                "Windows.UI.Notifications, ContentType=WindowsRuntime] > $null; "
                "$template = "
                "[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                "$toastXml = [xml]$template; "
                "$toastXml.GetElementsByTagName('text')[0].AppendChild("
                "$toastXml.CreateTextNode($args[0])) > $null; "
                "$toastXml.GetElementsByTagName('text')[1].AppendChild("
                "$toastXml.CreateTextNode($args[1])) > $null; "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($toastXml); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
                "$args[2]).Show($toast)"
            )
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    powershell_cmd,
                    self.app_name,
                    message,
                    self.app_name,
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Windows notification fallback failed: %s", exc)
            logger.info("%s: %s", title, message)

    def _escape_applescript(self, value: str) -> str:
        """Escape a string for safe inclusion in AppleScript."""
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _send_macos_notification(
        self,
        title: str,
        message: str,
        icon_path: Optional[str] = None,
    ) -> None:
        """Send a macOS notification using osascript."""
        try:
            safe_title = self._escape_applescript(title)
            safe_message = self._escape_applescript(message)
            safe_app = self._escape_applescript(self.app_name)
            apple_script = (
                f'display notification "{safe_message}" with title "{safe_title}" '
                f'subtitle "{safe_app}"'
            )
            subprocess.run(
                ["osascript", "-e", apple_script],
                check=False,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("macOS notification fallback failed: %s", exc)
            logger.info("%s: %s", title, message)

    def _send_linux_notification(
        self,
        title: str,
        message: str,
        icon_path: Optional[str] = None,
    ) -> None:
        """Send a Linux notification using notify-send with argument list."""
        try:
            cmd = ["notify-send", title, message]
            if icon_path and os.path.exists(icon_path):
                cmd.extend(["-i", icon_path])
            subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Linux notification fallback failed: %s", exc)
            logger.info("%s: %s", title, message)


def play_sound(sound_type: str = "notification") -> None:
    """
    Play a system sound

    Args:
        sound_type: Type of sound to play ("notification", "error", "success")
    """
    system = platform.system()

    try:
        if system == "Windows":
            import winsound

            sound_map = {
                "notification": winsound.MB_ICONINFORMATION,
                "error": winsound.MB_ICONERROR,
                "success": winsound.MB_ICONASTERISK,
            }
            winsound.MessageBeep(sound_map.get(sound_type, winsound.MB_ICONINFORMATION))

        elif system == "Darwin":
            sound_file = "Ping" if sound_type == "notification" else "Funk"
            sound_path = f"/System/Library/Sounds/{sound_file}.aiff"
            subprocess.run(
                ["afplay", sound_path],
                check=False,
                capture_output=True,
                timeout=10,
            )

        elif system == "Linux":
            sound_map = {
                "notification": "message-new-instant",
                "error": "dialog-error",
                "success": "message-sent-email",
            }
            sound_name = sound_map.get(sound_type, "message-new-instant")
            subprocess.run(
                ["canberra-gtk-play", "-i", sound_name],
                check=False,
                capture_output=True,
                timeout=10,
            )

    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("Sound playback failed: %s", exc)
