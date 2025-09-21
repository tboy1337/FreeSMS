"""
Base SMS service module and service response classes
"""
import abc
from typing import Dict, Any, Optional

class SMSResponse:
    """Class to represent an SMS service response"""
    
    def __init__(self, success: bool, message_id: str = None, error: str = None, details: Dict[str, Any] = None):
        """
        Initialize a new SMS response
        
        Args:
            success: Whether the message was sent successfully
            message_id: Unique message ID (for successful sends)
            error: Error message (for failed sends)
            details: Additional details or metadata
        """
        self.success = success
        self.message_id = message_id
        self.error = error
        self.details = details or {}
    
    def __str__(self) -> str:
        """String representation of the response"""
        if self.success:
            return f"Success: Message ID {self.message_id}"
        else:
            return f"Failed: {self.error}"

class SMSService(abc.ABC):
    """Abstract base class for SMS services"""
    
    def __init__(self, service_name: str, daily_limit: int = 0):
        """
        Initialize the SMS service
        
        Args:
            service_name: Display name of the service
            daily_limit: Maximum number of messages per day
        """
        self.service_name = service_name
        self.daily_limit = daily_limit
    
    @abc.abstractmethod
    def send_sms(self, recipient: str, message: str) -> SMSResponse:
        """
        Send an SMS message
        
        Args:
            recipient: Recipient phone number (E.164 format)
            message: Message content
            
        Returns:
            SMSResponse object with the result
        """
        pass
    
    @abc.abstractmethod
    def check_balance(self) -> Dict[str, Any]:
        """
        Check the account balance/status
        
        Returns:
            Dictionary with account details
        """
        pass
    
    @abc.abstractmethod
    def get_remaining_quota(self) -> int:
        """
        Get remaining daily message quota
        
        Returns:
            Number of messages remaining in quota
        """
        pass
    
    @abc.abstractmethod
    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get delivery status for a message
        
        Args:
            message_id: Message ID to check
            
        Returns:
            Dictionary with delivery status details
        """
        pass
    
    @abc.abstractmethod
    def validate_credentials(self) -> bool:
        """
        Validate that the API credentials are correct
        
        Returns:
            True if credentials are valid, False otherwise
        """
        pass 