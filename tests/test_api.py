#!/usr/bin/env python3
"""
Test script for FreeSMS API services
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.api.sms_service import SMSService, SMSResponse
from src.api.service_manager import SMSServiceManager
from src.api.twilio_service import TwilioService
from src.api.textbelt_service import TextBeltService

class TestSMSResponse(unittest.TestCase):
    """Test case for SMS Response class"""
    
    def test_success_response(self):
        """Test successful SMS response"""
        response = SMSResponse(
            success=True,
            message_id="msg123",
            details={"status": "sent", "cost": 0.01}
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.message_id, "msg123")
        self.assertEqual(response.details["status"], "sent")
        self.assertIsNone(response.error)
        
        # Test string representation
        response_str = str(response)
        self.assertIn("Success", response_str)
        self.assertIn("msg123", response_str)
    
    def test_error_response(self):
        """Test error SMS response"""
        response = SMSResponse(
            success=False,
            error="Authentication failed",
            details={"code": 401, "reason": "Invalid credentials"}
        )
        
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Authentication failed")
        self.assertEqual(response.details["code"], 401)
        self.assertIsNone(response.message_id)
        
        # Test string representation
        response_str = str(response)
        self.assertIn("Failed", response_str)
        self.assertIn("Authentication failed", response_str)

class MockSMSService(SMSService):
    """Mock implementation of SMSService for testing"""
    
    def __init__(self, service_name="Mock SMS Service"):
        super().__init__(service_name)
    
    def send_sms(self, recipient, message):
        return SMSResponse(True, "mock-msg-123")
    
    def check_balance(self):
        return {"balance": 100}
    
    def get_remaining_quota(self):
        return 50
    
    def get_delivery_status(self, message_id):
        return {"status": "delivered"}
    
    def validate_credentials(self):
        return True

class TestSMSService(unittest.TestCase):
    """Test case for base SMS Service class"""
    
    def test_mock_service(self):
        """Test mock service implementation"""
        # Create instance of mock service
        service = MockSMSService()
        
        # Test service properties
        self.assertEqual(service.service_name, "Mock SMS Service")
        self.assertEqual(service.daily_limit, 0)
        
        # Test implemented methods
        response = service.send_sms("+12125551234", "Test message")
        self.assertTrue(response.success)
        
        balance = service.check_balance()
        self.assertEqual(balance["balance"], 100)
        
        quota = service.get_remaining_quota()
        self.assertEqual(quota, 50)
        
        status = service.get_delivery_status("msg-123")
        self.assertEqual(status["status"], "delivered")
        
        valid = service.validate_credentials()
        self.assertTrue(valid)

class TestTwilioService(unittest.TestCase):
    """Test case for Twilio Service"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock the twilio.rest.Client completely
        self.mock_client_patcher = patch('twilio.rest.Client')
        self.mock_client_class = self.mock_client_patcher.start()
        
        # Mock the TwilioRestException
        self.mock_exception_patcher = patch('twilio.base.exceptions.TwilioRestException')
        self.mock_twilio_exception = self.mock_exception_patcher.start()
        
        # Mock credentials
        self.credentials = {
            "account_sid": "AC123",
            "auth_token": "token123",
            "from_number": "+15551234567"
        }
        
        # Create the service
        self.service = TwilioService()
        
        # Skip actual validation in configure method
        with patch.object(self.service, 'validate_credentials', return_value=True):
            self.service.configure(self.credentials)
    
    def tearDown(self):
        """Clean up test environment"""
        self.mock_client_patcher.stop()
        self.mock_exception_patcher.stop()
    
    def test_service_properties(self):
        """Test service properties"""
        self.assertEqual(self.service.service_name, "Twilio")
    
    @patch.object(TwilioService, 'validate_credentials')
    def test_configure(self, mock_validate):
        """Test service configuration"""
        # Set validate_credentials to return True
        mock_validate.return_value = True
        
        # Create a new service
        service = TwilioService()
        
        # Configure it
        result = service.configure(self.credentials)
        
        # Check that it was configured correctly
        self.assertTrue(result)
        self.assertEqual(service.account_sid, "AC123")
        self.assertEqual(service.auth_token, "token123")
        self.assertEqual(service.from_number, "+15551234567")
    
    def test_send_sms(self):
        """Test sending message via Twilio"""
        # Mock the client and message response
        mock_client = MagicMock()
        self.mock_client_class.return_value = mock_client
        
        # Create mock message response
        mock_message = MagicMock()
        mock_message.sid = "SM123"
        mock_message.status = "sent"
        mock_message.error_code = None
        mock_message.error_message = None
        
        # Set up the mock to return our message
        mock_client.messages.create.return_value = mock_message
        
        # Mock the service.client with our mock client
        self.service.client = mock_client
        
        # Test sending a message
        response = self.service.send_sms("+12125551234", "Test message")
        
        # Verify the response
        self.assertTrue(response.success)
        self.assertEqual(response.message_id, "SM123")
        self.assertEqual(response.details["status"], "sent")
        
        # Verify the client was called correctly
        mock_client.messages.create.assert_called_once()
        args, kwargs = mock_client.messages.create.call_args
        self.assertEqual(kwargs["to"], "+12125551234")
        self.assertEqual(kwargs["from_"], "+15551234567")
        self.assertEqual(kwargs["body"], "Test message")
    
    def test_send_sms_error(self):
        """Test sending message with error"""
        # Mock the client
        mock_client = MagicMock()
        
        # Set the client on the service
        self.service.client = mock_client
        
        # Make the client raise a general exception
        mock_client.messages.create.side_effect = Exception("API Error")
        
        # Test sending message
        response = self.service.send_sms("+12125551234", "Test message")
        
        # Verify response
        self.assertFalse(response.success)
        self.assertIn("API Error", response.error)

class TestTextBeltService(unittest.TestCase):
    """Test case for TextBelt Service"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock requests module
        self.requests_patch = patch('requests.post')
        self.requests_get_patch = patch('requests.get')
        
        # Start the patches
        self.mock_post = self.requests_patch.start()
        self.mock_get = self.requests_get_patch.start()
        
        # Mock credentials
        self.credentials = {
            "api_key": "textbelt_test"
        }
        
        # Create service
        self.service = TextBeltService()
        
        # Skip actual validation
        with patch.object(self.service, 'validate_credentials', return_value=True):
            self.service.configure(self.credentials)
    
    def tearDown(self):
        """Clean up test environment"""
        self.requests_patch.stop()
        self.requests_get_patch.stop()
    
    def test_service_properties(self):
        """Test service properties"""
        self.assertEqual(self.service.service_name, "TextBelt")
    
    def test_send_sms(self):
        """Test sending message via TextBelt"""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "textId": "TB123",
            "quotaRemaining": 99
        }
        self.mock_post.return_value = mock_response
        
        # Send a test message
        response = self.service.send_sms("+12125551234", "Test message")
        
        # Verify the response
        self.assertTrue(response.success)
        self.assertEqual(response.message_id, "TB123")
        self.assertEqual(response.details["quotaRemaining"], 99)
        
        # Verify API was called correctly
        self.mock_post.assert_called_once()
        call_args = self.mock_post.call_args
        
        # The first positional argument should be the URL
        self.assertEqual(call_args[0][0], "https://textbelt.com/text")
        
        # Extract the payload data (could be in 'data' or as a positional argument)
        if hasattr(call_args, 'kwargs') and call_args.kwargs.get('data'):
            payload = call_args.kwargs.get('data')
        else:
            # If not in kwargs, it might be the second positional argument
            payload = call_args[0][1] if len(call_args[0]) > 1 else None
        
        # Now verify the payload data
        self.assertIsNotNone(payload, "Payload data is missing in the API call")
        if payload:  # Only run these assertions if we found the payload
            self.assertEqual(payload.get("phone"), "+12125551234")
            self.assertEqual(payload.get("message"), "Test message")
            self.assertEqual(payload.get("key"), "textbelt_test")
    
    def test_send_sms_error(self):
        """Test sending message with error"""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Invalid phone number"
        }
        self.mock_post.return_value = mock_response
        
        # Send a test message
        response = self.service.send_sms("+12125551234", "Test message")
        
        # Verify the response
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Invalid phone number")

class TestSMSServiceManager(unittest.TestCase):
    """Test case for SMS Service Manager"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock database
        self.db = MagicMock()
        self.db.get_active_services.return_value = []
        self.db.get_api_credentials.return_value = None
        
        # Create service manager
        self.manager = SMSServiceManager(self.db)
    
    def test_get_available_services(self):
        """Test getting available services"""
        services = self.manager.get_available_services()
        self.assertIsInstance(services, list)
        self.assertIn("twilio", services)
        self.assertIn("textbelt", services)
    
    def test_get_service_by_name(self):
        """Test getting service by name"""
        # Get Twilio service
        twilio = self.manager.get_service_by_name("twilio")
        self.assertIsNotNone(twilio)
        self.assertEqual(twilio.service_name, "Twilio")
        
        # Get TextBelt service
        textbelt = self.manager.get_service_by_name("textbelt")
        self.assertIsNotNone(textbelt)
        self.assertEqual(textbelt.service_name, "TextBelt")
        
        # Get non-existent service
        none_service = self.manager.get_service_by_name("nonexistent")
        self.assertIsNone(none_service)
    
    def test_set_active_service(self):
        """Test setting active service"""
        # Mock get_api_credentials to return credentials
        self.db.get_api_credentials.return_value = {"api_key": "test"}
        
        # Set active service
        result = self.manager.set_active_service("twilio")
        self.assertTrue(result)
        
        # Verify active service was set
        self.assertEqual(self.manager.active_service.service_name, "Twilio")
        
        # Test with invalid service name
        result = self.manager.set_active_service("nonexistent")
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main() 