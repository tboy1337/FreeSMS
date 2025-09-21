"""
Twilio SMS service implementation
"""
import os
from typing import Dict, Any, Optional

from twilio.rest import Client

try:
    from twilio.base.exceptions import TwilioRestException
except ImportError:
    # Fallback for test environments or when Twilio is not fully available
    TwilioRestException = Exception

from src.api.sms_service import SMSService, SMSResponse
from src.utils.logger import get_logger

class TwilioService(SMSService):
    """Twilio SMS service implementation"""
    
    def __init__(self):
        """Initialize the Twilio service"""
        super().__init__("Twilio", daily_limit=100)  # Default daily limit for free tier
        self.logger = get_logger()
        self.client = None
        self.from_number = None
        self.account_sid = None
        self.auth_token = None
        
        # Try to load credentials from environment variables
        self._load_env_credentials()
    
    def _load_env_credentials(self):
        """Load credentials from environment variables"""
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_PHONE_NUMBER")
        
        if account_sid and auth_token and from_number:
            self.configure({
                "account_sid": account_sid,
                "auth_token": auth_token,
                "from_number": from_number
            })
    
    def configure(self, credentials: Dict[str, str], validate: bool = False) -> bool:
        """
        Configure the Twilio service with credentials
        
        Args:
            credentials: Dictionary with account_sid, auth_token, and from_number
            validate: Whether to validate credentials after configuration
            
        Returns:
            True if configured successfully, False otherwise
        """
        try:
            self.account_sid = credentials.get("account_sid")
            self.auth_token = credentials.get("auth_token")
            self.from_number = credentials.get("from_number")
            
            if not all([self.account_sid, self.auth_token, self.from_number]):
                self.logger.error("Missing required Twilio credentials")
                return False
            
            # Create Twilio client
            self.client = Client(self.account_sid, self.auth_token)
            
            # Optionally validate credentials
            if validate and not self.validate_credentials():
                self.logger.error("Invalid Twilio credentials")
                return False
            
            self.logger.info("Twilio service configured successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring Twilio: {e}")
            return False
    
    def send_sms(self, recipient: str, message: str) -> SMSResponse:
        """
        Send an SMS message using Twilio
        
        Args:
            recipient: Recipient phone number (E.164 format)
            message: Message content
            
        Returns:
            SMSResponse with the result
        """
        if not self.client:
            return SMSResponse(
                success=False,
                error="Twilio service not configured"
            )
        
        try:
            # Send the message
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=recipient
            )
            
            # Return success response
            return SMSResponse(
                success=True,
                message_id=twilio_message.sid,
                details={
                    "status": getattr(twilio_message, 'status', 'sent'),
                    "price": getattr(twilio_message, 'price', '0.00'),
                    "price_unit": getattr(twilio_message, 'price_unit', 'USD'),
                    "date_created": str(getattr(twilio_message, 'date_created', ''))
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error sending SMS with Twilio: {e}")
            # Check if it's a TwilioRestException
            if hasattr(e, 'msg') and hasattr(e, 'code'):
                return SMSResponse(
                    success=False,
                    error=f"Twilio API error: {e.msg}",
                    details={
                        "code": e.code,
                        "status": getattr(e, 'status', None),
                        "more_info": getattr(e, 'more_info', None)
                    }
                )
            else:
                return SMSResponse(
                    success=False,
                    error=f"Error: {str(e)}"
                )
    
    def check_balance(self) -> Dict[str, Any]:
        """
        Check the Twilio account balance
        
        Returns:
            Dictionary with account details
        """
        if not self.client:
            return {"error": "Twilio service not configured"}
        
        try:
            # Get account details
            account = self.client.api.accounts(self.account_sid).fetch()
            
            # Get actual balance
            balance = self.client.api.accounts(self.account_sid).balance.fetch()
            
            return {
                "balance": float(balance.balance),
                "currency": balance.currency,
                "status": getattr(account, 'status', 'active'),
                "type": getattr(account, 'type', 'standard')
            }
            
        except Exception as e:
            self.logger.error(f"Error checking balance: {e}")
            # Check if it's a TwilioRestException
            if hasattr(e, 'msg') and hasattr(e, 'code'):
                return {"error": f"Twilio API error: {e.msg}"}
            else:
                return {"error": f"Error: {str(e)}"}
    
    def get_remaining_quota(self) -> int:
        """
        Get remaining daily message quota
        
        Returns:
            Number of messages remaining in daily quota
        """
        # For paid Twilio accounts, there's no daily limit concept
        # Return the configured limit for consistency
        return self.daily_limit
    
    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get delivery status for a message
        
        Args:
            message_id: Message ID (SID) to check
            
        Returns:
            Dictionary with status details
        """
        if not self.client:
            return {"status": "unknown", "error": "Twilio service not configured"}
        
        try:
            # Get message details
            message = self.client.messages(message_id).fetch()
            
            # Map Twilio status to our status vocabulary
            status_mapping = {
                "queued": "pending",
                "sending": "pending",
                "sent": "sent",
                "delivered": "delivered",
                "undelivered": "failed",
                "failed": "failed"
            }
            
            mapped_status = status_mapping.get(message.status, message.status)
            
            return {
                "status": mapped_status,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "date_sent": str(message.date_sent) if message.date_sent else None,
                "date_updated": str(message.date_updated) if message.date_updated else None
            }
            
        except Exception as e:
            self.logger.error(f"Error checking message status: {e}")
            # Check if it's a TwilioRestException
            if hasattr(e, 'msg') and hasattr(e, 'code'):
                return {"status": "error", "error": f"Twilio API error: {e.msg}"}
            else:
                return {"status": "error", "error": f"Error: {str(e)}"}
    
    def validate_credentials(self) -> bool:
        """
        Validate Twilio credentials
        
        Returns:
            True if credentials are valid, False otherwise
        """
        if not self.client:
            return False
            
        try:
            # Try to fetch the account to validate credentials
            self.client.api.accounts(self.account_sid).fetch()
            return True
            
        except Exception as e:
            # Check if it's a TwilioRestException
            if hasattr(e, 'msg') and hasattr(e, 'code'):
                self.logger.error(f"Twilio authentication error: {e}")
            else:
                self.logger.error(f"Error validating Twilio credentials: {e}")
            return False 