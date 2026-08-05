"""
SMS service manager module
"""

import importlib
import threading
from typing import Any

from src.api.sms_service import SMSResponse, SMSService
from src.api.twilio_service import normalize_twilio_credentials
from src.models.database import Database
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
        self._lock = threading.RLock()
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
            "twilio": {"module": "src.api.twilio_service", "class": "TwilioService"},
            "textbelt": {
                "module": "src.api.textbelt_service",
                "class": "TextBeltService",
            },
        }

        # Load each service
        for service_id, service_info in services.items():
            try:
                # Import the module and class
                module = importlib.import_module(service_info["module"])
                service_class = getattr(module, service_info["class"])

                # Create an instance
                service = service_class()

                # Load credentials if available
                if credentials := self.db.get_api_credentials(service_id):
                    # Configure without network validation on reload
                    if hasattr(service, "configure"):
                        service.configure(credentials, validate=False)

                # Add to available services
                self.services[service_id] = service

            except (ImportError, AttributeError) as exc:
                self.logger.warning("Failed to load service %s: %s", service_id, exc)

    def _set_active_service(self):
        """Set the active SMS service"""
        if active_services := self.db.get_active_services():
            # Use the first active service
            if (service_id := active_services[0]) in self.services:
                self.active_service = self.services[service_id]
                self.logger.info("Active SMS service: %s", service_id)

    def get_service_by_name(self, service_name: str) -> SMSService | None:
        """
        Get a service by name

        Args:
            service_name: Service name

        Returns:
            SMSService instance or None if not found
        """
        return self.services.get(service_name)

    def get_available_services(self) -> list[str]:
        """
        Get names of available services

        Returns:
            List of service names
        """
        return list(self.services.keys())

    def _get_service_id(self, service: SMSService) -> str | None:
        """Return the registry key for a loaded service instance."""
        for service_id, loaded in self.services.items():
            if loaded is service:
                return service_id
        return None

    def get_active_service_id(self) -> str | None:
        """Return the registry key for the active service (thread-safe)."""
        with self._lock:
            if self.active_service is None:
                return None
            return self._get_service_id(self.active_service)

    def get_configured_services(self) -> list[str]:
        """
        Get names of services that have credentials configured

        Returns:
            List of configured service names
        """
        configured_services = []
        for service_name in self.services:
            if self.db.get_api_credentials(service_name):
                configured_services.append(service_name)
        return configured_services

    @staticmethod
    def _normalize_credentials(
        service_name: str, credentials: dict[str, str]
    ) -> dict[str, str]:
        """Normalize service-specific credential keys before save/configure."""
        if service_name == "twilio":
            return normalize_twilio_credentials(credentials)
        return dict(credentials)

    def get_active_service(self) -> SMSService | None:
        """Return the active service instance (thread-safe)."""
        with self._lock:
            return self.active_service

    def configure_service(
        self,
        service_name: str,
        credentials: dict[str, str],
        *,
        validate: bool = False,
    ) -> bool:
        """
        Configure an SMS service and persist credentials.

        Args:
            service_name: Service identifier (e.g. twilio, textbelt)
            credentials: Credential dictionary for the service
            validate: When True, validate credentials before saving

        Returns:
            True if configuration and persistence succeeded
        """
        if not (service := self.get_service_by_name(service_name)):
            self.logger.error("Service not found: %s", service_name)
            return False

        normalized = self._normalize_credentials(service_name, credentials)

        if hasattr(service, "configure"):
            if not service.configure(normalized, validate=validate):
                self.logger.error("Failed to configure service: %s", service_name)
                return False

        if not self.db.save_api_credentials(service_name, normalized):
            self.logger.error("Failed to save credentials for: %s", service_name)
            return False

        self.logger.info("Service configured successfully: %s", service_name)
        return True

    def set_active_service(self, service_name: str) -> bool:
        """
        Set the active SMS service

        Args:
            service_name: Service name

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if service_name not in self.services:
                self.logger.error("Service not found: %s", service_name)
                return False

            # Get service
            service = self.services[service_name]

            if not (credentials := self.db.get_api_credentials(service_name)):
                self.logger.error(
                    "No credentials configured for service: %s", service_name
                )
                return False

            self.db.save_api_credentials(service_name, credentials, is_active=True)
            self.active_service = service
            self.logger.info("Active SMS service set to: %s", service_name)
            return True

    def send_sms(
        self,
        recipient: str,
        message: str,
        service_name: str | None = None,
    ) -> SMSResponse:
        """
        Send an SMS message

        Args:
            recipient: Recipient phone number
            message: Message content
            service_name: Service to use (None for active service)

        Returns:
            SMSResponse with the result
        """
        with self._lock:
            if service_name:
                service = self.get_service_by_name(service_name)
            else:
                service = self.active_service

            if not service:
                self.logger.error("No SMS service available")
                return SMSResponse(success=False, error="No SMS service configured")

            service_id = self._get_service_id(service) or service.service_name

            try:
                daily_limit = int(service.daily_limit)
            except (TypeError, ValueError):
                daily_limit = 0

            if daily_limit > 0:
                sends_today = self.db.count_successful_sends_today(service_id)
                if sends_today >= daily_limit:
                    error_msg = (
                        f"Daily send limit reached for {service.service_name} "
                        f"({sends_today}/{service.daily_limit})"
                    )
                    self.logger.warning(error_msg)
                    return SMSResponse(success=False, error=error_msg)

        # Send outside the lock (network I/O)
        try:
            self.logger.info(
                "Sending SMS to %s using %s", recipient, service.service_name
            )
            response = service.send_sms(recipient, message)

            # Log to message history
            if response.success:
                self.db.save_message_history(
                    recipient=recipient,
                    message=message,
                    service=service_id,
                    status="sent",
                    message_id=response.message_id,
                    details=str(response.details),
                )
            else:
                self.db.save_message_history(
                    recipient=recipient,
                    message=message,
                    service=service_id,
                    status="failed",
                    details=response.error,
                )

            return response

        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            self.logger.error("Error sending SMS: %s", exc)
            error_response = SMSResponse(success=False, error=str(exc))

            service_id = self._get_service_id(service) or service.service_name
            self.db.save_message_history(
                recipient=recipient,
                message=message,
                service=service_id,
                status="error",
                details=str(exc),
            )

            return error_response
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Error sending SMS: %s", exc)
            error_response = SMSResponse(success=False, error=str(exc))

            service_id = self._get_service_id(service) or service.service_name
            self.db.save_message_history(
                recipient=recipient,
                message=message,
                service=service_id,
                status="error",
                details=str(exc),
            )

            return error_response

    def check_delivery_status(
        self, message_id: str, service_name: str | None = None
    ) -> dict[str, Any]:
        """
        Check delivery status of a message

        Args:
            message_id: Message ID to check
            service_name: Service to use (None for active service)

        Returns:
            Dictionary with delivery status details
        """
        # Use specified service or active service
        with self._lock:
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
            self.logger.info("Checking delivery status for message %s", message_id)
            return service.get_delivery_status(message_id)

        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            self.logger.error("Error checking delivery status: %s", exc)
            return {"status": "error", "error": str(exc)}
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Error checking delivery status: %s", exc)
            return {"status": "error", "error": str(exc)}
