"""
Main FreeSMS Application GUI
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QFrame, QPushButton, QApplication, QMessageBox,
    QFileDialog, QStatusBar
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
import threading
import time
from datetime import datetime
import pycountry
import os

from src.models.database import Database
from src.api.service_manager import SMSServiceManager
from src.models.contact_manager import ContactManager
from src.automation.scheduler import MessageScheduler
from src.security.validation import InputValidator
from src.gui.message_tab import MessageTab
from src.gui.contact_tab import ContactTab
from src.gui.history_tab import HistoryTab
from src.gui.schedule_tab import ScheduleTab
from src.gui.settings_tab import SettingsTab
from src.gui.templates_tab import TemplatesTab

class SMSApplication(QMainWindow):
    """Main FreeSMS Application"""
    
    def __init__(self, config=None, notification=None):
        """Initialize the application"""
        super().__init__()
        self.setWindowTitle("FreeSMS")
        
        # Save references to services
        self.config = config
        self.notification = notification
        
        # Set app icon if available
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "sms_icon.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass  # Icon not found, continue without it
        
        # Configure the application
        self._configure_app()
        
        # Create components
        self._create_components()
        
        # Initialize services
        self._initialize_services()
        
        # Create tabs
        self._create_tabs()
        
        # Set up event bindings
        self._setup_bindings()
        
        # Start background threads
        self._start_background_tasks()
    
    def _configure_app(self):
        """Configure the application"""
        # Set window properties
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Set stylesheet for styling
        self.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QLabel {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
        }
        QLabel[class="header"] {
            font-size: 14pt;
            font-weight: bold;
        }
        QLabel[class="title"] {
            font-size: 12pt;
            font-weight: bold;
        }
        QLabel[class="status"] {
            font-size: 9pt;
        }
        QPushButton {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
            padding: 5px 10px;
        }
        QPushButton[class="primary"] {
            background-color: #4a6cd4;
            color: white;
            border: none;
            border-radius: 3px;
        }
        QPushButton[class="primary"]:hover {
            background-color: #3a5cc4;
        }
        """)
    
    def _create_components(self):
        """Create main application components"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create header
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        header_label = QLabel("FreeSMS")
        header_label.setProperty("class", "header")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        main_layout.addWidget(header_frame)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setProperty("class", "status")
        self.status_bar.addWidget(self.status_label)
        
        self.service_status_label = QLabel("No SMS service configured")
        self.service_status_label.setProperty("class", "status")
        self.status_bar.addPermanentWidget(self.service_status_label)
    
    def _initialize_services(self):
        """Initialize application services"""
        # Database connection
        self.db = Database()
        
        # SMS service manager
        self.service_manager = SMSServiceManager(self.db)
        
        # Contact manager
        self.contact_manager = ContactManager(self.db)
        
        # Message scheduler
        self.scheduler = MessageScheduler(self.db, self.service_manager)
        
        # Input validator
        self.validator = InputValidator()
        
        # Start the scheduler
        self.scheduler.start()
        
        # Register scheduler callbacks
        self.scheduler.register_callback('message_sent', self._on_scheduled_message_sent)
        self.scheduler.register_callback('message_failed', self._on_scheduled_message_failed)
    
    def _create_tabs(self):
        """Create application tabs"""
        self.tabs = {}
        
        # Message Tab
        self.tabs["message"] = MessageTab(self)
        self.tab_widget.addTab(self.tabs["message"], "Send Message")
        
        # Contacts Tab
        self.tabs["contacts"] = ContactTab(self)
        self.tab_widget.addTab(self.tabs["contacts"], "Contacts")
        
        # History Tab
        self.tabs["history"] = HistoryTab(self)
        self.tab_widget.addTab(self.tabs["history"], "Message History")
        
        # Schedule Tab
        self.tabs["schedule"] = ScheduleTab(self)
        self.tab_widget.addTab(self.tabs["schedule"], "Scheduler")
        
        # Templates Tab
        self.tabs["templates"] = TemplatesTab(self)
        self.tab_widget.addTab(self.tabs["templates"], "Templates")
        
        # Settings Tab
        self.tabs["settings"] = SettingsTab(self)
        self.tab_widget.addTab(self.tabs["settings"], "Settings")
    
    def _setup_bindings(self):
        """Set up event bindings"""
        # Bind tab change event
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _start_background_tasks(self):
        """Start background tasks"""
        # Start status updater
        self.status_update_thread = threading.Thread(target=self._update_status_periodically)
        self.status_update_thread.daemon = True
        self.status_update_thread.start()
        
        # Initialize system tray if available
        try:
            from src.gui.systemtray import SystemTrayIcon
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "FreeSMS_icon.ico")
            self.tray_icon = SystemTrayIcon(self, icon_path=icon_path)
        except ImportError:
            # System tray functionality not available
            self.tray_icon = None
    
    def _update_status_periodically(self):
        """Update status information periodically"""
        while True:
            try:
                self._update_service_status()
                time.sleep(5)  # Update every 5 seconds
            except:
                # Ignore errors in background thread
                pass
    
    def _update_service_status(self):
        """Update the SMS service status display"""
        if not self.service_manager.active_service:
            service_text = "No SMS service configured"
        else:
            service = self.service_manager.active_service
            quota = service.get_remaining_quota()
            service_text = f"Service: {service.service_name} | Remaining: {quota}/{service.daily_limit}"
            
        # Update the service status label
        self.service_status_label.setText(service_text)
    
    def _on_tab_changed(self, index):
        """Handle tab changed event"""
        current_tab_text = self.tab_widget.tabText(index)
        
        # Refresh data when switching to certain tabs
        if current_tab_text == "Message History":
            self.tabs["history"].load_history()
        elif current_tab_text == "Contacts":
            self.tabs["contacts"].load_contacts()
        elif current_tab_text == "Scheduler":
            self.tabs["schedule"].load_scheduled_messages()
        elif current_tab_text == "Templates":
            self.tabs["templates"].load_templates()
    
    def _on_scheduled_message_sent(self, data):
        """Handle scheduled message sent event"""
        # Update the UI (Qt handles thread safety automatically)
        self._update_after_scheduled_send(data)
    
    def _update_after_scheduled_send(self, data):
        """Update UI after scheduled message is sent"""
        self.set_status(f"Scheduled message to {data['recipient']} sent successfully")
        
        # Refresh relevant tabs if they're currently visible
        current_index = self.tab_widget.currentIndex()
        current_tab_text = self.tab_widget.tabText(current_index)
        if current_tab_text == "Message History":
            self.tabs["history"].load_history()
        elif current_tab_text == "Scheduler":
            self.tabs["schedule"].load_scheduled_messages()
    
    def _on_scheduled_message_failed(self, data):
        """Handle scheduled message failed event"""
        # Update the UI (Qt handles thread safety automatically)
        self._update_after_scheduled_failure(data)
    
    def _update_after_scheduled_failure(self, data):
        """Update UI after scheduled message fails"""
        self.set_status(f"Failed to send scheduled message to {data['recipient']}: {data.get('error', 'Unknown error')}")
        
        # Refresh scheduler tab if visible
        current_index = self.tab_widget.currentIndex()
        current_tab_text = self.tab_widget.tabText(current_index)
        if current_tab_text == "Scheduler":
            self.tabs["schedule"].load_scheduled_messages()
    
    def send_message(self, recipient, message, service_name=None):
        """Send an SMS message"""
        # Validate inputs
        valid_phone, phone_error = self.validator.validate_phone_input(recipient)
        if not valid_phone:
            QMessageBox.critical(self, "Invalid Phone Number", phone_error)
            return False
            
        valid_msg, msg_error = self.validator.validate_message(message)
        if not valid_msg:
            QMessageBox.critical(self, "Invalid Message", msg_error)
            return False
        
        # Send in a background thread to avoid blocking UI
        threading.Thread(
            target=self._send_message_thread,
            args=(recipient, message, service_name)
        ).start()
        
        return True
    
    def _send_message_thread(self, recipient, message, service_name):
        """Send message in a background thread"""
        try:
            # Update status
            self.set_status(f"Sending message to {recipient}...")
            
            # Send the message
            response = self.service_manager.send_sms(recipient, message, service_name)
            
            # Handle the response (Qt handles thread safety automatically)
            self._handle_send_response(response, recipient)
            
        except Exception as e:
            # Handle errors (Qt handles thread safety automatically)
            self._handle_send_error(str(e), recipient)
    
    def _handle_send_response(self, response, recipient):
        """Handle send message response"""
        if response.success:
            self.set_status(f"Message sent successfully to {recipient}")
            QMessageBox.information(self, "Success", f"Message sent successfully to {recipient}")
            
            # Refresh history tab if it's visible
            current_index = self.tab_widget.currentIndex()
            current_tab_text = self.tab_widget.tabText(current_index)
            if current_tab_text == "Message History":
                self.tabs["history"].load_history()
                
        else:
            self.set_status(f"Failed to send message: {response.error}")
            QMessageBox.critical(self, "Error", f"Failed to send message: {response.error}")
            
        # Update service status
        self._update_service_status()
    
    def _handle_send_error(self, error, recipient):
        """Handle send message error"""
        self.set_status(f"Error sending message to {recipient}")
        QMessageBox.critical(self, "Error", f"Error sending message: {error}")
    
    def set_status(self, message):
        """Set the status bar message"""
        self.status_label.setText(message)
    
    def load_contact_to_message(self, contact_id):
        """Load a contact into the message tab"""
        contact = self.contact_manager.get_contact(contact_id)
        if contact:
            # Switch to message tab
            self.tab_widget.setCurrentIndex(0)
            
            # Set recipient
            self.tabs["message"].set_recipient(contact["phone"])
    
    def closeEvent(self, event):
        """Handle application close"""
        try:
            # Stop background threads
            self.scheduler.stop()
            
            # Shutdown tray icon if active
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.shutdown()
            
            # Close database connection
            self.db.close()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            
        # Accept the close event
        event.accept() 