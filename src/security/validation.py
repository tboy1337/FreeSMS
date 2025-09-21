"""
Input Validation - Security utilities for validating user input
"""
import re
import html
from typing import Tuple, Optional, Any

class InputValidator:
    """Input validation utilities for secure data handling"""
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text input to prevent HTML/script injection"""
        if not text:
            return ""
        # Escape HTML special characters
        return html.escape(text)
    
    @staticmethod
    def validate_phone_input(phone: str) -> Tuple[bool, Optional[str]]:
        """Validate a phone number input format"""
        if not phone:
            return False, "Phone number is required"
            
        # Remove common formatting characters for validation
        clean_phone = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Check if it's a reasonable phone number
        # This is a basic validation; the phonenumbers library will do more thorough validation
        if not clean_phone.replace('+', '').isdigit():
            return False, "Phone number should contain only digits, spaces, and + - ( ) characters"
            
        if len(clean_phone) < 7 or len(clean_phone) > 15:
            return False, "Phone number length is invalid"
            
        return True, None
    
    @staticmethod
    def validate_message(message: str, max_length: int = 1600) -> Tuple[bool, Optional[str]]:
        """Validate a message to ensure it meets requirements"""
        if not message:
            return False, "Message text is required"
            
        if len(message) > max_length:
            return False, f"Message exceeds maximum length of {max_length} characters"
            
        return True, None
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Validate an email address format"""
        if not email:
            return False, "Email is required"
            
        # Simple regex for email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
            
        return True, None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize a filename to prevent path traversal attacks"""
        # Remove any directory components
        safe_name = re.sub(r'[\\/*?:"<>|]', '', filename)
        safe_name = safe_name.replace('..', '')
        
        # Ensure it's not empty after sanitization
        if not safe_name:
            safe_name = "file"
            
        return safe_name
    
    @staticmethod
    def validate_country_code(country_code: str) -> Tuple[bool, Optional[str]]:
        """Validate a country code"""
        if not country_code:
            return False, "Country code is required"
            
        # Clean the country code
        clean_code = country_code.strip().upper()
        
        # Simple validation for standard 2-letter ISO country codes
        if len(clean_code) == 2 and clean_code.isalpha():
            return True, None
            
        # For longer codes that include the + and digits
        if clean_code.startswith('+') and clean_code[1:].isdigit():
            return True, None
            
        return False, "Invalid country code format"
    
    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
        """Validate an API key format"""
        if not api_key:
            return False, "API key is required"
            
        # Basic validation - API keys are typically alphanumeric
        # Different services have different formats
        if len(api_key) < 8:
            return False, "API key is too short"
            
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', api_key):
            return False, "API key contains invalid characters"
            
        return True, None
    
    @staticmethod
    def validate_date_format(date_str: str, expected_format: str = '%Y-%m-%d') -> Tuple[bool, Optional[str]]:
        """Validate a date string format"""
        import datetime
        
        if not date_str:
            return False, "Date is required"
            
        try:
            datetime.datetime.strptime(date_str, expected_format)
            return True, None
        except ValueError:
            return False, f"Date must be in {expected_format} format"
    
    @staticmethod
    def validate_time_format(time_str: str, expected_format: str = '%H:%M') -> Tuple[bool, Optional[str]]:
        """Validate a time string format"""
        import datetime
        
        if not time_str:
            return False, "Time is required"
            
        try:
            datetime.datetime.strptime(time_str, expected_format)
            return True, None
        except ValueError:
            return False, f"Time must be in {expected_format} format" 