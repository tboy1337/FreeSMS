#!/usr/bin/env python3
"""
Test script for FreeSMS API services with additional coverage
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests
from twilio.base.exceptions import TwilioRestException

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import application modules
from src.api.sms_service import SMSResponse, SMSService
from src.api.textbelt_service import TextBeltService
from src.api.twilio_service import TwilioService


class TestTextBeltServiceDetailed:
    """Test case for TextBelt Service with detailed coverage"""

    def setup_method(self):
        """Set up test environment"""
        # Mock requests module
        self.requests_patch = patch("requests.post")
        self.requests_get_patch = patch("requests.get")

        # Start the patches
        self.mock_post = self.requests_patch.start()
        self.mock_get = self.requests_get_patch.start()

        # Mock credentials
        self.credentials = {"api_key": "textbelt_test"}

        # Create service
        self.service = TextBeltService()

        # Skip actual validation
        with patch.object(self.service, "validate_credentials", return_value=True):
            self.service.configure(self.credentials)

    def teardown_method(self):
        """Clean up test environment"""
        self.requests_patch.stop()
        self.requests_get_patch.stop()

    def test_check_balance(self):
        """Test checking TextBelt balance"""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"quotaRemaining": 100, "quotaMax": 250}
        self.mock_get.return_value = mock_response

        # Check balance
        balance = self.service.check_balance()

        # Verify API was called
        self.mock_get.assert_called_once()

        # Verify response
        assert isinstance(balance, dict)
        assert balance["quota"] == 100
        assert balance["limit"] == 250

    def test_get_remaining_quota(self):
        """Test getting remaining quota"""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"quotaRemaining": 75, "quotaMax": 250}
        self.mock_get.return_value = mock_response

        # Get quota
        quota = self.service.get_remaining_quota()

        # Verify API was called
        self.mock_get.assert_called_once()

        # Verify response
        assert quota == 75

    def test_get_delivery_status(self):
        """Test getting message delivery status"""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "DELIVERED",  # API returns uppercase but method converts to lowercase
            "timestamp": "2023-07-01T12:30:45Z",
        }
        self.mock_get.return_value = mock_response

        # Get status
        status = self.service.get_delivery_status("TB12345")

        # Verify API was called
        self.mock_get.assert_called_once()

        # Verify response - the implementation converts "DELIVERED" to "delivered"
        assert isinstance(status, dict)
        assert status["status"] == "delivered"

        # Test with non-delivered status
        mock_response.json.return_value = {
            "status": "SENT",
            "timestamp": "2023-07-01T12:30:45Z",
        }

        # Reset mock and call again
        self.mock_get.reset_mock()
        status = self.service.get_delivery_status("TB12345")

        # Should return "pending" for any non-DELIVERED status
        assert status["status"] == "pending"

    def test_validate_credentials(self):
        """Test credentials validation"""
        # Set up the mock response for success - just needs 200 status code
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"quotaRemaining": 100, "quotaMax": 250}
        self.mock_get.return_value = mock_response

        # Validate credentials
        valid = self.service.validate_credentials()

        # Verify response
        assert valid

        # Test with invalid credentials (non-200 status code)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}

        # Validate credentials again
        valid = self.service.validate_credentials()

        # Verify response
        assert not valid

    def test_configure_with_invalid_credentials(self):
        """Test configuring with invalid credentials"""
        # Create a new service
        service = TextBeltService()

        # Mock validate_credentials to return False
        with patch.object(service, "validate_credentials", return_value=False):
            # Configure with invalid credentials
            result = service.configure({"api_key": "invalid"})

            # Verify result
            assert not result

    def test_configure_missing_api_key(self):
        """Test configuring with missing API key"""
        # Create a new service
        service = TextBeltService()

        # Configure with empty credentials
        result = service.configure({})

        # Verify result
        assert not result

    def test_configure_exception(self):
        """Test exception handling in configure method"""
        # Create a new service
        service = TextBeltService()

        # Mock validate_credentials to raise an exception
        with patch.object(
            service, "validate_credentials", side_effect=Exception("Test error")
        ):
            # Configure should handle the exception
            result = service.configure({"api_key": "test"})

            # Verify result
            assert not result

    def test_load_env_credentials(self):
        """Test loading credentials from environment variables"""
        # Mock os.environ.get to return a test API key
        with patch("os.environ.get", return_value="test_env_key"):
            # Mock configure to verify it's called with the right args
            with patch.object(
                TextBeltService, "configure", return_value=True
            ) as mock_configure:
                # Create service (which will call _load_env_credentials)
                service = TextBeltService()

                # Verify configure was called with the environment key
                mock_configure.assert_called_once_with({"api_key": "test_env_key"})

    def test_send_sms_unconfigured(self):
        """Test sending SMS without configuring first"""
        # Create service without configuring
        service = TextBeltService()
        service.api_key = None

        # Send SMS
        response = service.send_sms("+12125551234", "Test message")

        # Verify error response
        assert not response.success
        assert response.error == "TextBelt service not configured"

    def test_send_sms_request_exception(self):
        """Test handling of request exception when sending SMS"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock requests.post to raise an exception
        self.mock_post.side_effect = requests.RequestException("Connection error")

        # Send SMS
        response = self.service.send_sms("+12125551234", "Test message")

        # Verify error response
        assert not response.success
        assert "API request error" in response.error

    def test_send_sms_json_decode_error(self):
        """Test handling of JSON decode error when sending SMS"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock response that will cause a JSON decode error
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        self.mock_post.return_value = mock_response

        # Send SMS
        response = self.service.send_sms("+12125551234", "Test message")

        # Verify error response
        assert not response.success
        assert "Error parsing response" in response.error

    def test_send_sms_general_exception(self):
        """Test handling of general exception when sending SMS"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock requests.post to raise an unexpected exception
        self.mock_post.side_effect = Exception("Unexpected error")

        # Send SMS
        response = self.service.send_sms("+12125551234", "Test message")

        # Verify error response
        assert not response.success
        assert "Error:" in response.error

    def test_check_balance_unconfigured(self):
        """Test checking balance without configuring first"""
        # Create service without configuring
        service = TextBeltService()
        service.api_key = None

        # Check balance
        balance = service.check_balance()

        # Verify error response
        assert "error" in balance
        assert balance["error"] == "TextBelt service not configured"

    def test_check_balance_request_exception(self):
        """Test handling of request exception when checking balance"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock requests.get to raise an exception
        self.mock_get.side_effect = requests.RequestException("Connection error")

        # Check balance
        balance = self.service.check_balance()

        # Verify error response
        assert "error" in balance
        assert balance["error"] == "Connection error"

    def test_check_balance_json_decode_error(self):
        """Test handling of JSON decode error when checking balance"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock response that will cause a JSON decode error
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        self.mock_get.return_value = mock_response

        # Check balance
        balance = self.service.check_balance()

        # Verify error response
        assert "error" in balance
        assert "Invalid JSON" in balance["error"]

    def test_check_balance_error_response(self):
        """Test handling of error response when checking balance"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        self.mock_get.return_value = mock_response

        # Check balance
        balance = self.service.check_balance()

        # Verify error response
        assert "error" in balance
        assert balance["error"] == "Invalid API key"

    def test_get_remaining_quota_unconfigured(self):
        """Test getting quota without configuring first"""
        # Create service without configuring
        service = TextBeltService()
        service.api_key = None

        # Get quota
        quota = service.get_remaining_quota()

        # Verify zero is returned
        assert quota == 0

    def test_get_remaining_quota_exception(self):
        """Test handling of exception when getting quota"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock requests.get to raise an exception
        self.mock_get.side_effect = Exception("Test error")

        # Get quota
        quota = self.service.get_remaining_quota()

        # Verify zero is returned
        assert quota == 0

    def test_get_delivery_status_unconfigured(self):
        """Test getting delivery status without configuring first"""
        # Create service without configuring
        service = TextBeltService()
        service.api_key = None

        # Get status
        status = service.get_delivery_status("msg123")

        # Verify error response
        assert status["status"] == "unknown"
        assert status["error"] == "TextBelt service not configured"

    def test_get_delivery_status_request_exception(self):
        """Test handling of request exception when getting delivery status"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock requests.get to raise an exception
        self.mock_get.side_effect = requests.RequestException("Connection error")

        # Get status
        status = self.service.get_delivery_status("msg123")

        # Verify error response
        assert status["status"] == "error"
        assert status["error"] == "Connection error"

    def test_get_delivery_status_json_decode_error(self):
        """Test handling of JSON decode error when getting delivery status"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock response that will cause a JSON decode error
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        self.mock_get.return_value = mock_response

        # Get status
        status = self.service.get_delivery_status("msg123")

        # Verify error response
        assert status["status"] == "error"
        assert "Invalid JSON" in status["error"]

    def test_get_delivery_status_error_response(self):
        """Test handling of error response when getting delivery status"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Message not found"}
        self.mock_get.return_value = mock_response

        # Get status
        status = self.service.get_delivery_status("msg123")

        # Verify error response
        assert status["status"] == "error"
        assert status["error"] == "Message not found"

    def test_check_balance_general_exception(self):
        """Test handling of general exception when checking balance"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock to raise a non-requests, non-json exception
        self.mock_get.side_effect = ValueError("Unexpected error")

        # Check balance
        balance = self.service.check_balance()

        # Verify error response
        assert "error" in balance
        assert "Unexpected error" in balance["error"]

    def test_get_remaining_quota_http_error(self):
        """Test get_remaining_quota with HTTP error"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        self.mock_get.return_value = mock_response

        # Get quota
        quota = self.service.get_remaining_quota()

        # Verify returns 0 on error
        assert quota == 0

    def test_get_delivery_status_general_exception(self):
        """Test handling of general exception when getting delivery status"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock to raise a non-requests, non-json exception
        self.mock_get.side_effect = ValueError("Unexpected error")

        # Get status
        status = self.service.get_delivery_status("msg123")

        # Verify error response
        assert status["status"] == "error"
        assert "Unexpected error" in status["error"]

    def test_validate_credentials_no_api_key(self):
        """Test validate_credentials with no API key"""
        # Create service without API key
        service = TextBeltService()
        service.api_key = None

        # Validate credentials
        result = service.validate_credentials()

        # Should return False
        assert not result

    def test_validate_credentials_exception(self):
        """Test handling of exception in validate_credentials"""
        # Configure the service
        self.service.api_key = "test_key"

        # Mock to raise an exception
        self.mock_get.side_effect = Exception("Network error")

        # Validate credentials
        result = self.service.validate_credentials()

        # Should return False
        assert not result
