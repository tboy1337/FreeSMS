#!/usr/bin/env python3
"""
Test script for FreeSMS service manager
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import application modules
from src.api.service_manager import SMSServiceManager
from src.api.sms_service import SMSResponse
from src.models.database import Database


class TestSMSServiceManager:
    """Test case for SMS Service Manager with detailed coverage"""
    
    def setup_method(self):
        """Set up test environment"""
        # Mock database
        self.db = MagicMock(spec=Database)
        
        # Set up API credentials
        self.db.get_api_credentials.side_effect = lambda service_name: {
            'twilio': {
                'account_sid': 'test_sid',
                'auth_token': 'test_token',
                'from_number': '+12345678901'
            },
            'textbelt': {
                'api_key': 'test_key'
            }
        }.get(service_name)
        
        # Set up active services
        self.db.get_active_services.return_value = ['twilio']
        
        # Mock importlib to avoid actual imports
        self.import_module_patcher = patch('importlib.import_module')
        self.mock_import_module = self.import_module_patcher.start()
        
        # Create mock modules and services
        self.mock_twilio_module = MagicMock()
        self.mock_textbelt_module = MagicMock()
        
        self.mock_twilio_service = MagicMock()
        self.mock_twilio_service.service_name = 'Twilio'
        self.mock_twilio_service.configure.return_value = True
        
        self.mock_textbelt_service = MagicMock()
        self.mock_textbelt_service.service_name = 'TextBelt'
        self.mock_textbelt_service.configure.return_value = True
        
        # Set up the mock modules to return mock service classes
        self.mock_twilio_module.TwilioService.return_value = self.mock_twilio_service
        self.mock_textbelt_module.TextBeltService.return_value = self.mock_textbelt_service
        
        # Set up the import_module to return the mock modules
        self.mock_import_module.side_effect = lambda name: {
            'src.api.twilio_service': self.mock_twilio_module,
            'src.api.textbelt_service': self.mock_textbelt_module
        }[name]
        
        # Create service manager
        self.manager = SMSServiceManager(self.db)
    
    def teardown_method(self):
        """Clean up test environment"""
        self.import_module_patcher.stop()
    
    def test_initialization(self):
        """Test service manager initialization"""
        # Check that services were loaded
        assert len(self.manager.services) == 2
        assert 'twilio' in self.manager.services
        assert 'textbelt' in self.manager.services
        
        # Check that active service was set
        assert self.manager.active_service == self.mock_twilio_service
        
        # Check that services were configured with credentials
        self.mock_twilio_service.configure.assert_called_once()
        self.mock_textbelt_service.configure.assert_called_once()
    
    def test_get_service_by_name(self):
        """Test getting service by name"""
        # Get existing service
        service = self.manager.get_service_by_name('twilio')
        assert service == self.mock_twilio_service
        
        # Get non-existent service
        service = self.manager.get_service_by_name('invalid')
        assert service is None
    
    def test_get_available_services(self):
        """Test getting available services"""
        services = self.manager.get_available_services()
        assert set(services) == {'twilio', 'textbelt'}
    
    def test_get_configured_services(self):
        """Test getting configured services"""
        # Both services should be configured
        services = self.manager.get_configured_services()
        assert set(services) == {'twilio', 'textbelt'}
        
        # Test with one service not configured
        self.db.get_api_credentials.side_effect = lambda service_name: {
            'twilio': {
                'account_sid': 'test_sid',
                'auth_token': 'test_token',
                'from_number': '+12345678901'
            },
            'textbelt': None
        }.get(service_name)
        
        services = self.manager.get_configured_services()
        assert services == ['twilio']
    
    def test_set_active_service(self):
        """Test setting active service"""
        # Set existing service
        result = self.manager.set_active_service('textbelt')
        assert result
        assert self.manager.active_service == self.mock_textbelt_service
        
        # Set non-existent service
        result = self.manager.set_active_service('invalid')
        assert not result
        assert self.manager.active_service == self.mock_textbelt_service
        
        # Verify database was updated
        self.db.save_api_credentials.assert_called_with('textbelt', 
                                                      {'api_key': 'test_key'}, 
                                                      is_active=True)
    
    def test_send_sms_with_active_service(self):
        """Test sending SMS with active service"""
        # Mock the response
        mock_response = MagicMock(spec=SMSResponse)
        mock_response.success = True
        mock_response.message_id = 'msg123'
        mock_response.details = {'status': 'sent'}
        
        self.mock_twilio_service.send_sms.return_value = mock_response
        
        # Send the message
        response = self.manager.send_sms('+12345678901', 'Test message')
        
        # Verify service was called
        self.mock_twilio_service.send_sms.assert_called_once_with('+12345678901', 'Test message')
        
        # Verify message history was saved
        self.db.save_message_history.assert_called_once()
    
    def test_send_sms_with_specific_service(self):
        """Test sending SMS with specific service"""
        # Mock the response
        mock_response = MagicMock(spec=SMSResponse)
        mock_response.success = True
        mock_response.message_id = 'msg123'
        mock_response.details = {'status': 'sent'}
        
        self.mock_textbelt_service.send_sms.return_value = mock_response
        
        # Send the message with specific service
        response = self.manager.send_sms('+12345678901', 'Test message', service_name='textbelt')
        
        # Verify service was called
        self.mock_textbelt_service.send_sms.assert_called_once_with('+12345678901', 'Test message')
        
        # Verify message history was saved
        self.db.save_message_history.assert_called_once()
    
    def test_send_sms_with_failed_response(self):
        """Test sending SMS with failed response"""
        # Mock the failed response
        mock_response = MagicMock(spec=SMSResponse)
        mock_response.success = False
        mock_response.error = 'Test error'
        
        self.mock_twilio_service.send_sms.return_value = mock_response
        
        # Send the message
        response = self.manager.send_sms('+12345678901', 'Test message')
        
        # Verify service was called
        self.mock_twilio_service.send_sms.assert_called_once_with('+12345678901', 'Test message')
        
        # Verify message history was saved as failed
        self.db.save_message_history.assert_called_once()
        args, kwargs = self.db.save_message_history.call_args
        assert kwargs['status'] == 'failed'
    
    def test_send_sms_with_exception(self):
        """Test sending SMS with exception"""
        # Make the service raise an exception
        self.mock_twilio_service.send_sms.side_effect = Exception('Test exception')
        
        # Send the message
        response = self.manager.send_sms('+12345678901', 'Test message')
        
        # Verify response is error
        assert not response.success
        assert response.error == 'Test exception'
        
        # Verify message history was saved as error
        self.db.save_message_history.assert_called_once()
        args, kwargs = self.db.save_message_history.call_args
        assert kwargs['status'] == 'error'
    
    def test_send_sms_with_no_service(self):
        """Test sending SMS with no service available"""
        # Set active service to None
        self.manager.active_service = None
        
        # Send the message
        response = self.manager.send_sms('+12345678901', 'Test message')
        
        # Verify response is error
        assert not response.success
        assert response.error == 'No SMS service configured'
        
        # Verify no service was called
        self.mock_twilio_service.send_sms.assert_not_called()
        self.mock_textbelt_service.send_sms.assert_not_called()
    
    def test_check_delivery_status(self):
        """Test checking delivery status"""
        # Mock the status response
        mock_status = {'status': 'delivered', 'timestamp': '2023-01-01T12:00:00Z'}
        self.mock_twilio_service.get_delivery_status.return_value = mock_status
        
        # Check status
        status = self.manager.check_delivery_status('msg123')
        
        # Verify service was called
        self.mock_twilio_service.get_delivery_status.assert_called_once_with('msg123')
        
        # Verify response
        assert status == mock_status
    
    def test_check_delivery_status_with_specific_service(self):
        """Test checking delivery status with specific service"""
        # Mock the status response
        mock_status = {'status': 'delivered', 'timestamp': '2023-01-01T12:00:00Z'}
        self.mock_textbelt_service.get_delivery_status.return_value = mock_status
        
        # Check status with specific service
        status = self.manager.check_delivery_status('msg123', service_name='textbelt')
        
        # Verify service was called
        self.mock_textbelt_service.get_delivery_status.assert_called_once_with('msg123')
        
        # Verify response
        assert status == mock_status
    
    def test_check_delivery_status_with_exception(self):
        """Test checking delivery status with exception"""
        # Make the service raise an exception
        self.mock_twilio_service.get_delivery_status.side_effect = Exception('Test exception')
        
        # Check status
        status = self.manager.check_delivery_status('msg123')
        
        # Verify response is error
        assert status['status'] == 'error'
        assert status['error'] == 'Test exception'
    
    def test_check_delivery_status_with_no_service(self):
        """Test checking delivery status with no service available"""
        # Set active service to None
        self.manager.active_service = None
        
        # Check status
        status = self.manager.check_delivery_status('msg123')
        
        # Verify response is error
        assert status['status'] == 'unknown'
        assert status['error'] == 'No SMS service configured'
        
        # Verify no service was called
        self.mock_twilio_service.get_delivery_status.assert_not_called()
        self.mock_textbelt_service.get_delivery_status.assert_not_called()


class TestSMSServiceManagerImportErrors:
    """Test case for SMS Service Manager import errors"""
    
    @patch('importlib.import_module')
    def test_load_services_with_import_error(self, mock_import):
        """Test loading services with import error"""
        # Set the mock to raise ImportError
        mock_import.side_effect = ImportError("Module not found")
        
        # Create a mock database
        db = MagicMock(spec=Database)
        db.get_active_services.return_value = []
        
        # Should not raise exception
        manager = SMSServiceManager(db)
        
        # Services should be empty
        assert len(manager.services) == 0
    
    def test_service_without_configure_method(self):
        """Test loading service that doesn't have configure method"""
        # Mock database with no active services initially
        db = MagicMock(spec=Database)
        db.get_active_services.return_value = []
        
        # Mock service that doesn't have configure method
        mock_service = MagicMock()
        del mock_service.configure  # Remove configure method
        
        mock_service_class = MagicMock(return_value=mock_service)
        mock_module = MagicMock()
        mock_module.TwilioService = mock_service_class
        
        db.get_api_credentials.return_value = {'test': 'credentials'}
        
        with patch('importlib.import_module', return_value=mock_module):
            manager = SMSServiceManager(db)
        
        # Service should still be loaded even without configure method
        assert 'twilio' in manager.services
        assert manager.services['twilio'] == mock_service
    
    def test_set_active_service_with_invalid_service_id(self):
        """Test setting active service with service ID not in loaded services"""
        # Mock database
        db = MagicMock(spec=Database)
        # Return a service ID that doesn't exist in loaded services
        db.get_active_services.return_value = ['invalid_service']
        
        # Mock import to only load 'twilio' service
        mock_service = MagicMock()
        mock_service_class = MagicMock(return_value=mock_service)
        mock_module = MagicMock()
        mock_module.TwilioService = mock_service_class
        
        with patch('importlib.import_module') as mock_import:
            mock_import.return_value = mock_module
            manager = SMSServiceManager(db)
        
        # Active service should remain None since 'invalid_service' is not in services
        assert manager.active_service is None
    
    def test_set_service_no_credentials(self):
        """Test setting service as active when no credentials are found"""
        # Mock database
        db = MagicMock(spec=Database)
        db.get_active_services.return_value = []  # No initial active services
        
        # Mock service
        mock_service = MagicMock()
        mock_service_class = MagicMock(return_value=mock_service)
        mock_module = MagicMock()
        mock_module.TwilioService = mock_service_class
        
        # Return None for credentials lookup
        db.get_api_credentials.return_value = None
        
        with patch('importlib.import_module', return_value=mock_module):
            manager = SMSServiceManager(db)
        
        # Manually set a service as active without credentials
        result = manager.set_active_service('twilio')
        
        # Should still return True and set active service
        assert result
        assert manager.active_service == mock_service
        
        # save_api_credentials should not be called without credentials
        db.save_api_credentials.assert_not_called()