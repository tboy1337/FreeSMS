"""
TextBelt SMS service implementation
"""
import os
import json
import requests
from typing import Dict, Any

from src.api.sms_service import SMSService, SMSResponse
from src.utils.logger import get_logger

class TextBeltService(SMSService):
    """TextBelt SMS service implementation"""
    
    def __init__(self):
        """Initialize the TextBelt service"""
        super().__init__("TextBelt", daily_limit=1)  # Free tier: 1 message per day
        self.logger = get_logger()
        self.api_key = None
        self.base_url = "https://textbelt.com/text"
        self.status_url = "https://textbelt.com/status"
        
        # Try to load credentials from environment variables
        self._load_env_credentials()
    
    def _load_env_credentials(self):
        """Load credentials from environment variables"""
        api_key = os.environ.get("TEXTBELT_API_KEY")
        
        if api_key:
            self.configure({"api_key": api_key})
    
    def configure(self, credentials: Dict[str, str]) -> bool:
        """
        Configure the TextBelt service with credentials
        
        Args:
            credentials: Dictionary with api_key
            
        Returns:
            True if configured successfully, False otherwise
        """
        try:
            self.api_key = credentials.get("api_key")
            
            if not self.api_key:
                self.logger.error("Missing TextBelt API key")
                return False
            
            # Validate credentials
            if not self.validate_credentials():
                self.logger.error("Invalid TextBelt API key")
                return False
            
            self.logger.info("TextBelt service configured successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring TextBelt: {e}")
            return False
    
    def send_sms(self, recipient: str, message: str) -> SMSResponse:
        """
        Send an SMS message using TextBelt
        
        Args:
            recipient: Recipient phone number (E.164 format)
            message: Message content
            
        Returns:
            SMSResponse with the result
        """
        if not self.api_key:
            return SMSResponse(
                success=False,
                error="TextBelt service not configured"
            )
        
        try:
            # Send the message
            response = requests.post(
                self.base_url,
                {
                    "phone": recipient,
                    "message": message,
                    "key": self.api_key
                },
                timeout=10
            )
            
            # Parse the response
            data = response.json()
            
            if data.get("success"):
                # Successful send
                return SMSResponse(
                    success=True,
                    message_id=data.get("textId"),
                    details={
                        "quotaRemaining": data.get("quotaRemaining"),
                        "timestamp": data.get("timestamp")
                    }
                )
            else:
                # Failed send
                return SMSResponse(
                    success=False,
                    error=data.get("error") or "Unknown error",
                    details=data
                )
            
        except requests.RequestException as e:
            self.logger.error(f"TextBelt API request error: {e}")
            return SMSResponse(
                success=False,
                error=f"API request error: {str(e)}"
            )
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing TextBelt response: {e}")
            return SMSResponse(
                success=False,
                error=f"Error parsing response: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Error sending SMS with TextBelt: {e}")
            return SMSResponse(
                success=False,
                error=f"Error: {str(e)}"
            )
    
    def check_balance(self) -> Dict[str, Any]:
        """
        Check the TextBelt account balance
        
        Returns:
            Dictionary with account details
        """
        if not self.api_key:
            return {"error": "TextBelt service not configured"}
        
        try:
            # Get quota information
            response = requests.get(
                f"{self.status_url}/quota/{self.api_key}",
                timeout=10
            )
            
            data = response.json()
            
            if response.status_code == 200:
                return {
                    "quota": data.get("quotaRemaining", 0),
                    "limit": data.get("quotaMax", 0)
                }
            else:
                return {"error": data.get("error") or "Unknown error"}
            
        except requests.RequestException as e:
            self.logger.error(f"TextBelt API request error: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing TextBelt response: {e}")
            return {"error": str(e)}
        except Exception as e:
            self.logger.error(f"Error checking TextBelt balance: {e}")
            return {"error": str(e)}
    
    def get_remaining_quota(self) -> int:
        """
        Get remaining daily message quota
        
        Returns:
            Number of messages remaining in quota
        """
        if not self.api_key:
            return 0
        
        try:
            # Get quota information
            response = requests.get(
                f"{self.status_url}/quota/{self.api_key}",
                timeout=10
            )
            
            data = response.json()
            
            if response.status_code == 200:
                return data.get("quotaRemaining", 0)
            
            return 0
            
        except Exception:
            return 0
    
    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get delivery status for a message
        
        Args:
            message_id: Message ID to check
            
        Returns:
            Dictionary with delivery status details
        """
        if not self.api_key:
            return {"status": "unknown", "error": "TextBelt service not configured"}
        
        try:
            # Get message status
            response = requests.get(
                f"{self.status_url}/{message_id}",
                timeout=10
            )
            
            data = response.json()
            
            if response.status_code == 200:
                delivery_state = "delivered" if data.get("status") == "DELIVERED" else "pending"
                
                return {
                    "status": delivery_state,
                    "details": data
                }
            else:
                return {"status": "error", "error": data.get("error") or "Unknown error"}
            
        except requests.RequestException as e:
            self.logger.error(f"TextBelt API request error: {e}")
            return {"status": "error", "error": str(e)}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing TextBelt response: {e}")
            return {"status": "error", "error": str(e)}
        except Exception as e:
            self.logger.error(f"Error checking message status: {e}")
            return {"status": "error", "error": str(e)}
    
    def validate_credentials(self) -> bool:
        """
        Validate that the TextBelt API key is correct
        
        Returns:
            True if API key is valid, False otherwise
        """
        if not self.api_key:
            return False
        
        try:
            # Try to get quota information
            response = requests.get(
                f"{self.status_url}/quota/{self.api_key}",
                timeout=10
            )
            
            # Consider it valid if we get a 200 status code
            return response.status_code == 200
            
        except Exception:
            return False 