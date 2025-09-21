"""
SMS service manager module
"""
import importlib
from typing import Dict, List, Optional, Any

from src.models.database import Database
from src.api.sms_service import SMSService, SMSResponse
from src.utils.logger import get_logger

class SMSServiceManager:
    """Manager for SMS service providers"""
    
    def __init__(self, db: Database):
        """
        Initialize the service manager
        
        Args:
            db: Database instance for storing credentials
        """
        self.db = db
        self.logger = get_logger()
        self.active_service = None
        self.services = {}
        
        # Load available services
        self._load_services()
        
        # Set active service
        self._set_active_service()
    
    def _load_services(self):
        """Load available SMS services"""
        # These would normally be discovered dynamically
        # For simplicity, we're hard-coding the available services
        services = {
            'twilio': {
                'module': 'src.api.twilio_service',
                'class': 'TwilioService'
            },
            'textbelt': {
                'module': 'src.api.textbelt_service',
                'class': 'TextBeltService'
            }
        }
        
        # Load each service
        for service_id, service_info in services.items():
            try:
                # Import the module and class
                module = importlib.import_module(service_info['module'])
                service_class = getattr(module, service_info['class'])
                
                # Create an instance
                service = service_class()
                
                # Load credentials if available
                credentials = self.db.get_api_credentials(service_id)
                if credentials:
                    # Configure the service with credentials
                    if hasattr(service, 'configure'):
                        service.configure(credentials)
                
                # Add to available services
                self.services[service_id] = service
                
            except (ImportError, AttributeError) as e:
                self.logger.warning(f"Failed to load service {service_id}: {e}")
    
    def _set_active_service(self):
        """Set the active SMS service"""
        active_services = self.db.get_active_services()
        
        if active_services:
            # Use the first active service
            service_id = active_services[0]
            if service_id in self.services:
                self.active_service = self.services[service_id]
                self.logger.info(f"Active SMS service: {service_id}")
    
    def get_service_by_name(self, service_name: str) -> Optional[SMSService]:
        """
        Get a service by name
        
        Args:
            service_name: Service name
            
        Returns:
            SMSService instance or None if not found
        """
        return self.services.get(service_name)
    
    def get_available_services(self) -> List[str]:
        """
        Get names of available services
        
        Returns:
            List of service names
        """
        return list(self.services.keys())
    
    def get_configured_services(self) -> List[str]:
        """
        Get names of services that have credentials configured
        
        Returns:
            List of configured service names
        """
        configured_services = []
        for service_name in self.services.keys():
            credentials = self.db.get_api_credentials(service_name)
            if credentials:
                configured_services.append(service_name)
        return configured_services
    
    def set_active_service(self, service_name: str) -> bool:
        """
        Set the active SMS service
        
        Args:
            service_name: Service name
            
        Returns:
            True if successful, False otherwise
        """
        if service_name not in self.services:
            self.logger.error(f"Service not found: {service_name}")
            return False
        
        # Get service
        service = self.services[service_name]
        
        # Update active service in database
        credentials = self.db.get_api_credentials(service_name)
        if credentials:
            self.db.save_api_credentials(service_name, credentials, is_active=True)
        
        # Set active service
        self.active_service = service
        self.logger.info(f"Active SMS service set to: {service_name}")
        return True
    
    def send_sms(self, recipient: str, message: str, service_name: str = None) -> SMSResponse:
        """
        Send an SMS message
        
        Args:
            recipient: Recipient phone number
            message: Message content
            service_name: Service to use (None for active service)
            
        Returns:
            SMSResponse with the result
        """
        # Use specified service or active service
        service = None
        if service_name:
            service = self.get_service_by_name(service_name)
        else:
            service = self.active_service
        
        # If no service available, return error
        if not service:
            self.logger.error("No SMS service available")
            return SMSResponse(
                success=False,
                error="No SMS service configured"
            )
        
        # Send the message
        try:
            self.logger.info(f"Sending SMS to {recipient} using {service.service_name}")
            response = service.send_sms(recipient, message)
            
            # Log to message history
            if response.success:
                self.db.save_message_history(
                    recipient=recipient,
                    message=message,
                    service=service.service_name,
                    status="sent",
                    message_id=response.message_id,
                    details=str(response.details)
                )
            else:
                self.db.save_message_history(
                    recipient=recipient,
                    message=message,
                    service=service.service_name,
                    status="failed",
                    details=response.error
                )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error sending SMS: {e}")
            error_response = SMSResponse(
                success=False,
                error=str(e)
            )
            
            # Log to message history
            self.db.save_message_history(
                recipient=recipient,
                message=message,
                service=service.service_name,
                status="error",
                details=str(e)
            )
            
            return error_response
    
    def check_delivery_status(self, message_id: str, service_name: str = None) -> Dict[str, Any]:
        """
        Check delivery status of a message
        
        Args:
            message_id: Message ID to check
            service_name: Service to use (None for active service)
            
        Returns:
            Dictionary with delivery status details
        """
        # Use specified service or active service
        service = None
        if service_name:
            service = self.get_service_by_name(service_name)
        else:
            service = self.active_service
        
        # If no service available, return error
        if not service:
            self.logger.error("No SMS service available")
            return {"status": "unknown", "error": "No SMS service configured"}
        
        # Check delivery status
        try:
            self.logger.info(f"Checking delivery status for message {message_id}")
            return service.get_delivery_status(message_id)
            
        except Exception as e:
            self.logger.error(f"Error checking delivery status: {e}")
            return {"status": "error", "error": str(e)} 