"""
System Tray module for SMS application using PySide6
Provides cross-platform system tray functionality
"""
import os
from pathlib import Path
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon, QAction

class SystemTrayIcon(QObject):
    """PySide6 system tray icon implementation"""
    
    # Signals
    show_requested = Signal()
    new_message_requested = Signal()
    exit_requested = Signal()
    
    def __init__(self, app, icon_path=None, tooltip="FreeSMS"):
        """
        Initialize the system tray icon
        
        Args:
            app: Main application instance
            icon_path: Path to icon file
            tooltip: Tooltip text for the tray icon
        """
        super().__init__()
        self.app = app
        self.icon_path = icon_path
        self.tooltip = tooltip
        self.tray_icon = None
        
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray is not available on this system.")
            return
        
        self._init_tray()
    
    def _init_tray(self):
        """Initialize the system tray"""
        try:
            # Load icon
            icon = self._load_icon()
            
            # Create tray icon
            self.tray_icon = QSystemTrayIcon(icon, self.app)
            self.tray_icon.setToolTip(self.tooltip)
            
            # Create context menu
            self._create_menu()
            
            # Connect signals
            self.show_requested.connect(self._on_show_window)
            self.new_message_requested.connect(self._on_new_message)
            self.exit_requested.connect(self._on_exit)
            
            # Show the tray icon
            self.tray_icon.show()
            
        except Exception as e:
            print(f"Failed to initialize system tray: {e}")
    
    def _load_icon(self):
        """Load icon for the tray"""
        # Try to load the provided icon path
        if self.icon_path and os.path.exists(self.icon_path):
            return QIcon(self.icon_path)
        
        # Try default icon path
        default_path = self._get_default_icon_path()
        if default_path and os.path.exists(default_path):
            return QIcon(default_path)
        
        # Use default system icon if no custom icon is available
        return self.app.style().standardIcon(self.app.style().StandardPixmap.SP_ComputerIcon)
    
    def _get_default_icon_path(self):
        """Get default icon path"""
        script_dir = Path(__file__).parent
        
        # Try PNG first
        png_path = script_dir / "assets" / "sms_icon.png"
        if png_path.exists():
            return str(png_path)
        
        # Try ICO
        ico_path = script_dir / "assets" / "sms_icon.ico"
        if ico_path.exists():
            return str(ico_path)
        
        return None
    
    def _create_menu(self):
        """Create the context menu"""
        menu = QMenu()
        
        # Show action
        show_action = QAction("Show", self.app)
        show_action.triggered.connect(lambda: self.show_requested.emit())
        menu.addAction(show_action)
        
        # Send Message action
        message_action = QAction("Send Message", self.app)
        message_action.triggered.connect(lambda: self.new_message_requested.emit())
        menu.addAction(message_action)
        
        # Separator
        menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self.app)
        exit_action.triggered.connect(lambda: self.exit_requested.emit())
        menu.addAction(exit_action)
        
        # Set the menu
        self.tray_icon.setContextMenu(menu)
    
    def _on_show_window(self):
        """Show the main application window"""
        if hasattr(self.app, 'show'):
            self.app.show()
            self.app.raise_()
            self.app.activateWindow()
    
    def _on_new_message(self):
        """Open new message tab"""
        if hasattr(self.app, 'show') and hasattr(self.app, 'tab_widget'):
            self.app.show()
            self.app.tab_widget.setCurrentIndex(0)  # Select message tab
            self.app.raise_()
            self.app.activateWindow()
    
    def _on_exit(self):
        """Exit the application"""
        if hasattr(self.app, 'close'):
            self.app.close()
    
    def show_message(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information, timeout=5000):
        """Show a system tray message"""
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon, timeout)
    
    def is_visible(self):
        """Check if the tray icon is visible"""
        return self.tray_icon and self.tray_icon.isVisible()
    
    def shutdown(self):
        """Shutdown the tray icon"""
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None