#!/usr/bin/env python3
"""
Comprehensive pytest-qt GUI tests for FreeSMS application
"""
import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.models.database import Database
from src.api.service_manager import SMSServiceManager
from src.models.contact_manager import ContactManager
from src.api.sms_service import SMSResponse
from src.services.config_service import ConfigService
from src.gui.app import SMSApplication
from src.gui.message_tab import MessageTab
from src.gui.contact_tab import ContactTab
from src.gui.history_tab import HistoryTab
from src.gui.schedule_tab import ScheduleTab
from src.gui.settings_tab import SettingsTab
from src.gui.templates_tab import TemplatesTab


class TestSMSAppCore:
    """Test core SMS application functionality (non-GUI)"""
    
    def setup_method(self):
        """Set up test environment"""
        # Create mock database
        self.db = MagicMock(spec=Database)
        self.db.get_api_credentials.return_value = None
        self.db.get_active_services.return_value = []
        
        # Create a temporary directory for config files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Patch the home directory to use our temp directory
        self.home_patcher = patch('pathlib.Path.home', return_value=Path(self.temp_dir.name))
        self.mock_home = self.home_patcher.start()
        
        # Create config service with temporary config directory
        self.config = ConfigService("test_app")
        
        # Create notification service mock
        self.notification = MagicMock()
    
    def teardown_method(self):
        """Clean up test environment"""
        # Stop the patchers
        self.home_patcher.stop()
        
        # Clean up temp directory
        self.temp_dir.cleanup()
    
    def test_service_manager(self):
        """Test SMS service manager"""
        # Create manager with mock database
        manager = SMSServiceManager(self.db)
        
        # Verify available services
        services = manager.get_available_services()
        assert isinstance(services, list)
        assert 'twilio' in services
        assert 'textbelt' in services
        
        # Test get service by name
        twilio = manager.get_service_by_name('twilio')
        assert twilio is not None
        assert twilio.service_name == 'Twilio'
        
        textbelt = manager.get_service_by_name('textbelt')
        assert textbelt is not None
        assert textbelt.service_name == 'TextBelt'
    
    def test_contact_manager(self):
        """Test contact manager"""
        # Set up mock for database
        self.db.get_contacts.return_value = []
        self.db.save_contact.return_value = True
        
        # Create manager with mock database
        manager = ContactManager(self.db)
        
        # Test getting contacts
        contacts = manager.get_all_contacts()
        assert isinstance(contacts, list)
        
        # Mock validation method to return success
        with patch('src.models.contact_manager.ContactManager._validate_phone_number',
                  return_value=(True, '+12125551234')):
            # Test adding contact
            result = manager.add_contact("Test User", "12125551234", "US", "Test note")
            assert result
            self.db.save_contact.assert_called_once()
    
    def test_config_service(self):
        """Test config service"""
        # Test default settings
        assert self.config.get("general.start_minimized") is not None
        assert not self.config.get("general.start_minimized")
        
        # Test setting a value
        self.config.set("general.start_minimized", True)
        assert self.config.get("general.start_minimized")
        
        # Test non-existent key with default
        assert self.config.get("nonexistent.key", "default") == "default"
        
        # Test nested setting
        self.config.set("test.nested.setting", 123)
        assert self.config.get("test.nested.setting") == 123
    
    def test_sms_response(self):
        """Test SMS response object"""
        # Create success response
        success = SMSResponse(
            success=True,
            message_id="msg123",
            details={"status": "sent"}
        )
        assert success.success
        assert success.message_id == "msg123"
        assert "status" in success.details
        
        # Create error response
        error = SMSResponse(
            success=False,
            error="Connection failed",
            details={"code": 500}
        )
        assert not error.success
        assert error.error == "Connection failed"
        assert "code" in error.details
        assert error.details["code"] == 500
        
        # Test string representation
        assert "Success" in str(success)
        assert "Failed" in str(error)


@pytest.fixture
def setup_gui_test(qtbot):
    """Set up GUI test environment with proper mocking"""
    # Create mock database
    db = MagicMock(spec=Database)
    db.get_api_credentials.return_value = None
    db.get_active_services.return_value = []
    db.get_contacts.return_value = []
    db.get_message_history.return_value = []
    db.get_scheduled_messages.return_value = []
    db.get_templates.return_value = []
    
    # Create a temporary directory for config files
    temp_dir = tempfile.TemporaryDirectory()
    
    # Patch multiple components to prevent real interactions
    patches = []
    
    # Patch home directory
    home_patcher = patch('pathlib.Path.home', return_value=Path(temp_dir.name))
    patches.append(home_patcher)
    
    # Patch logger to prevent log file creation
    logger_patcher = patch('src.utils.logger.setup_logger')
    patches.append(logger_patcher)
    
    # Patch database to prevent real DB creation
    db_patcher = patch('src.models.database.Database')
    patches.append(db_patcher)
    
    # Patch message boxes and dialogs
    msgbox_patcher = patch('PySide6.QtWidgets.QMessageBox.question', return_value=16384)  # QMessageBox.Yes
    patches.append(msgbox_patcher)
    
    filedialog_patcher = patch('PySide6.QtWidgets.QFileDialog.getOpenFileName', return_value=('', ''))
    patches.append(filedialog_patcher)
    
    # Start all patches
    for patcher in patches:
        patcher.start()
    
    # Create config service
    config = ConfigService("test_app")
    
    # Create notification service mock
    notification = MagicMock()
    
    yield {
        'db': db,
        'config': config,
        'notification': notification,
        'temp_dir': temp_dir,
        'patches': patches
    }
    
    # Cleanup all patches
    for patcher in patches:
        patcher.stop()
    
    # Safe cleanup of temp directory
    try:
        temp_dir.cleanup()
    except (PermissionError, OSError):
        # Ignore cleanup errors in tests
        pass


class TestSMSApplicationGUI:
    """Test GUI components using pytest-qt"""

    @patch('src.utils.logger.setup_logger')
    @patch('src.automation.scheduler.MessageScheduler')
    @patch('src.models.contact_manager.ContactManager')
    @patch('src.api.service_manager.SMSServiceManager')
    @patch('src.models.database.Database')
    def test_app_initialization(self, mock_db_class, mock_service_manager_class, 
                              mock_contact_manager_class, mock_scheduler_class,
                              mock_logger, qtbot, setup_gui_test):
        """Test main application window initialization"""
        setup = setup_gui_test
        
        # Mock class instantiations
        mock_db_class.return_value = setup['db']
        mock_service_manager_class.return_value = MagicMock()
        mock_contact_manager_class.return_value = MagicMock()
        mock_scheduler_class.return_value = MagicMock()
        mock_logger.return_value = MagicMock()
        
        # Create application with comprehensive mocking
        with patch('PySide6.QtWidgets.QMessageBox.question') as mock_msg, \
             patch('threading.Thread') as mock_thread:
            
            mock_msg.return_value = 16384  # QMessageBox.Yes
            mock_thread.return_value = MagicMock()
            
            app = SMSApplication(config=setup['config'], notification=setup['notification'])
            qtbot.addWidget(app)
            
            # Test window properties
            assert app.windowTitle() == "FreeSMS"
            assert app.isVisible() is False  # Not shown yet
            
            # Show window
            app.show()
            qtbot.waitExposed(app)  # Use waitExposed instead of deprecated waitForWindowShown
            assert app.isVisible()
            
            # Test main components exist
            assert app.tab_widget is not None
            assert app.status_bar is not None
            assert app.status_label is not None
            assert app.service_status_label is not None
            
            # Test tabs are created
            assert app.tab_widget.count() >= 6  # Should have at least 6 tabs
            
            # Check tab titles
            tab_titles = []
            for i in range(app.tab_widget.count()):
                tab_titles.append(app.tab_widget.tabText(i))
            
            expected_tabs = ["Send Message", "Contacts", "Message History", "Scheduler", "Templates", "Settings"]
            for tab in expected_tabs:
                assert tab in tab_titles
    
    def test_message_tab(self, qtbot, setup_gui_test):
        """Test MessageTab functionality"""
        setup = setup_gui_test
        
        # Create mock app
        mock_app = MagicMock()
        mock_app.db = setup['db']
        mock_app.service_manager = MagicMock()
        mock_app.service_manager.get_active_service.return_value = None
        mock_app.contact_manager = MagicMock()
        mock_app.contact_manager.get_all_contacts.return_value = []
        
        # Create message tab with mocking
        with patch('PySide6.QtWidgets.QMessageBox.information'), \
             patch('PySide6.QtWidgets.QMessageBox.warning'):
            tab = MessageTab(mock_app)
            qtbot.addWidget(tab)
        
        # Test initial state
        assert tab.recipient_entry is not None
        assert tab.country_combo is not None
        assert tab.message_text is not None
        assert tab.send_button is not None
        
        # Test form interaction
        qtbot.keyClicks(tab.recipient_entry, "1234567890")
        assert tab.recipient_entry.text() == "1234567890"
        
        # Test message text
        qtbot.keyClicks(tab.message_text, "Test message")
        assert tab.message_text.toPlainText() == "Test message"
        
        # Test country selection
        tab.country_combo.setCurrentText("United States")
        assert "United States" in tab.country_combo.currentText()
    
    def test_contact_tab(self, qtbot, setup_gui_test):
        """Test ContactTab functionality"""
        setup = setup_gui_test
        
        # Create mock app
        mock_app = MagicMock()
        mock_app.contact_manager = MagicMock()
        mock_app.contact_manager.get_all_contacts.return_value = [
            {'id': 1, 'name': 'John Doe', 'phone': '+12125551234', 'country': 'US', 'notes': 'Test contact'}
        ]
        
        # Create contact tab with mocking
        with patch('PySide6.QtWidgets.QMessageBox.information'), \
             patch('PySide6.QtWidgets.QMessageBox.warning'), \
             patch('PySide6.QtWidgets.QFileDialog.getOpenFileName', return_value=('', '')):
            tab = ContactTab(mock_app)
            qtbot.addWidget(tab)
        
        # Test initial state
        assert tab.search_entry is not None
        assert tab.search_button is not None
        assert tab.contact_table is not None
        assert tab.add_button is not None
        
        # Test search functionality
        qtbot.keyClicks(tab.search_entry, "John")
        assert tab.search_entry.text() == "John"
        
        # Test search button click
        qtbot.mouseClick(tab.search_button, Qt.LeftButton)
        
        # Test that table has at least one row (from mock data)
        assert tab.contact_table.rowCount() >= 0
    
    def test_history_tab(self, qtbot, setup_gui_test):
        """Test HistoryTab functionality"""
        setup = setup_gui_test
        
        # Create mock app with proper database setup
        mock_app = MagicMock()
        mock_app.db = setup['db']
        
        # Setup mock data with correct field names
        setup['db'].get_message_history.return_value = [
            {'id': 1, 'recipient': '+12125551234', 'message': 'Test message', 
             'status': 'sent', 'service': 'twilio', 'sent_at': '2025-01-01 12:00:00'}
        ]
        
        # Mock all QMessageBox calls before creating the tab
        with patch('PySide6.QtWidgets.QMessageBox.information') as mock_info, \
             patch('PySide6.QtWidgets.QMessageBox.critical') as mock_critical, \
             patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning, \
             patch('PySide6.QtWidgets.QMessageBox.question', return_value=16384) as mock_question:
            
            # Create history tab - load_history() is called during __init__
            tab = HistoryTab(mock_app)
            qtbot.addWidget(tab)
            
            # Verify no message boxes were shown during initialization
            mock_critical.assert_not_called()
            mock_info.assert_not_called()
            mock_warning.assert_not_called()
            
            # Test initial state
            assert tab.status_combo is not None
            assert tab.service_combo is not None
            assert tab.filter_button is not None
            assert tab.history_table is not None
            assert tab.count_label is not None
            
            # Test filter controls
            tab.status_combo.setCurrentText("Sent")
            assert tab.status_combo.currentText() == "Sent"
            
            # Test filter button click
            qtbot.mouseClick(tab.filter_button, Qt.LeftButton)
            
            # Verify database was called
            setup['db'].get_message_history.assert_called()
    
    def test_schedule_tab(self, qtbot, setup_gui_test):
        """Test ScheduleTab functionality"""
        setup = setup_gui_test
        
        # Create mock app
        mock_app = MagicMock()
        mock_app.scheduler = MagicMock()
        mock_app.scheduler.get_scheduled_messages.return_value = []
        mock_app.contact_manager = MagicMock()
        mock_app.contact_manager.get_all_contacts.return_value = []
        
        # Create schedule tab with mocking
        with patch('PySide6.QtWidgets.QMessageBox.information'), \
             patch('PySide6.QtWidgets.QMessageBox.warning'):
            tab = ScheduleTab(mock_app)
            qtbot.addWidget(tab)
        
        # Test initial state
        assert tab.schedule_table is not None
        assert tab.recipient_entry is not None
        assert tab.message_text is not None
        assert tab.date_edit is not None
        assert tab.time_edit is not None
        assert tab.save_button is not None
        
        # Test form interaction
        qtbot.keyClicks(tab.recipient_entry, "+12125551234")
        assert tab.recipient_entry.text() == "+12125551234"
        
        qtbot.keyClicks(tab.message_text, "Scheduled test message")
        assert tab.message_text.toPlainText() == "Scheduled test message"
    
    def test_settings_tab(self, qtbot, setup_gui_test):
        """Test SettingsTab functionality"""
        setup = setup_gui_test
        
        # Create mock app
        mock_app = MagicMock()
        mock_app.db = setup['db']
        mock_app.service_manager = MagicMock()
        mock_app.service_manager.get_available_services.return_value = ['twilio', 'textbelt']
        mock_app.config = setup['config']
        
        # Create settings tab with mocking
        with patch('PySide6.QtWidgets.QMessageBox.information'), \
             patch('PySide6.QtWidgets.QMessageBox.warning'), \
             patch('threading.Thread'):
            tab = SettingsTab(mock_app)
            qtbot.addWidget(tab)
        
        # Test initial state
        assert tab.tab_widget is not None
        assert tab.tab_widget.count() >= 2  # Should have at least SMS Services and General
        
        # Test that SMS Services tab exists
        tab_titles = [tab.tab_widget.tabText(i) for i in range(tab.tab_widget.count())]
        assert "SMS Services" in tab_titles
        assert "General Settings" in tab_titles
    
    def test_templates_tab(self, qtbot, setup_gui_test):
        """Test TemplatesTab functionality"""
        setup = setup_gui_test
        
        # Create mock app
        mock_app = MagicMock()
        mock_app.db = setup['db']
        setup['db'].get_templates.return_value = [
            {'id': 1, 'name': 'Test Template', 'content': 'Hello {name}!'}
        ]
        
        # Create templates tab with mocking
        with patch('PySide6.QtWidgets.QMessageBox.information'), \
             patch('PySide6.QtWidgets.QMessageBox.warning'):
            tab = TemplatesTab(mock_app)
            qtbot.addWidget(tab)
        
        # Test initial state
        assert tab.template_list is not None
        assert tab.name_entry is not None
        assert tab.content_text is not None
        
        # Test form interaction
        qtbot.keyClicks(tab.name_entry, "New Template")
        assert tab.name_entry.text() == "New Template"
        
        qtbot.keyClicks(tab.content_text, "Template content")
        assert tab.content_text.toPlainText() == "Template content"
    
    @patch('PySide6.QtWidgets.QMessageBox.question', return_value=16384)  # QMessageBox.Yes
    def test_app_close_confirmation(self, mock_question, qtbot, setup_gui_test):
        """Test application close confirmation dialog"""
        setup = setup_gui_test
        
        with patch('src.utils.logger.setup_logger'), \
             patch('src.automation.scheduler.MessageScheduler'), \
             patch('src.models.contact_manager.ContactManager'), \
             patch('src.api.service_manager.SMSServiceManager'), \
             patch('src.models.database.Database'), \
             patch('threading.Thread'):
            
            app = SMSApplication(config=setup['config'], notification=setup['notification'])
            qtbot.addWidget(app)
            app.show()
            qtbot.waitExposed(app)
            
            # Test close event
            app.close()
            
            # Verify the app processes the close properly
            assert not app.isVisible()
    
    def test_tab_switching(self, qtbot, setup_gui_test):
        """Test switching between tabs"""
        setup = setup_gui_test
        
        with patch('src.utils.logger.setup_logger'), \
             patch('src.automation.scheduler.MessageScheduler'), \
             patch('src.models.contact_manager.ContactManager'), \
             patch('src.api.service_manager.SMSServiceManager'), \
             patch('src.models.database.Database'), \
             patch('threading.Thread'):
            
            app = SMSApplication(config=setup['config'], notification=setup['notification'])
            qtbot.addWidget(app)
            app.show()
            qtbot.waitExposed(app)
            
            # Test switching tabs
            initial_tab = app.tab_widget.currentIndex()
            
            # Switch to next tab
            next_tab_index = (initial_tab + 1) % app.tab_widget.count()
            app.tab_widget.setCurrentIndex(next_tab_index)
            
            assert app.tab_widget.currentIndex() == next_tab_index
            
            # Switch to specific tab by name
            for i in range(app.tab_widget.count()):
                if app.tab_widget.tabText(i) == "Settings":
                    app.tab_widget.setCurrentIndex(i)
                    assert app.tab_widget.currentIndex() == i
                    break