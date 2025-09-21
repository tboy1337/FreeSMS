"""
Notification service for SMS application
Provides cross-platform notification functionality
"""
import os
import sys
import platform
import tempfile
from typing import Optional
from pathlib import Path

class NotificationService:
    """Cross-platform notification service"""
    
    def __init__(self, app_name="FreeSMS"):
        """Initialize the notification service"""
        self.app_name = app_name
        self.system = platform.system()
    
    def send_notification(self, title: str, message: str, icon_path: Optional[str] = None):
        """
        Send a system notification
        
        Args:
            title: Notification title
            message: Notification message
            icon_path: Path to notification icon (optional)
        """
        if self.system == "Windows":
            self._send_windows_notification(title, message, icon_path)
        elif self.system == "Darwin":  # macOS
            self._send_macos_notification(title, message, icon_path)
        elif self.system == "Linux":
            self._send_linux_notification(title, message, icon_path)
        else:
            # Fallback to console output
            print(f"{title}: {message}")
    
    def _send_windows_notification(self, title: str, message: str, icon_path: Optional[str] = None):
        """Send a Windows notification using PowerShell"""
        try:
            # Use Windows 10 toast notifications via PowerShell
            powershell_cmd = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $toastXml = [xml]$template
            $toastXml.GetElementsByTagName("text")[0].AppendChild($toastXml.CreateTextNode("{self.app_name}")) > $null
            $toastXml.GetElementsByTagName("text")[1].AppendChild($toastXml.CreateTextNode("{message}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($toastXml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self.app_name}").Show($toast)
            '''
            
            # Save command to temporary file to avoid command line length issues
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1') as temp:
                temp.write(powershell_cmd.encode('utf-8'))
                temp_path = temp.name
            
            # Execute the PowerShell script
            os.system(f'powershell -ExecutionPolicy Bypass -File "{temp_path}"')
            
            # Clean up the temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
        except Exception:
            # Fallback to console output
            print(f"{title}: {message}")
    
    def _send_macos_notification(self, title: str, message: str, icon_path: Optional[str] = None):
        """Send a macOS notification using osascript"""
        try:
            # Escape double quotes in the message
            message = message.replace('"', '\\"')
            title = title.replace('"', '\\"')
            
            # Build the AppleScript command
            apple_script = f'display notification "{message}" with title "{title}"'
            
            # If an app name is provided, add it
            if self.app_name:
                apple_script += f' subtitle "{self.app_name}"'
            
            # Execute the AppleScript
            os.system(f"osascript -e '{apple_script}'")
            
        except Exception:
            # Fallback to console output
            print(f"{title}: {message}")
    
    def _send_linux_notification(self, title: str, message: str, icon_path: Optional[str] = None):
        """Send a Linux notification using notify-send"""
        try:
            # Escape special characters
            message = message.replace('"', '\\"').replace("'", "\\'")
            title = title.replace('"', '\\"').replace("'", "\\'")
            
            # Build the command
            cmd = f'notify-send "{title}" "{message}"'
            
            # Add icon if provided
            if icon_path and os.path.exists(icon_path):
                cmd += f' -i "{icon_path}"'
                
            # Execute the command
            os.system(cmd)
            
        except Exception:
            # Fallback to console output
            print(f"{title}: {message}")

def play_sound(sound_type="notification"):
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
                "success": winsound.MB_ICONASTERISK
            }
            winsound.MessageBeep(sound_map.get(sound_type, winsound.MB_ICONINFORMATION))
            
        elif system == "Darwin":  # macOS
            sound_file = "Ping" if sound_type == "notification" else "Funk"
            os.system(f'afplay /System/Library/Sounds/{sound_file}.aiff')
            
        elif system == "Linux":
            sound_map = {
                "notification": "message-new-instant",
                "error": "dialog-error",
                "success": "message-sent-email"
            }
            sound_name = sound_map.get(sound_type, "message-new-instant")
            os.system(f'canberra-gtk-play -i {sound_name}')
            
    except Exception:
        # Silently fail if sound playing fails
        pass 