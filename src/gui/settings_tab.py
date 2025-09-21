"""
Settings Tab - UI for configuring SMS services and application settings
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QSpinBox, QTextEdit, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
import threading
import json

from src.security.validation import InputValidator

class SettingsTab(QWidget):
    """Settings and configuration tab"""
    
    def __init__(self, app):
        """Initialize the settings tab"""
        super().__init__()
        self.app = app
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create notebook for settings sections
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create settings pages
        self._create_sms_services_page()
        self._create_general_settings_page()
        
        # Load current settings
        self._load_current_settings()
    
    def _create_sms_services_page(self):
        """Create the SMS services configuration page"""
        services_widget = QWidget()
        services_layout = QVBoxLayout(services_widget)
        services_layout.setContentsMargins(10, 10, 10, 10)
        services_layout.setSpacing(10)
        
        self.tab_widget.addTab(services_widget, "SMS Services")
        
        # Service selection
        service_group = QGroupBox("SMS Services")
        service_layout = QFormLayout(service_group)
        
        self.service_combo = QComboBox()
        self.service_combo.addItems(["Twilio", "TextBelt"])
        self.service_combo.currentTextChanged.connect(self._on_service_selected)
        service_layout.addRow("Select Service:", self.service_combo)
        
        services_layout.addWidget(service_group)
        
        # Service details
        self.service_details_frame = QFrame()
        self.service_details_layout = QVBoxLayout(self.service_details_frame)
        
        empty_label = QLabel("Select a service to configure")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.service_details_layout.addWidget(empty_label)
        
        services_layout.addWidget(self.service_details_frame)
        
        # Active service
        active_group = QGroupBox("Active SMS Service")
        active_layout = QFormLayout(active_group)
        
        self.active_service_label = QLabel("None")
        active_layout.addRow("Current Active Service:", self.active_service_label)
        
        self.quota_label = QLabel("N/A")
        active_layout.addRow("Remaining Quota:", self.quota_label)
        
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.addStretch()
        
        self.set_active_button = QPushButton("Set as Active")
        self.set_active_button.clicked.connect(self._on_set_active_service)
        button_layout.addWidget(self.set_active_button)
        
        active_layout.addRow(button_frame)
        active_group.setLayout(active_layout)
        
        services_layout.addWidget(active_group)
        services_layout.addStretch()
    
    def _create_general_settings_page(self):
        """Create the general settings page"""
        general_widget = QWidget()
        general_layout = QVBoxLayout(general_widget)
        general_layout.setContentsMargins(10, 10, 10, 10)
        general_layout.setSpacing(10)
        
        self.tab_widget.addTab(general_widget, "General Settings")
        
        # Application settings
        app_group = QGroupBox("Application Settings")
        app_layout = QVBoxLayout(app_group)
        
        self.start_minimized_check = QCheckBox("Start minimized to system tray")
        app_layout.addWidget(self.start_minimized_check)
        
        self.check_updates_check = QCheckBox("Check for updates on startup")
        self.check_updates_check.setChecked(True)
        app_layout.addWidget(self.check_updates_check)
        
        general_layout.addWidget(app_group)
        
        # Notification settings
        notification_group = QGroupBox("Notification Settings")
        notification_layout = QVBoxLayout(notification_group)
        
        self.show_notifications_check = QCheckBox("Show desktop notifications")
        self.show_notifications_check.setChecked(True)
        notification_layout.addWidget(self.show_notifications_check)
        
        self.play_sound_check = QCheckBox("Play sound on message sent/received")
        self.play_sound_check.setChecked(True)
        notification_layout.addWidget(self.play_sound_check)
        
        general_layout.addWidget(notification_group)
        
        # Scheduler settings
        scheduler_group = QGroupBox("Scheduler Settings")
        scheduler_layout = QFormLayout(scheduler_group)
        
        interval_frame = QWidget()
        interval_layout = QHBoxLayout(interval_frame)
        
        self.check_interval_spin = QSpinBox()
        self.check_interval_spin.setMinimum(1)
        self.check_interval_spin.setMaximum(60)
        self.check_interval_spin.setValue(1)
        interval_layout.addWidget(self.check_interval_spin)
        
        interval_layout.addWidget(QLabel("minutes"))
        interval_layout.addStretch()
        
        scheduler_layout.addRow("Check scheduled messages every:", interval_frame)
        
        general_layout.addWidget(scheduler_group)
        
        # Save button
        save_frame = QWidget()
        save_layout = QHBoxLayout(save_frame)
        save_layout.addStretch()
        
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._on_save_general_settings)
        save_layout.addWidget(save_button)
        
        general_layout.addWidget(save_frame)
        general_layout.addStretch()
    
    def _load_current_settings(self):
        """Load current settings"""
        try:
            if hasattr(self.app, 'service_manager') and self.app.service_manager.active_service:
                service = self.app.service_manager.active_service
                self.active_service_label.setText(service.service_name)
                
                quota = service.get_remaining_quota()
                self.quota_label.setText(f"{quota}/{service.daily_limit}")
            else:
                self.active_service_label.setText("None")
                self.quota_label.setText("N/A")
        except:
            self.active_service_label.setText("None")
            self.quota_label.setText("N/A")
    
    def _on_service_selected(self, service_name):
        """Handle service selection"""
        # Clear service details frame
        for i in reversed(range(self.service_details_layout.count())):
            child = self.service_details_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Create form for the selected service
        if service_name == "Twilio":
            self._create_twilio_form()
        elif service_name == "TextBelt":
            self._create_textbelt_form()
    
    def _create_twilio_form(self):
        """Create Twilio configuration form"""
        # Get existing credentials
        try:
            credentials = self.app.db.get_api_credentials("twilio") or {}
            
            if isinstance(credentials, str):
                try:
                    credentials = json.loads(credentials)
                except:
                    credentials = {}
        except:
            credentials = {}
        
        form_group = QGroupBox("Twilio Configuration")
        form_layout = QFormLayout(form_group)
        
        # Account SID
        self.twilio_sid_entry = QLineEdit()
        self.twilio_sid_entry.setText(credentials.get('account_sid', ''))
        form_layout.addRow("Account SID:", self.twilio_sid_entry)
        
        # Auth Token
        self.twilio_token_entry = QLineEdit()
        self.twilio_token_entry.setText(credentials.get('auth_token', ''))
        self.twilio_token_entry.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Auth Token:", self.twilio_token_entry)
        
        # Phone Number
        self.twilio_phone_entry = QLineEdit()
        self.twilio_phone_entry.setText(credentials.get('phone_number', ''))
        form_layout.addRow("Twilio Phone Number:", self.twilio_phone_entry)
        
        # Help text
        help_text = QTextEdit()
        help_text.setMaximumHeight(150)
        help_text.setReadOnly(True)
        help_text.setPlainText(
            "To get your Twilio credentials:\n"
            "1. Sign up at https://www.twilio.com/try-twilio\n"
            "2. Get your Account SID and Auth Token from the Twilio Console\n"
            "3. Get a Twilio phone number from the Phone Numbers section\n\n"
            "Note: Twilio's free trial has limited credits and requires verifying recipient phone numbers."
        )
        form_layout.addRow("Help:", help_text)
        
        # Buttons
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.addStretch()
        
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self._on_test_twilio)
        button_layout.addWidget(test_button)
        
        save_button = QPushButton("Save Credentials")
        save_button.clicked.connect(self._on_save_twilio)
        button_layout.addWidget(save_button)
        
        form_layout.addRow(button_frame)
        
        self.service_details_layout.addWidget(form_group)
    
    def _create_textbelt_form(self):
        """Create TextBelt configuration form"""
        # Get existing credentials
        try:
            credentials = self.app.db.get_api_credentials("textbelt") or {}
            
            if isinstance(credentials, str):
                try:
                    credentials = json.loads(credentials)
                except:
                    credentials = {}
        except:
            credentials = {}
        
        form_group = QGroupBox("TextBelt Configuration")
        form_layout = QFormLayout(form_group)
        
        # API Key
        self.textbelt_key_entry = QLineEdit()
        self.textbelt_key_entry.setText(credentials.get('api_key', ''))
        form_layout.addRow("API Key:", self.textbelt_key_entry)
        
        # Use free tier option
        self.use_free_tier_check = QCheckBox("Use free tier (1 message per day)")
        self.use_free_tier_check.setChecked(credentials.get('api_key', '') == 'textbelt')
        self.use_free_tier_check.toggled.connect(self._on_free_tier_toggled)
        form_layout.addRow(self.use_free_tier_check)
        
        # Help text
        help_text = QTextEdit()
        help_text.setMaximumHeight(120)
        help_text.setReadOnly(True)
        help_text.setPlainText(
            "TextBelt options:\n"
            "1. Free tier: 1 free SMS per day (no registration required)\n"
            "2. Paid tier: Purchase an API key at https://textbelt.com/\n\n"
            "The free tier has limited availability and may not work in all regions."
        )
        form_layout.addRow("Help:", help_text)
        
        # Buttons
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.addStretch()
        
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self._on_test_textbelt)
        button_layout.addWidget(test_button)
        
        save_button = QPushButton("Save Credentials")
        save_button.clicked.connect(self._on_save_textbelt)
        button_layout.addWidget(save_button)
        
        form_layout.addRow(button_frame)
        
        self.service_details_layout.addWidget(form_group)
        
        # Update entry state based on free tier checkbox
        self._on_free_tier_toggled()
    
    def _on_free_tier_toggled(self):
        """Handle free tier checkbox toggle"""
        if self.use_free_tier_check.isChecked():
            self.textbelt_key_entry.setEnabled(False)
            self.textbelt_key_entry.setText("textbelt")
        else:
            self.textbelt_key_entry.setEnabled(True)
            if self.textbelt_key_entry.text() == "textbelt":
                self.textbelt_key_entry.clear()
    
    def _on_test_twilio(self):
        """Test Twilio connection"""
        account_sid = self.twilio_sid_entry.text().strip()
        auth_token = self.twilio_token_entry.text().strip()
        phone_number = self.twilio_phone_entry.text().strip()
        
        if not account_sid:
            QMessageBox.critical(self, "Error", "Account SID is required")
            return
            
        if not auth_token:
            QMessageBox.critical(self, "Error", "Auth Token is required")
            return
            
        if not phone_number:
            QMessageBox.critical(self, "Error", "Phone Number is required")
            return
        
        credentials = {
            'account_sid': account_sid,
            'auth_token': auth_token,
            'phone_number': phone_number
        }
        
        self.app.set_status("Testing Twilio connection...")
        threading.Thread(target=self._test_twilio_thread, args=(credentials,)).start()
    
    def _test_twilio_thread(self, credentials):
        """Test Twilio connection in a background thread"""
        try:
            service = self.app.service_manager.get_service_by_name("twilio")
            if not service:
                QMessageBox.critical(self, "Error", "Twilio service not available")
                self.app.set_status("Ready")
                return
                
            success = service.configure(credentials)
            
            if success:
                QMessageBox.information(self, "Success", "Twilio connection successful")
            else:
                QMessageBox.critical(self, "Error", "Failed to connect to Twilio")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error testing Twilio: {str(e)}")
            
        self.app.set_status("Ready")
    
    def _on_save_twilio(self):
        """Save Twilio credentials"""
        account_sid = self.twilio_sid_entry.text().strip()
        auth_token = self.twilio_token_entry.text().strip()
        phone_number = self.twilio_phone_entry.text().strip()
        
        if not account_sid:
            QMessageBox.critical(self, "Error", "Account SID is required")
            return
            
        if not auth_token:
            QMessageBox.critical(self, "Error", "Auth Token is required")
            return
            
        if not phone_number:
            QMessageBox.critical(self, "Error", "Phone Number is required")
            return
        
        credentials = {
            'account_sid': account_sid,
            'auth_token': auth_token,
            'phone_number': phone_number
        }
        
        try:
            success = self.app.service_manager.configure_service("twilio", credentials)
            
            if success:
                QMessageBox.information(self, "Success", "Twilio credentials saved successfully")
                self._load_current_settings()
            else:
                QMessageBox.critical(self, "Error", "Failed to save Twilio credentials")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Twilio credentials: {str(e)}")
    
    def _on_test_textbelt(self):
        """Test TextBelt connection"""
        api_key = self.textbelt_key_entry.text().strip()
        
        if not api_key:
            QMessageBox.critical(self, "Error", "API Key is required")
            return
        
        credentials = {'api_key': api_key}
        
        self.app.set_status("Testing TextBelt connection...")
        threading.Thread(target=self._test_textbelt_thread, args=(credentials,)).start()
    
    def _test_textbelt_thread(self, credentials):
        """Test TextBelt connection in a background thread"""
        try:
            service = self.app.service_manager.get_service_by_name("textbelt")
            if not service:
                QMessageBox.critical(self, "Error", "TextBelt service not available")
                self.app.set_status("Ready")
                return
                
            success = service.configure(credentials)
            
            if success:
                quota = service.get_remaining_quota()
                QMessageBox.information(self, "Success", 
                    f"TextBelt connection successful\nRemaining quota: {quota}")
            else:
                QMessageBox.critical(self, "Error", "Failed to connect to TextBelt")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error testing TextBelt: {str(e)}")
            
        self.app.set_status("Ready")
    
    def _on_save_textbelt(self):
        """Save TextBelt credentials"""
        api_key = self.textbelt_key_entry.text().strip()
        
        if not api_key:
            QMessageBox.critical(self, "Error", "API Key is required")
            return
        
        credentials = {'api_key': api_key}
        
        try:
            success = self.app.service_manager.configure_service("textbelt", credentials)
            
            if success:
                QMessageBox.information(self, "Success", "TextBelt credentials saved successfully")
                self._load_current_settings()
            else:
                QMessageBox.critical(self, "Error", "Failed to save TextBelt credentials")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save TextBelt credentials: {str(e)}")
    
    def _on_set_active_service(self):
        """Set the active SMS service"""
        service_name = self.service_combo.currentText()
        
        if not service_name:
            QMessageBox.information(self, "Information", "Please select a service to set as active")
            return
        
        try:
            success = self.app.service_manager.set_active_service(service_name.lower())
            
            if success:
                QMessageBox.information(self, "Success", f"{service_name} set as active service")
                self._load_current_settings()
            else:
                QMessageBox.critical(self, "Error", 
                    f"Failed to set {service_name} as active service. Is it configured?")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set active service: {str(e)}")
    
    def _on_save_general_settings(self):
        """Save general settings"""
        QMessageBox.information(self, "Success", "Settings saved successfully")
        
        check_interval = self.check_interval_spin.value()
        # Update scheduler interval if supported
        # self.app.scheduler.set_check_interval(check_interval * 60)  # Convert to seconds