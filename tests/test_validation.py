#!/usr/bin/env python3
"""
Test suite for validation.py module
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.security.validation import InputValidator


class TestInputValidator:
    """Test cases for InputValidator class"""
    
    def test_sanitize_text_empty(self):
        """Test sanitizing empty text"""
        result = InputValidator.sanitize_text("")
        assert result == ""
    
    def test_sanitize_text_none(self):
        """Test sanitizing None input"""
        result = InputValidator.sanitize_text(None)
        assert result == ""
    
    def test_sanitize_text_normal(self):
        """Test sanitizing normal text"""
        result = InputValidator.sanitize_text("Hello World")
        assert result == "Hello World"
    
    def test_sanitize_text_html_chars(self):
        """Test sanitizing text with HTML special characters"""
        result = InputValidator.sanitize_text("<script>alert('xss')</script>")
        assert result == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    
    def test_sanitize_text_ampersand(self):
        """Test sanitizing text with ampersand"""
        result = InputValidator.sanitize_text("Tom & Jerry")
        assert result == "Tom &amp; Jerry"
    
    def test_sanitize_text_quotes(self):
        """Test sanitizing text with quotes"""
        result = InputValidator.sanitize_text('He said "Hello"')
        assert result == "He said &quot;Hello&quot;"
    
    def test_validate_phone_input_empty(self):
        """Test validating empty phone number"""
        valid, error = InputValidator.validate_phone_input("")
        assert not valid
        assert error == "Phone number is required"
    
    def test_validate_phone_input_none(self):
        """Test validating None phone number"""
        valid, error = InputValidator.validate_phone_input(None)
        assert not valid
        assert error == "Phone number is required"
    
    def test_validate_phone_input_valid_formats(self):
        """Test validating various valid phone number formats"""
        valid_phones = [
            "+12125551234",
            "212-555-1234",
            "(212) 555-1234",
            "212.555.1234",
            "2125551234",
            "+1 212 555 1234"
        ]
        
        for phone in valid_phones:
            valid, error = InputValidator.validate_phone_input(phone)
            assert valid, f"Phone {phone} should be valid"
            assert error is None
    
    def test_validate_phone_input_invalid_characters(self):
        """Test validating phone number with invalid characters"""
        valid, error = InputValidator.validate_phone_input("212-555-abcd")
        assert not valid
        assert error == "Phone number should contain only digits, spaces, and + - ( ) characters"
    
    def test_validate_phone_input_too_short(self):
        """Test validating phone number that's too short"""
        valid, error = InputValidator.validate_phone_input("12345")
        assert not valid
        assert error == "Phone number length is invalid"
    
    def test_validate_phone_input_too_long(self):
        """Test validating phone number that's too long"""
        valid, error = InputValidator.validate_phone_input("1234567890123456")  # 16 digits
        assert not valid
        assert error == "Phone number length is invalid"
    
    def test_validate_message_empty(self):
        """Test validating empty message"""
        valid, error = InputValidator.validate_message("")
        assert not valid
        assert error == "Message text is required"
    
    def test_validate_message_none(self):
        """Test validating None message"""
        valid, error = InputValidator.validate_message(None)
        assert not valid
        assert error == "Message text is required"
    
    def test_validate_message_valid(self):
        """Test validating valid message"""
        valid, error = InputValidator.validate_message("Hello, this is a test message!")
        assert valid
        assert error is None
    
    def test_validate_message_max_length_default(self):
        """Test validating message at default max length"""
        message = "x" * 1600
        valid, error = InputValidator.validate_message(message)
        assert valid
        assert error is None
    
    def test_validate_message_exceeds_max_length_default(self):
        """Test validating message that exceeds default max length"""
        message = "x" * 1601
        valid, error = InputValidator.validate_message(message)
        assert not valid
        assert error == "Message exceeds maximum length of 1600 characters"
    
    def test_validate_message_custom_max_length(self):
        """Test validating message with custom max length"""
        message = "x" * 100
        valid, error = InputValidator.validate_message(message, max_length=50)
        assert not valid
        assert error == "Message exceeds maximum length of 50 characters"
    
    def test_validate_message_at_custom_max_length(self):
        """Test validating message exactly at custom max length"""
        message = "x" * 50
        valid, error = InputValidator.validate_message(message, max_length=50)
        assert valid
        assert error is None
    
    def test_validate_email_empty(self):
        """Test validating empty email"""
        valid, error = InputValidator.validate_email("")
        assert not valid
        assert error == "Email is required"
    
    def test_validate_email_none(self):
        """Test validating None email"""
        valid, error = InputValidator.validate_email(None)
        assert not valid
        assert error == "Email is required"
    
    def test_validate_email_valid_formats(self):
        """Test validating various valid email formats"""
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.uk",
            "first.last+tag@domain.org",
            "user123@test-domain.com",
            "a@b.co"
        ]
        
        for email in valid_emails:
            valid, error = InputValidator.validate_email(email)
            assert valid, f"Email {email} should be valid"
            assert error is None
    
    def test_validate_email_invalid_formats(self):
        """Test validating invalid email formats"""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user@example",
            "user@example.",
            "user name@example.com"
        ]
        
        for email in invalid_emails:
            valid, error = InputValidator.validate_email(email)
            assert not valid, f"Email {email} should be invalid"
            assert error == "Invalid email format"
    
    def test_validate_email_double_dots_accepted(self):
        """Test that email with double dots is accepted by the current regex"""
        # The current regex is permissive and allows this
        valid, error = InputValidator.validate_email("user..double.dot@example.com")
        assert valid
        assert error is None
    
    def test_sanitize_filename_normal(self):
        """Test sanitizing normal filename"""
        result = InputValidator.sanitize_filename("document.txt")
        assert result == "document.txt"
    
    def test_sanitize_filename_with_invalid_chars(self):
        """Test sanitizing filename with invalid characters"""
        result = InputValidator.sanitize_filename("doc<ument>file*.txt")
        assert result == "documentfile.txt"
    
    def test_sanitize_filename_with_path_traversal(self):
        """Test sanitizing filename with path traversal attempts"""
        result = InputValidator.sanitize_filename("../../../etc/passwd")
        assert result == "etcpasswd"
    
    def test_sanitize_filename_windows_paths(self):
        """Test sanitizing filename with Windows path characters"""
        result = InputValidator.sanitize_filename("C:\\Windows\\System32\\file.txt")
        assert result == "CWindowsSystem32file.txt"
    
    def test_sanitize_filename_empty_after_sanitization(self):
        """Test sanitizing filename that becomes empty after sanitization"""
        result = InputValidator.sanitize_filename("***///...")  # 3 dots -> "..." -> "." after removing ".."
        assert result == "."  # One dot remains, not empty
        
        # Test case that actually becomes empty
        result2 = InputValidator.sanitize_filename("***///..")  # 2 dots -> ".." -> "" after removing ".."
        assert result2 == "file"
    
    def test_sanitize_filename_just_dots(self):
        """Test sanitizing filename with just dots"""
        result = InputValidator.sanitize_filename("...")
        assert result == "."  # After removing "..", one "." remains
    
    def test_sanitize_filename_completely_invalid(self):
        """Test sanitizing filename with only invalid characters"""
        result = InputValidator.sanitize_filename("***///")
        assert result == "file"
    
    def test_validate_country_code_empty(self):
        """Test validating empty country code"""
        valid, error = InputValidator.validate_country_code("")
        assert not valid
        assert error == "Country code is required"
    
    def test_validate_country_code_none(self):
        """Test validating None country code"""
        valid, error = InputValidator.validate_country_code(None)
        assert not valid
        assert error == "Country code is required"
    
    def test_validate_country_code_valid_iso(self):
        """Test validating valid ISO country codes"""
        valid_codes = ["US", "UK", "CA", "FR", "DE", "us", "ca"]
        
        for code in valid_codes:
            valid, error = InputValidator.validate_country_code(code)
            assert valid, f"Country code {code} should be valid"
            assert error is None
    
    def test_validate_country_code_valid_phone_codes(self):
        """Test validating valid phone country codes"""
        valid_codes = ["+1", "+44", "+33", "+49", "+86"]
        
        for code in valid_codes:
            valid, error = InputValidator.validate_country_code(code)
            assert valid, f"Country code {code} should be valid"
            assert error is None
    
    def test_validate_country_code_invalid_formats(self):
        """Test validating invalid country code formats"""
        invalid_codes = ["USA", "A", "12", "U1", "++1", "+abc"]
        
        for code in invalid_codes:
            valid, error = InputValidator.validate_country_code(code)
            assert not valid, f"Country code {code} should be invalid"
            assert error == "Invalid country code format"
    
    def test_validate_api_key_empty(self):
        """Test validating empty API key"""
        valid, error = InputValidator.validate_api_key("")
        assert not valid
        assert error == "API key is required"
    
    def test_validate_api_key_none(self):
        """Test validating None API key"""
        valid, error = InputValidator.validate_api_key(None)
        assert not valid
        assert error == "API key is required"
    
    def test_validate_api_key_too_short(self):
        """Test validating API key that's too short"""
        valid, error = InputValidator.validate_api_key("1234567")  # 7 chars
        assert not valid
        assert error == "API key is too short"
    
    def test_validate_api_key_valid(self):
        """Test validating valid API keys"""
        valid_keys = [
            "abcd1234efgh5678",
            "sk_live_abcd1234",
            "test-key-123456",
            "API_KEY_123.456",
            "12345678"  # minimum length
        ]
        
        for key in valid_keys:
            valid, error = InputValidator.validate_api_key(key)
            assert valid, f"API key {key} should be valid"
            assert error is None
    
    def test_validate_api_key_invalid_characters(self):
        """Test validating API key with invalid characters"""
        invalid_keys = [
            "key with spaces",
            "key@with#symbols",
            "key/with\\slashes",
            "key(with)parens"
        ]
        
        for key in invalid_keys:
            valid, error = InputValidator.validate_api_key(key)
            assert not valid, f"API key {key} should be invalid"
            assert error == "API key contains invalid characters"
    
    def test_validate_date_format_empty(self):
        """Test validating empty date"""
        valid, error = InputValidator.validate_date_format("")
        assert not valid
        assert error == "Date is required"
    
    def test_validate_date_format_none(self):
        """Test validating None date"""
        valid, error = InputValidator.validate_date_format(None)
        assert not valid
        assert error == "Date is required"
    
    def test_validate_date_format_valid_default(self):
        """Test validating valid date with default format"""
        valid, error = InputValidator.validate_date_format("2023-12-25")
        assert valid
        assert error is None
    
    def test_validate_date_format_invalid_default(self):
        """Test validating invalid date with default format"""
        valid, error = InputValidator.validate_date_format("12/25/2023")
        assert not valid
        assert error == "Date must be in %Y-%m-%d format"
    
    def test_validate_date_format_custom_format(self):
        """Test validating date with custom format"""
        valid, error = InputValidator.validate_date_format("12/25/2023", "%m/%d/%Y")
        assert valid
        assert error is None
    
    def test_validate_date_format_invalid_custom(self):
        """Test validating invalid date with custom format"""
        valid, error = InputValidator.validate_date_format("2023-12-25", "%m/%d/%Y")
        assert not valid
        assert error == "Date must be in %m/%d/%Y format"
    
    def test_validate_time_format_empty(self):
        """Test validating empty time"""
        valid, error = InputValidator.validate_time_format("")
        assert not valid
        assert error == "Time is required"
    
    def test_validate_time_format_none(self):
        """Test validating None time"""
        valid, error = InputValidator.validate_time_format(None)
        assert not valid
        assert error == "Time is required"
    
    def test_validate_time_format_valid_default(self):
        """Test validating valid time with default format"""
        valid, error = InputValidator.validate_time_format("14:30")
        assert valid
        assert error is None
    
    def test_validate_time_format_invalid_default(self):
        """Test validating invalid time with default format"""
        valid, error = InputValidator.validate_time_format("2:30 PM")
        assert not valid
        assert error == "Time must be in %H:%M format"
    
    def test_validate_time_format_custom_format(self):
        """Test validating time with custom format"""
        valid, error = InputValidator.validate_time_format("2:30 PM", "%I:%M %p")
        assert valid
        assert error is None
    
    def test_validate_time_format_invalid_custom(self):
        """Test validating invalid time with custom format"""
        valid, error = InputValidator.validate_time_format("14:30", "%I:%M %p")
        assert not valid
        assert error == "Time must be in %I:%M %p format"