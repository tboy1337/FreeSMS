"""
Formatting utilities for SMS application
"""
import re
import phonenumbers
from typing import Tuple, Optional

def format_phone_number(phone: str, country_code: str = "US") -> Tuple[bool, Optional[str]]:
    """
    Format a phone number to E.164 format
    
    Args:
        phone: The phone number to format
        country_code: The ISO country code (default: "US")
        
    Returns:
        Tuple containing (success, formatted_number)
    """
    try:
        # If the phone doesn't start with +, add the country code
        if not phone.startswith('+'):
            # Parse with country code
            parsed = phonenumbers.parse(phone, country_code)
        else:
            # Parse as is if it has +
            parsed = phonenumbers.parse(phone, None)
            
        # Check if it's a valid number
        if not phonenumbers.is_valid_number(parsed):
            return False, None
            
        # Format to E.164 format
        formatted = phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164)
            
        return True, formatted
        
    except phonenumbers.NumberParseException:
        return False, None

def get_message_parts(message: str) -> Tuple[int, int]:
    """
    Calculate how many SMS parts a message will require
    
    Args:
        message: The message text
        
    Returns:
        Tuple containing (character_count, number_of_parts)
    """
    count = len(message)
    
    # GSM-7 encoding allows 160 chars per SMS
    # Unicode messages are limited to 70 chars per SMS
    
    # Check if message contains characters outside GSM-7 charset
    gsm_pattern = r'^[@£$¥èéùìòÇØøÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ!\"\#¤%&\'()*+,\-./:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà\s]*$'
    
    if re.match(gsm_pattern, message):
        # GSM-7 encoding
        chars_per_sms = 160
        chars_per_concat_sms = 153  # 160 - 7 bytes used for UDH header
    else:
        # Unicode encoding
        chars_per_sms = 70
        chars_per_concat_sms = 67  # 70 - 3 bytes used for UDH header
    
    if count <= chars_per_sms:
        parts = 1
    else:
        parts = (count + chars_per_concat_sms - 1) // chars_per_concat_sms
    
    return count, parts

def truncate_message(message: str, max_length: int = 160) -> str:
    """
    Truncate a message to a maximum length
    
    Args:
        message: The message text
        max_length: Maximum length (default: 160)
        
    Returns:
        Truncated message with ellipsis if needed
    """
    if len(message) <= max_length:
        return message
        
    return message[:max_length-3] + "..."

def format_delivery_time(timestamp: str) -> str:
    """
    Format a timestamp for display
    
    Args:
        timestamp: The timestamp string from database
        
    Returns:
        Formatted datetime string
    """
    from datetime import datetime
    
    try:
        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return timestamp or "N/A" 