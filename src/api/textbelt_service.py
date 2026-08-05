"""
TextBelt SMS service implementation
"""

import json
import os
from typing import Any

import requests

from src.api.sms_service import SMSResponse, SMSService
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
        if api_key := os.environ.get("TEXTBELT_API_KEY"):
            self.configure({"api_key": api_key})

    def configure(self, credentials: dict[str, str], validate: bool = False) -> bool:
        """
        Configure the TextBelt service with credentials

        Args:
            credentials: Dictionary with api_key
            validate: Whether to validate credentials after configuration

        Returns:
            True if configured successfully, False otherwise
        """
        try:
            self.api_key = credentials.get("api_key")

            if not self.api_key:
                self.logger.error("Missing TextBelt API key")
                return False

            if validate and not self.validate_credentials():
                self.logger.error("Invalid TextBelt API key")
                return False

            self.logger.info("TextBelt service configured successfully")
            return True

        except (OSError, ValueError, TypeError) as exc:
            self.logger.error("Error configuring TextBelt: %s", exc)
            return False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Error configuring TextBelt: %s", exc)
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
            return SMSResponse(success=False, error="TextBelt service not configured")

        try:
            # Send the message
            response = requests.post(
                self.base_url,
                {"phone": recipient, "message": message, "key": self.api_key},
                timeout=10,
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
                        "timestamp": data.get("timestamp"),
                    },
                )

            # Failed send
            return SMSResponse(
                success=False,
                error=data.get("error") or "Unknown error",
                details=data,
            )

        except requests.RequestException as exc:
            self.logger.error("TextBelt API request error: %s", exc)
            return SMSResponse(success=False, error=f"API request error: {exc!s}")
        except json.JSONDecodeError as exc:
            self.logger.error("Error parsing TextBelt response: %s", exc)
            return SMSResponse(success=False, error=f"Error parsing response: {exc!s}")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Unexpected TextBelt send error: %s", exc)
            return SMSResponse(success=False, error=f"Error: {exc!s}")

    def check_balance(self) -> dict[str, Any]:
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
                f"{self.status_url}/quota/{self.api_key}", timeout=10
            )

            data = response.json()

            if response.status_code == 200:
                return {
                    "quota": data.get("quotaRemaining", 0),
                    "limit": data.get("quotaMax", 0),
                }

            return {"error": data.get("error") or "Unknown error"}

        except requests.RequestException as exc:
            self.logger.error("TextBelt API request error: %s", exc)
            return {"error": str(exc)}
        except json.JSONDecodeError as exc:
            self.logger.error("Error parsing TextBelt response: %s", exc)
            return {"error": str(exc)}
        except (ValueError, TypeError) as exc:
            self.logger.error("Unexpected TextBelt balance error: %s", exc)
            return {"error": str(exc)}

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
                f"{self.status_url}/quota/{self.api_key}", timeout=10
            )

            data = response.json()

            if response.status_code == 200:
                return data.get("quotaRemaining", 0)

            return 0

        except (requests.RequestException, json.JSONDecodeError, KeyError, TypeError):
            return 0
        except Exception:  # pylint: disable=broad-exception-caught
            return 0

    def get_delivery_status(self, message_id: str) -> dict[str, Any]:
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
            response = requests.get(f"{self.status_url}/{message_id}", timeout=10)

            data = response.json()

            if response.status_code == 200:
                delivery_state = (
                    "delivered" if data.get("status") == "DELIVERED" else "pending"
                )

                return {"status": delivery_state, "details": data}

            return {
                "status": "error",
                "error": data.get("error") or "Unknown error",
            }

        except requests.RequestException as exc:
            self.logger.error("TextBelt API request error: %s", exc)
            return {"status": "error", "error": str(exc)}
        except json.JSONDecodeError as exc:
            self.logger.error("Error parsing TextBelt response: %s", exc)
            return {"status": "error", "error": str(exc)}
        except (ValueError, TypeError) as exc:
            self.logger.error("Unexpected TextBelt status error: %s", exc)
            return {"status": "error", "error": str(exc)}

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
                f"{self.status_url}/quota/{self.api_key}", timeout=10
            )

            # Consider it valid if we get a 200 status code
            return response.status_code == 200

        except requests.RequestException:
            return False
        except Exception:  # pylint: disable=broad-exception-caught
            return False
