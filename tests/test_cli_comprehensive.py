#!/usr/bin/env python3
"""
Comprehensive test suite for CLI module - Consolidated from comprehensive and extended tests
"""
import os
import sys
import pytest
import json
import csv
import tempfile
import argparse
from unittest.mock import patch, MagicMock, call, mock_open
from datetime import datetime, timedelta
from io import StringIO

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cli.cli import SMSCommandLineInterface, parse_args, main


class TestSMSCommandLineInterface:
    """Test cases for SMS CLI class - Basic functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        self.original_argv = sys.argv.copy()
        
    def teardown_method(self):
        """Clean up test environment after each test"""
        sys.argv = self.original_argv
    
    @patch('src.cli.cli.Database')
    @patch('src.cli.cli.SMSServiceManager')
    @patch('src.cli.cli.ContactManager')
    @patch('src.cli.cli.MessageScheduler')
    @patch('src.cli.cli.InputValidator')
    @patch('src.cli.cli.setup_logger')
    def test_initialization(self, mock_logger, mock_validator, mock_scheduler, 
                           mock_contact_mgr, mock_service_mgr, mock_db):
        """Test CLI initialization"""
        mock_logger.return_value = MagicMock()
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        
        mock_service_mgr_instance = MagicMock()
        mock_service_mgr.return_value = mock_service_mgr_instance
        
        mock_contact_mgr_instance = MagicMock()
        mock_contact_mgr.return_value = mock_contact_mgr_instance
        
        mock_scheduler_instance = MagicMock()
        mock_scheduler.return_value = mock_scheduler_instance
        
        mock_validator_instance = MagicMock()
        mock_validator.return_value = mock_validator_instance
        
        # Initialize CLI
        cli = SMSCommandLineInterface()
        
        # Verify all services were initialized
        mock_logger.assert_called_once_with("sms_sender_cli")
        mock_db.assert_called_once()
        mock_service_mgr.assert_called_once_with(mock_db_instance)
        mock_contact_mgr.assert_called_once_with(mock_db_instance)
        mock_scheduler.assert_called_once_with(mock_db_instance, mock_service_mgr_instance)
        mock_validator.assert_called_once()
        mock_scheduler_instance.start.assert_called_once()
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_send_message_success(self, mock_logger, mock_init_services):
        """Test successful message sending"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful validation and sending
        cli.validator.validate_phone_input.return_value = (True, None)
        cli.validator.validate_message.return_value = (True, None)
        cli.service_manager.send_sms.return_value = {
            'success': True,
            'message_id': 'msg_123',
            'service': 'test_service'
        }
        
        # Test sending message
        result = cli.send_message("+1234567890", "Test message")
        
        # Verify validation was called
        cli.validator.validate_phone_input.assert_called_once_with("+1234567890")
        cli.validator.validate_message.assert_called_once_with("Test message")
        
        # Verify message was sent
        cli.service_manager.send_sms.assert_called_once_with(
            "+1234567890", "Test message", None
        )
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_send_message_validation_failure(self, mock_logger, mock_init_services):
        """Test message sending with validation failure"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock phone validation failure
        cli.validator.validate_phone_input.return_value = (False, "Invalid phone number")
        
        # Test sending message
        result = cli.send_message("+invalid", "Test message")
        
        # Verify validation was called but sending was not
        cli.validator.validate_phone_input.assert_called_once_with("+invalid")
        cli.service_manager.send_sms.assert_not_called()
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_send_message_service_failure(self, mock_logger, mock_init_services):
        """Test message sending with service failure"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful validation but service failure
        cli.validator.validate_phone_input.return_value = (True, None)
        cli.validator.validate_message.return_value = (True, None)
        cli.service_manager.send_sms.return_value = {
            'success': False,
            'error': 'Service unavailable'
        }
        
        # Test sending message
        result = cli.send_message("+1234567890", "Test message")
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_contacts_success(self, mock_print, mock_logger, mock_init_services):
        """Test successful contacts listing"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock contacts data
        mock_contacts = [
            {'id': 1, 'name': 'John Doe', 'phone': '+1234567890', 'country': 'US', 'notes': 'Test contact'},
            {'id': 2, 'name': 'Jane Smith', 'phone': '+0987654321', 'country': 'UK', 'notes': ''}
        ]
        cli.contact_manager.list_contacts.return_value = mock_contacts
        
        # Test listing contacts
        result = cli.list_contacts()
        
        # Verify contacts were retrieved
        cli.contact_manager.list_contacts.assert_called_once()
        
        # Verify print was called (contacts were displayed)
        assert mock_print.called
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_contacts_empty(self, mock_print, mock_logger, mock_init_services):
        """Test contacts listing when empty"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock empty contacts
        cli.contact_manager.list_contacts.return_value = []
        
        # Test listing contacts
        result = cli.list_contacts()
        
        # Verify contacts were retrieved
        cli.contact_manager.list_contacts.assert_called_once()
        
        # Verify "No contacts" message was printed
        mock_print.assert_called_with("No contacts found.")
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_add_contact_success(self, mock_logger, mock_init_services):
        """Test successful contact addition"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful validation and addition
        cli.validator.validate_phone_input.return_value = (True, None)
        cli.contact_manager.add_contact.return_value = {'id': 1, 'success': True}
        
        # Test adding contact
        result = cli.add_contact("John Doe", "+1234567890", "US", "Test notes")
        
        # Verify validation was called
        cli.validator.validate_phone_input.assert_called_once_with("+1234567890")
        
        # Verify contact was added
        cli.contact_manager.add_contact.assert_called_once_with(
            "John Doe", "+1234567890", "US", "Test notes"
        )
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_add_contact_validation_failure(self, mock_logger, mock_init_services):
        """Test contact addition with validation failure"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock phone validation failure
        cli.validator.validate_phone_input.return_value = (False, "Invalid phone")
        
        # Test adding contact
        result = cli.add_contact("John Doe", "+invalid", "US", "Test notes")
        
        # Verify validation was called but addition was not
        cli.validator.validate_phone_input.assert_called_once_with("+invalid")
        cli.contact_manager.add_contact.assert_not_called()
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_delete_contact_success(self, mock_logger, mock_init_services):
        """Test successful contact deletion"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful deletion
        cli.contact_manager.delete_contact.return_value = True
        
        # Test deleting contact
        result = cli.delete_contact(1)
        
        # Verify contact was deleted
        cli.contact_manager.delete_contact.assert_called_once_with(1)
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_delete_contact_failure(self, mock_logger, mock_init_services):
        """Test contact deletion failure"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock deletion failure
        cli.contact_manager.delete_contact.return_value = False
        
        # Test deleting contact
        result = cli.delete_contact(999)
        
        # Verify contact deletion was attempted
        cli.contact_manager.delete_contact.assert_called_once_with(999)
        
        # Verify result
        assert result is False


class TestCLITemplatesFeatures:
    """Test cases for template-related CLI functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        self.original_argv = sys.argv.copy()
        
    def teardown_method(self):
        """Clean up test environment after each test"""
        sys.argv = self.original_argv
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_templates_success(self, mock_print, mock_logger, mock_init_services):
        """Test successful template listing"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock templates data
        mock_templates = [
            {'id': 1, 'name': 'Reminder', 'content': 'Don\'t forget your appointment', 'created_at': '2024-01-01 10:00:00'},
            {'id': 2, 'name': 'Welcome', 'content': 'Welcome to our service!', 'created_at': '2024-01-02 11:00:00'}
        ]
        cli.db.get_templates.return_value = mock_templates
        
        # Test listing templates
        result = cli.list_templates()
        
        # Verify templates were retrieved
        cli.db.get_templates.assert_called_once()
        
        # Verify print was called (templates were displayed)
        assert mock_print.called
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_templates_empty(self, mock_print, mock_logger, mock_init_services):
        """Test template listing when empty"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock empty templates
        cli.db.get_templates.return_value = []
        
        # Test listing templates
        result = cli.list_templates()
        
        # Verify templates were retrieved
        cli.db.get_templates.assert_called_once()
        
        # Verify "No templates" message was printed
        mock_print.assert_called_with("No templates found.")
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_add_template_success(self, mock_logger, mock_init_services):
        """Test successful template addition"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful validation and addition
        cli.validator.validate_message.return_value = (True, None)
        cli.db.save_template.return_value = {'id': 1, 'success': True}
        
        # Test adding template
        result = cli.add_template("Test Template", "This is a test template")
        
        # Verify validation was called
        cli.validator.validate_message.assert_called_once_with("This is a test template")
        
        # Verify template was added
        cli.db.save_template.assert_called_once_with("Test Template", "This is a test template")
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_add_template_validation_failure(self, mock_logger, mock_init_services):
        """Test template addition with validation failure"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock validation failure
        cli.validator.validate_message.return_value = (False, "Message too long")
        
        # Test adding template
        result = cli.add_template("Test Template", "A" * 1000)  # Very long message
        
        # Verify validation was called but addition was not
        cli.validator.validate_message.assert_called_once()
        cli.db.save_template.assert_not_called()
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_delete_template_success(self, mock_logger, mock_init_services):
        """Test successful template deletion"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful deletion
        cli.db.delete_template.return_value = True
        
        # Test deleting template
        result = cli.delete_template(1)
        
        # Verify template was deleted
        cli.db.delete_template.assert_called_once_with(1)
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_delete_template_failure(self, mock_logger, mock_init_services):
        """Test template deletion failure"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock deletion failure
        cli.db.delete_template.return_value = False
        
        # Test deleting template
        result = cli.delete_template(999)
        
        # Verify template deletion was attempted
        cli.db.delete_template.assert_called_once_with(999)
        
        # Verify result
        assert result is False


class TestCLISchedulingFeatures:
    """Test cases for scheduling-related CLI functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        self.original_argv = sys.argv.copy()
        
    def teardown_method(self):
        """Clean up test environment after each test"""
        sys.argv = self.original_argv
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_scheduled_messages_success(self, mock_print, mock_logger, mock_init_services):
        """Test successful scheduled messages listing"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock scheduled messages data
        mock_messages = [
            {'id': 1, 'recipient': '+1234567890', 'message': 'Test message', 'scheduled_time': '2024-12-25 10:00:00', 'status': 'pending'},
            {'id': 2, 'recipient': '+0987654321', 'message': 'Another message', 'scheduled_time': '2024-12-26 15:30:00', 'status': 'pending'}
        ]
        cli.db.get_scheduled_messages.return_value = mock_messages
        
        # Test listing scheduled messages
        result = cli.list_scheduled_messages()
        
        # Verify messages were retrieved (pending only)
        cli.db.get_scheduled_messages.assert_called_once_with(include_sent=False)
        
        # Verify print was called (messages were displayed)
        assert mock_print.called
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_scheduled_messages_all(self, mock_print, mock_logger, mock_init_services):
        """Test listing all scheduled messages including sent"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock scheduled messages data including sent
        mock_messages = [
            {'id': 1, 'recipient': '+1234567890', 'message': 'Test message', 'scheduled_time': '2024-12-25 10:00:00', 'status': 'pending'},
            {'id': 2, 'recipient': '+0987654321', 'message': 'Sent message', 'scheduled_time': '2024-12-20 15:30:00', 'status': 'sent'}
        ]
        cli.db.get_scheduled_messages.return_value = mock_messages
        
        # Test listing all scheduled messages
        result = cli.list_scheduled_messages(include_all=True)
        
        # Verify messages were retrieved (including sent)
        cli.db.get_scheduled_messages.assert_called_once_with(include_sent=True)
        
        # Verify print was called (messages were displayed)
        assert mock_print.called
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_scheduled_messages_empty(self, mock_print, mock_logger, mock_init_services):
        """Test scheduled messages listing when empty"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock empty scheduled messages
        cli.db.get_scheduled_messages.return_value = []
        
        # Test listing scheduled messages
        result = cli.list_scheduled_messages()
        
        # Verify messages were retrieved
        cli.db.get_scheduled_messages.assert_called_once()
        
        # Verify "No messages" message was printed
        mock_print.assert_called_with("No scheduled messages found.")
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_schedule_message_success(self, mock_logger, mock_init_services):
        """Test successful message scheduling"""
        cli = SMSCommandLineInterface()
        cli.scheduler = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful validation and scheduling
        cli.validator.validate_phone_input.return_value = (True, None)
        cli.validator.validate_message.return_value = (True, None)
        cli.scheduler.schedule_message.return_value = {'id': 1, 'success': True}
        
        # Test scheduling message
        result = cli.schedule_message("+1234567890", "Test message", "2024-12-25T10:00:00", None, False, None)
        
        # Verify validation was called
        cli.validator.validate_phone_input.assert_called_once_with("+1234567890")
        cli.validator.validate_message.assert_called_once_with("Test message")
        
        # Verify message was scheduled
        cli.scheduler.schedule_message.assert_called_once()
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_schedule_message_validation_failure(self, mock_logger, mock_init_services):
        """Test message scheduling with validation failure"""
        cli = SMSCommandLineInterface()
        cli.scheduler = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock phone validation failure
        cli.validator.validate_phone_input.return_value = (False, "Invalid phone number")
        
        # Test scheduling message
        result = cli.schedule_message("+invalid", "Test message", "2024-12-25T10:00:00", None, False, None)
        
        # Verify validation was called but scheduling was not
        cli.validator.validate_phone_input.assert_called_once_with("+invalid")
        cli.scheduler.schedule_message.assert_not_called()
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_cancel_scheduled_message_success(self, mock_logger, mock_init_services):
        """Test successful scheduled message cancellation"""
        cli = SMSCommandLineInterface()
        cli.scheduler = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful cancellation
        cli.scheduler.cancel_scheduled_message.return_value = True
        
        # Test cancelling scheduled message
        result = cli.cancel_scheduled_message(1)
        
        # Verify message was cancelled
        cli.scheduler.cancel_scheduled_message.assert_called_once_with(1)
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_cancel_scheduled_message_failure(self, mock_logger, mock_init_services):
        """Test scheduled message cancellation failure"""
        cli = SMSCommandLineInterface()
        cli.scheduler = MagicMock()
        cli.logger = MagicMock()
        
        # Mock cancellation failure
        cli.scheduler.cancel_scheduled_message.return_value = False
        
        # Test cancelling scheduled message
        result = cli.cancel_scheduled_message(999)
        
        # Verify message cancellation was attempted
        cli.scheduler.cancel_scheduled_message.assert_called_once_with(999)
        
        # Verify result
        assert result is False


class TestCLIHistoryFeatures:
    """Test cases for history-related CLI functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        self.original_argv = sys.argv.copy()
        
    def teardown_method(self):
        """Clean up test environment after each test"""
        sys.argv = self.original_argv
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_message_history_success(self, mock_print, mock_logger, mock_init_services):
        """Test successful message history listing"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock history data
        mock_history = [
            {'id': 1, 'recipient': '+1234567890', 'message': 'Hello', 'sent_at': '2024-01-01 10:00:00', 'status': 'sent'},
            {'id': 2, 'recipient': '+0987654321', 'message': 'Hi there', 'sent_at': '2024-01-01 11:00:00', 'status': 'delivered'}
        ]
        cli.db.get_message_history.return_value = mock_history
        
        # Test listing message history
        result = cli.list_message_history(10)
        
        # Verify history was retrieved
        cli.db.get_message_history.assert_called_once_with(10)
        
        # Verify print was called (history was displayed)
        assert mock_print.called
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_message_history_empty(self, mock_print, mock_logger, mock_init_services):
        """Test message history listing when empty"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock empty history
        cli.db.get_message_history.return_value = []
        
        # Test listing message history
        result = cli.list_message_history(20)
        
        # Verify history was retrieved
        cli.db.get_message_history.assert_called_once_with(20)
        
        # Verify "No history" message was printed
        mock_print.assert_called_with("No message history found.")
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.open', create=True)
    def test_export_history_success(self, mock_open_func, mock_logger, mock_init_services):
        """Test successful message history export"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock history data
        mock_history = [
            {'id': 1, 'recipient': '+1234567890', 'message': 'Hello', 'sent_at': '2024-01-01 10:00:00', 'status': 'sent', 'service': 'twilio'},
            {'id': 2, 'recipient': '+0987654321', 'message': 'Hi there', 'sent_at': '2024-01-01 11:00:00', 'status': 'delivered', 'service': 'textbelt'}
        ]
        cli.db.get_message_history.return_value = mock_history
        
        # Mock file operations
        mock_file = MagicMock()
        mock_open_func.return_value.__enter__.return_value = mock_file
        
        # Test exporting history
        result = cli.export_history("test_export.csv", 100)
        
        # Verify history was retrieved
        cli.db.get_message_history.assert_called_once_with(100)
        
        # Verify file was opened for writing
        mock_open_func.assert_called_once_with("test_export.csv", 'w', newline='', encoding='utf-8')
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_export_history_empty(self, mock_logger, mock_init_services):
        """Test message history export when empty"""
        cli = SMSCommandLineInterface()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock empty history
        cli.db.get_message_history.return_value = []
        
        # Test exporting history
        result = cli.export_history("empty_export.csv", 100)
        
        # Verify history was retrieved
        cli.db.get_message_history.assert_called_once_with(100)
        
        # Verify result
        assert result is False


class TestCLIServiceFeatures:
    """Test cases for service-related CLI functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        self.original_argv = sys.argv.copy()
        
    def teardown_method(self):
        """Clean up test environment after each test"""
        sys.argv = self.original_argv
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.print')
    def test_list_services_success(self, mock_print, mock_logger, mock_init_services):
        """Test successful services listing"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock services data
        mock_services = ['twilio', 'textbelt']
        mock_configured_services = ['twilio']
        mock_active_service = 'twilio'
        
        cli.service_manager.get_available_services.return_value = mock_services
        cli.service_manager.get_configured_services.return_value = mock_configured_services
        cli.service_manager.get_active_service.return_value = mock_active_service
        
        # Test listing services
        result = cli.list_services()
        
        # Verify services were retrieved
        cli.service_manager.get_available_services.assert_called_once()
        cli.service_manager.get_configured_services.assert_called_once()
        cli.service_manager.get_active_service.assert_called_once()
        
        # Verify print was called (services were displayed)
        assert mock_print.called
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_configure_service_success(self, mock_logger, mock_init_services):
        """Test successful service configuration"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful configuration
        mock_service = MagicMock()
        mock_service.configure.return_value = True
        cli.service_manager.get_service_by_name.return_value = mock_service
        
        # Test configuring service
        result = cli.configure_service("twilio", "account_sid:auth_token")
        
        # Verify service was configured
        cli.service_manager.get_service_by_name.assert_called_once_with("twilio")
        mock_service.configure.assert_called_once()
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_configure_service_not_found(self, mock_logger, mock_init_services):
        """Test service configuration when service not found"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock service not found
        cli.service_manager.get_service_by_name.return_value = None
        
        # Test configuring service
        result = cli.configure_service("nonexistent", "credentials")
        
        # Verify service lookup was attempted
        cli.service_manager.get_service_by_name.assert_called_once_with("nonexistent")
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_set_active_service_success(self, mock_logger, mock_init_services):
        """Test successful active service setting"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful active service setting
        cli.service_manager.set_active_service.return_value = True
        
        # Test setting active service
        result = cli.set_active_service("twilio")
        
        # Verify active service was set
        cli.service_manager.set_active_service.assert_called_once_with("twilio")
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_set_active_service_failure(self, mock_logger, mock_init_services):
        """Test active service setting failure"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock active service setting failure
        cli.service_manager.set_active_service.return_value = False
        
        # Test setting active service
        result = cli.set_active_service("nonexistent")
        
        # Verify active service setting was attempted
        cli.service_manager.set_active_service.assert_called_once_with("nonexistent")
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_test_service_success(self, mock_logger, mock_init_services):
        """Test successful service testing"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock successful service test
        cli.service_manager.send_sms.return_value = {
            'success': True,
            'message_id': 'test_123'
        }
        
        # Test testing service
        result = cli.test_service("twilio")
        
        # Verify service test was performed
        cli.service_manager.send_sms.assert_called_once()
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_test_service_failure(self, mock_logger, mock_init_services):
        """Test service testing failure"""
        cli = SMSCommandLineInterface()
        cli.service_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock service test failure
        cli.service_manager.send_sms.return_value = {
            'success': False,
            'error': 'Service unavailable'
        }
        
        # Test testing service
        result = cli.test_service("twilio")
        
        # Verify service test was performed
        cli.service_manager.send_sms.assert_called_once()
        
        # Verify result
        assert result is False


class TestCLIImportExportFeatures:
    """Test cases for import/export CLI functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        self.original_argv = sys.argv.copy()
        
    def teardown_method(self):
        """Clean up test environment after each test"""
        sys.argv = self.original_argv
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.open', create=True)
    def test_export_contacts_success(self, mock_open_func, mock_logger, mock_init_services):
        """Test successful contacts export"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock contacts data
        mock_contacts = [
            {'id': 1, 'name': 'John Doe', 'phone': '+1234567890', 'country': 'US', 'notes': 'Test contact'},
            {'id': 2, 'name': 'Jane Smith', 'phone': '+0987654321', 'country': 'UK', 'notes': 'Another contact'}
        ]
        cli.contact_manager.list_contacts.return_value = mock_contacts
        
        # Mock file operations
        mock_file = MagicMock()
        mock_open_func.return_value.__enter__.return_value = mock_file
        
        # Test exporting contacts
        result = cli.export_contacts("test_contacts.csv")
        
        # Verify contacts were retrieved
        cli.contact_manager.list_contacts.assert_called_once()
        
        # Verify file was opened for writing
        mock_open_func.assert_called_once_with("test_contacts.csv", 'w', newline='', encoding='utf-8')
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_export_contacts_empty(self, mock_logger, mock_init_services):
        """Test contacts export when no contacts"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock empty contacts
        cli.contact_manager.list_contacts.return_value = []
        
        # Test exporting contacts
        result = cli.export_contacts("empty_contacts.csv")
        
        # Verify contacts were retrieved
        cli.contact_manager.list_contacts.assert_called_once()
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_import_contacts_success(self, mock_exists, mock_open_func, mock_logger, mock_init_services):
        """Test successful contacts import"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.validator = MagicMock()
        cli.logger = MagicMock()
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock CSV data
        csv_data = StringIO("name,phone,country,notes\nJohn Doe,+1234567890,US,Test contact\nJane Smith,+0987654321,UK,Another contact")
        mock_open_func.return_value.__enter__.return_value = csv_data
        
        # Mock successful validation and addition
        cli.validator.validate_phone_input.return_value = (True, None)
        cli.contact_manager.add_contact.return_value = {'id': 1, 'success': True}
        
        # Test importing contacts
        result = cli.import_contacts("test_contacts.csv")
        
        # Verify file existence was checked
        mock_exists.assert_called_once_with("test_contacts.csv")
        
        # Verify file was opened for reading
        mock_open_func.assert_called_once_with("test_contacts.csv", 'r', encoding='utf-8')
        
        # Verify validation was called for each contact
        assert cli.validator.validate_phone_input.call_count == 2
        
        # Verify contacts were added
        assert cli.contact_manager.add_contact.call_count == 2
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('os.path.exists')
    def test_import_contacts_file_not_found(self, mock_exists, mock_logger, mock_init_services):
        """Test contacts import when file doesn't exist"""
        cli = SMSCommandLineInterface()
        cli.contact_manager = MagicMock()
        cli.logger = MagicMock()
        
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Test importing contacts
        result = cli.import_contacts("nonexistent.csv")
        
        # Verify file existence was checked
        mock_exists.assert_called_once_with("nonexistent.csv")
        
        # Verify no contacts were added
        cli.contact_manager.add_contact.assert_not_called()
        
        # Verify result
        assert result is False
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    @patch('builtins.open', create=True)
    def test_create_contacts_template_success(self, mock_open_func, mock_logger, mock_init_services):
        """Test successful contacts template creation"""
        cli = SMSCommandLineInterface()
        cli.logger = MagicMock()
        
        # Mock file operations
        mock_file = MagicMock()
        mock_open_func.return_value.__enter__.return_value = mock_file
        
        # Test creating contacts template
        result = cli.create_contacts_template("contacts_template.csv")
        
        # Verify file was opened for writing
        mock_open_func.assert_called_once_with("contacts_template.csv", 'w', newline='', encoding='utf-8')
        
        # Verify result
        assert result is True
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_shutdown_success(self, mock_logger, mock_init_services):
        """Test successful CLI shutdown"""
        cli = SMSCommandLineInterface()
        cli.scheduler = MagicMock()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Test shutdown
        cli.shutdown()
        
        # Verify scheduler was stopped
        cli.scheduler.stop.assert_called_once()
        
        # Verify database was closed
        cli.db.close.assert_called_once()
    
    @patch('src.cli.cli.SMSCommandLineInterface._initialize_services')
    @patch('src.cli.cli.setup_logger')
    def test_shutdown_with_exceptions(self, mock_logger, mock_init_services):
        """Test CLI shutdown with exceptions"""
        cli = SMSCommandLineInterface()
        cli.scheduler = MagicMock()
        cli.db = MagicMock()
        cli.logger = MagicMock()
        
        # Mock scheduler stop failure
        cli.scheduler.stop.side_effect = Exception("Scheduler stop failed")
        
        # Test shutdown (should not raise exception)
        cli.shutdown()
        
        # Verify scheduler stop was attempted
        cli.scheduler.stop.assert_called_once()
        
        # Verify database was still closed
        cli.db.close.assert_called_once()


class TestParseArgs:
    """Test cases for argument parsing"""
    
    def setup_method(self):
        """Set up test environment"""
        self.original_argv = sys.argv.copy()
    
    def teardown_method(self):
        """Clean up test environment"""
        sys.argv = self.original_argv
    
    def test_parse_send_command(self):
        """Test parsing send command"""
        sys.argv = ['cli.py', 'send', '+1234567890', 'Hello World']
        args = parse_args()
        
        assert args.command == 'send'
        assert args.recipient == '+1234567890'
        assert args.message == 'Hello World'
        assert args.service is None
    
    def test_parse_send_command_with_service(self):
        """Test parsing send command with service"""
        sys.argv = ['cli.py', 'send', '+1234567890', 'Hello World', '--service', 'twilio']
        args = parse_args()
        
        assert args.command == 'send'
        assert args.recipient == '+1234567890'
        assert args.message == 'Hello World'
        assert args.service == 'twilio'
    
    def test_parse_contacts_list_command(self):
        """Test parsing contacts list command"""
        sys.argv = ['cli.py', 'contacts', 'list']
        args = parse_args()
        
        assert args.command == 'contacts'
        assert args.subcommand == 'list'
    
    def test_parse_contacts_add_command(self):
        """Test parsing contacts add command"""
        sys.argv = ['cli.py', 'contacts', 'add', 'John Doe', '+1234567890', '--country', 'US', '--notes', 'Test contact']
        args = parse_args()
        
        assert args.command == 'contacts'
        assert args.subcommand == 'add'
        assert args.name == 'John Doe'
        assert args.phone == '+1234567890'
        assert args.country == 'US'
        assert args.notes == 'Test contact'
    
    def test_parse_contacts_delete_command(self):
        """Test parsing contacts delete command"""
        sys.argv = ['cli.py', 'contacts', 'delete', '123']
        args = parse_args()
        
        assert args.command == 'contacts'
        assert args.subcommand == 'delete'
        assert args.id == '123'
    
    def test_parse_contacts_import_command(self):
        """Test parsing contacts import command"""
        sys.argv = ['cli.py', 'contacts', 'import', 'contacts.csv']
        args = parse_args()
        
        assert args.command == 'contacts'
        assert args.subcommand == 'import'
        assert args.input_file == 'contacts.csv'
    
    def test_parse_contacts_export_command(self):
        """Test parsing contacts export command"""
        sys.argv = ['cli.py', 'contacts', 'export', 'output.csv']
        args = parse_args()
        
        assert args.command == 'contacts'
        assert args.subcommand == 'export'
        assert args.output_file == 'output.csv'
    
    def test_parse_history_list_command(self):
        """Test parsing history list command"""
        sys.argv = ['cli.py', 'history', 'list', '--limit', '50']
        args = parse_args()
        
        assert args.command == 'history'
        assert args.subcommand == 'list'
        assert args.limit == 50
    
    def test_parse_schedule_add_command(self):
        """Test parsing schedule add command"""
        sys.argv = ['cli.py', 'schedule', 'add', '+1234567890', 'Test message', '2024-12-25T10:00:00', '--recurring', 'daily', '--interval', '7']
        args = parse_args()
        
        assert args.command == 'schedule'
        assert args.subcommand == 'add'
        assert args.recipient == '+1234567890'
        assert args.message == 'Test message'
        assert args.time == '2024-12-25T10:00:00'
        assert args.recurring == 'daily'
        assert args.interval == 7
    
    def test_parse_services_list_command(self):
        """Test parsing services list command"""
        sys.argv = ['cli.py', 'services', 'list']
        args = parse_args()
        
        assert args.command == 'services'
        assert args.subcommand == 'list'
    
    def test_parse_services_configure_command(self):
        """Test parsing services configure command"""
        sys.argv = ['cli.py', 'services', 'configure', 'twilio', '--credentials', 'api_key:secret']
        args = parse_args()
        
        assert args.command == 'services'
        assert args.subcommand == 'configure'
        assert args.name == 'twilio'
        assert args.credentials == 'api_key:secret'


class TestMainFunction:
    """Test cases for main function"""
    
    def setup_method(self):
        """Set up test environment"""
        self.original_argv = sys.argv.copy()
    
    def teardown_method(self):
        """Clean up test environment"""
        sys.argv = self.original_argv
    
    @patch('src.cli.cli.SMSCommandLineInterface')
    def test_main_send_command(self, mock_cli_class):
        """Test main function with send command"""
        sys.argv = ['cli.py', 'send', '+1234567890', 'Hello World']
        
        mock_cli_instance = MagicMock()
        mock_cli_class.return_value = mock_cli_instance
        mock_cli_instance.send_message.return_value = True
        
        main()
        
        # Verify CLI was initialized and send_message was called
        mock_cli_class.assert_called_once()
        mock_cli_instance.send_message.assert_called_once_with('+1234567890', 'Hello World', None)
        mock_cli_instance.shutdown.assert_called_once()
    
    @patch('src.cli.cli.SMSCommandLineInterface')
    def test_main_contacts_list_command(self, mock_cli_class):
        """Test main function with contacts list command"""
        sys.argv = ['cli.py', 'contacts', 'list']
        
        mock_cli_instance = MagicMock()
        mock_cli_class.return_value = mock_cli_instance
        mock_cli_instance.list_contacts.return_value = True
        
        main()
        
        # Verify CLI was initialized and list_contacts was called
        mock_cli_class.assert_called_once()
        mock_cli_instance.list_contacts.assert_called_once()
        mock_cli_instance.shutdown.assert_called_once()
    
    @patch('src.cli.cli.SMSCommandLineInterface')
    def test_main_contacts_add_command(self, mock_cli_class):
        """Test main function with contacts add command"""
        sys.argv = ['cli.py', 'contacts', 'add', 'John Doe', '+1234567890', '--country', 'US', '--notes', 'Test contact']
        
        mock_cli_instance = MagicMock()
        mock_cli_class.return_value = mock_cli_instance
        mock_cli_instance.add_contact.return_value = True
        
        main()
        
        # Verify CLI was initialized and add_contact was called
        mock_cli_class.assert_called_once()
        mock_cli_instance.add_contact.assert_called_once_with('John Doe', '+1234567890', 'US', 'Test contact')
        mock_cli_instance.shutdown.assert_called_once()
    
    @patch('src.cli.cli.SMSCommandLineInterface')
    def test_main_no_command(self, mock_cli_class):
        """Test main function with no command (should show help)"""
        sys.argv = ['cli.py']
        
        mock_cli_instance = MagicMock()
        mock_cli_class.return_value = mock_cli_instance
        
        # Mock parse_args to handle help
        with patch('src.cli.cli.parse_args') as mock_parse_args:
            mock_parse_args.side_effect = [SystemExit(0)]  # argparse help exits
            
            with pytest.raises(SystemExit):
                main()
        
        # Verify CLI was initialized and shutdown was called
        mock_cli_class.assert_called_once()
        mock_cli_instance.shutdown.assert_called_once()
    
    @patch('src.cli.cli.SMSCommandLineInterface')
    def test_main_exception_handling(self, mock_cli_class):
        """Test main function exception handling"""
        sys.argv = ['cli.py', 'send', '+1234567890', 'Hello World']
        
        mock_cli_instance = MagicMock()
        mock_cli_class.return_value = mock_cli_instance
        mock_cli_instance.send_message.side_effect = Exception("Test error")
        
        # Should not raise exception, but should call shutdown
        main()
        
        # Verify CLI was initialized and shutdown was called despite error
        mock_cli_class.assert_called_once()
        mock_cli_instance.send_message.assert_called_once()
        mock_cli_instance.shutdown.assert_called_once()