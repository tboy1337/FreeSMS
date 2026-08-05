"""
Shared application service initialization helpers.
"""

from typing import Protocol

from src.api.service_manager import SMSServiceManager
from src.automation.scheduler import MessageScheduler
from src.models.contact_manager import ContactManager
from src.models.database import Database
from src.security.validation import InputValidator


class CoreServiceHost(Protocol):
    """Objects that receive shared FreeSMS core services."""

    db: Database
    service_manager: SMSServiceManager
    contact_manager: ContactManager
    scheduler: MessageScheduler
    validator: InputValidator


def initialize_core_services(host: CoreServiceHost) -> None:
    """Attach database, managers, scheduler, and validator to an app host."""
    host.db = Database()
    host.service_manager = SMSServiceManager(host.db)
    host.contact_manager = ContactManager(host.db)
    host.scheduler = MessageScheduler(host.db, host.service_manager)
    host.validator = InputValidator()
    host.scheduler.start()
