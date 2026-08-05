"""
Database module for SMS application
"""

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any

from src.models.database_helpers import (
    DB_TIMESTAMP_FORMAT,
    DatabaseError,
    db_locked,
    format_db_timestamp,
)
from src.models.database_schema import create_tables
from src.security.encryption import (
    CredentialEncryptionError,
    decrypt_credentials,
    encrypt_credentials,
    is_legacy_plaintext,
    parse_legacy_credentials,
)
from src.utils.logger import get_logger
from src.utils.paths import get_app_dir, get_db_path

__all__ = ["Database", "DatabaseError"]


class Database:
    """SQLite database for SMS application"""

    def __init__(self, db_path=None):
        """
        Initialize the database

        Args:
            db_path: Path to database file (None for default location)
        """
        # Set up logger
        self.logger = get_logger()

        # Set default database path if not provided
        if db_path is None:
            app_dir = get_app_dir()
            app_dir.mkdir(parents=True, exist_ok=True)
            db_path = get_db_path()

        self.db_path = db_path
        self.conn = None
        self._lock = threading.RLock()

        # Initialize database
        with self._lock:
            self._init_db()

    def _init_db(self):
        """Initialize the database connection and tables"""
        try:
            # Connect to database (check_same_thread=False; access serialized via _lock)
            self.conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")

            # Create tables if they don't exist
            self._create_tables()

            self.logger.info("Database initialized at %s", self.db_path)

        except sqlite3.Error as e:
            self.logger.error("Database initialization error: %s", e)
            raise DatabaseError(
                f"Failed to initialize database at {self.db_path}: {e}"
            ) from e

    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        create_tables(cursor)
        self.conn.commit()

    @db_locked
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __del__(self):
        """Ensure open connections are closed when instances are garbage-collected."""
        try:
            self.close()
        except (
            sqlite3.Error,
            DatabaseError,
            RuntimeError,
            AttributeError,
            OSError,
        ) as exc:
            if hasattr(self, "logger"):
                self.logger.debug("Database cleanup during GC failed: %s", exc)

    @db_locked
    def save_api_credentials(
        self, service_name: str, credentials: dict[str, str], is_active: bool = False
    ) -> bool:
        """
        Save API credentials for a service

        Args:
            service_name: Name of the service
            credentials: Dictionary of credentials
            is_active: Whether this is the active service

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Encrypt credentials before storage
            creds_stored = encrypt_credentials(credentials)

            # Check if credentials already exist for this service
            cursor.execute(
                "SELECT id FROM api_credentials WHERE service_name = ?", (service_name,)
            )

            if cursor.fetchone():
                # Update existing credentials
                cursor.execute(
                    """
                UPDATE api_credentials
                SET credentials = ?, is_active = ?
                WHERE service_name = ?
                """,
                    (creds_stored, 1 if is_active else 0, service_name),
                )
            else:
                # Insert new credentials
                cursor.execute(
                    """
                INSERT INTO api_credentials (service_name, credentials, is_active)
                VALUES (?, ?, ?)
                """,
                    (service_name, creds_stored, 1 if is_active else 0),
                )

            # If this is the active service, deactivate others
            if is_active:
                cursor.execute(
                    """
                UPDATE api_credentials
                SET is_active = 0
                WHERE service_name != ?
                """,
                    (service_name,),
                )

            self.conn.commit()
            self.logger.info("API credentials saved for %s", service_name)
            return True

        except CredentialEncryptionError as e:
            self.logger.error("Error encrypting API credentials: %s", e)
            return False
        except sqlite3.Error as e:
            self.logger.error("Error saving API credentials: %s", e)
            return False

    @db_locked
    def get_api_credentials(self, service_name: str) -> dict[str, str] | None:
        """
        Get API credentials for a service

        Args:
            service_name: Name of the service

        Returns:
            Dictionary of credentials or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT credentials FROM api_credentials WHERE service_name = ?",
                (service_name,),
            )

            if not (row := cursor.fetchone()):
                return None

            stored_value = row["credentials"]

            if (credentials := decrypt_credentials(stored_value)) is not None:
                return credentials

            if is_legacy_plaintext(stored_value):
                if (legacy := parse_legacy_credentials(stored_value)) is not None:
                    self.logger.info(
                        "Migrating legacy plaintext credentials for %s",
                        service_name,
                    )
                    self.save_api_credentials(service_name, legacy, is_active=False)
                    return legacy

            self.logger.error(
                "Unable to read credentials for %s (unknown format)",
                service_name,
            )
            return None

        except sqlite3.Error as e:
            self.logger.error("Error getting API credentials: %s", e)
            return None

    @db_locked
    def get_active_services(self) -> list[str]:
        """
        Get names of active services

        Returns:
            List of active service names
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT service_name FROM api_credentials WHERE is_active = 1"
            )
            rows = cursor.fetchall()

            return [row["service_name"] for row in rows]

        except sqlite3.Error as e:
            self.logger.error("Error getting active services: %s", e)
            return []

    @db_locked
    def save_contact(
        self, name: str, phone: str, country: str = "", notes: str = ""
    ) -> bool:
        """
        Save a contact

        Args:
            name: Contact name
            phone: Phone number
            country: Country code
            notes: Additional notes

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Check if contact already exists with this phone number
            cursor.execute("SELECT id FROM contacts WHERE phone = ?", (phone,))

            if cursor.fetchone():
                # Update existing contact
                cursor.execute(
                    """
                UPDATE contacts
                SET name = ?, country = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE phone = ?
                """,
                    (name, country, notes, phone),
                )
            else:
                # Insert new contact
                cursor.execute(
                    """
                INSERT INTO contacts (name, phone, country, notes)
                VALUES (?, ?, ?, ?)
                """,
                    (name, phone, country, notes),
                )

            self.conn.commit()
            self.logger.info("Contact saved: %s (%s)", name, phone)
            return True

        except sqlite3.Error as e:
            self.logger.error("Error saving contact: %s", e)
            return False

    @db_locked
    def get_contacts(self) -> list[dict[str, Any]]:
        """
        Get all contacts

        Returns:
            List of contact dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM contacts ORDER BY name")
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error("Error getting contacts: %s", e)
            return []

    @db_locked
    def get_contact(self, contact_id: int) -> dict[str, Any] | None:
        """
        Get a contact by ID

        Args:
            contact_id: Contact ID

        Returns:
            Contact dictionary or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))

            if row := cursor.fetchone():
                return dict(row)

            return None

        except sqlite3.Error as e:
            self.logger.error("Error getting contact: %s", e)
            return None

    @db_locked
    def delete_contact(self, contact_id: int) -> bool:
        """
        Delete a contact

        Args:
            contact_id: Contact ID

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            self.conn.commit()

            self.logger.info("Contact deleted: ID %s", contact_id)
            return True

        except sqlite3.Error as e:
            self.logger.error("Error deleting contact: %s", e)
            return False

    @db_locked
    def search_contacts(self, query: str) -> list[dict[str, Any]]:
        """
        Search contacts by name or phone number

        Args:
            query: Search query

        Returns:
            List of matching contacts
        """
        try:
            cursor = self.conn.cursor()

            # Use LIKE for partial matching
            search_pattern = f"%{query}%"

            cursor.execute(
                """
            SELECT * FROM contacts
            WHERE name LIKE ? OR phone LIKE ?
            ORDER BY name
            """,
                (search_pattern, search_pattern),
            )

            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error("Error searching contacts: %s", e)
            return []

    @db_locked
    def save_message_history(
        self,
        recipient: str,
        message: str,
        service: str,
        status: str,
        *,
        message_id: str = None,
        details: str = None,
    ) -> bool:
        """
        Save message to history

        Args:
            recipient: Recipient phone number
            message: Message text
            service: Service used to send the message
            status: Message status
            message_id: Message ID from the service
            details: Additional details as JSON string

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute(
                """
            INSERT INTO message_history (
                recipient, message, service, status, message_id, details
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
                (recipient, message, service, status, message_id, details),
            )

            self.conn.commit()
            self.logger.info("Message history saved for %s", recipient)
            return True

        except sqlite3.Error as e:
            self.logger.error("Error saving message history: %s", e)
            return False

    @db_locked
    def count_successful_sends_today(self, service_name: str) -> int:
        """
        Count successful message sends for a service today.

        Args:
            service_name: Service name to count sends for

        Returns:
            Number of successful sends today
        """
        try:
            if self.conn is None:
                return 0

            cursor = self.conn.cursor()
            today_prefix = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                """
                SELECT COUNT(*) AS count FROM message_history
                WHERE service = ? AND status = 'sent' AND sent_at LIKE ?
                """,
                (service_name, f"{today_prefix}%"),
            )
            if row := cursor.fetchone():
                return int(row["count"])
            return 0
        except sqlite3.Error as e:
            self.logger.error("Error counting today's sends: %s", e)
            return 0

    @db_locked
    def get_message_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get message history

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM message_history ORDER BY sent_at DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error("Error getting message history: %s", e)
            return []

    @db_locked
    def get_message_history_by_id(self, message_id: int) -> dict[str, Any] | None:
        """
        Get a single message history record by ID.

        Args:
            message_id: Message history row ID

        Returns:
            Message dictionary or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM message_history WHERE id = ?", (message_id,))
            if row := cursor.fetchone():
                return dict(row)
            return None

        except sqlite3.Error as e:
            self.logger.error("Error getting message history by id: %s", e)
            return None

    @db_locked
    def save_scheduled_message(
        self,
        recipient: str,
        message: str,
        scheduled_time: str,
        *,
        service: str = None,
        recurring: str = None,
        recurring_interval: int = None,
        recurrence_data: dict = None,
    ) -> int | None:
        """
        Save a scheduled message

        Args:
            recipient: Recipient phone number
            message: Message content
            scheduled_time: Time to send the message (YYYY-MM-DD HH:MM:SS)
            service: Service name to use
            recurring: Recurring type (daily, weekly, monthly, None)
            recurring_interval: Interval for recurring messages
            recurrence_data: Additional data for recurring messages
                (stored in recurring_interval as JSON)

        Returns:
            ID of the saved message or None on error
        """
        try:
            cursor = self.conn.cursor()

            # Convert recurrence_data to JSON if provided
            if recurrence_data is not None:
                recurring_interval = json.dumps(recurrence_data)

            scheduled_time = format_db_timestamp(scheduled_time)

            cursor.execute(
                """
            INSERT INTO scheduled_messages
            (recipient, message, scheduled_time, service, recurring, recurring_interval)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    recipient,
                    message,
                    scheduled_time,
                    service,
                    recurring,
                    recurring_interval,
                ),
            )

            self.conn.commit()
            message_id = cursor.lastrowid
            self.logger.info("Scheduled message saved: ID %s", message_id)
            return message_id

        except sqlite3.Error as e:
            self.logger.error("Error saving scheduled message: %s", e)
            return None

    @db_locked
    def get_scheduled_messages(
        self, include_completed: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get all scheduled messages

        Args:
            include_completed: Whether to include completed messages

        Returns:
            List of scheduled message dictionaries
        """
        try:
            cursor = self.conn.cursor()

            if include_completed:
                query = "SELECT * FROM scheduled_messages ORDER BY scheduled_time"
            else:
                query = (
                    "SELECT * FROM scheduled_messages "
                    "WHERE status != 'completed' ORDER BY scheduled_time"
                )

            cursor.execute(query)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error("Error getting scheduled messages: %s", e)
            return []

    @db_locked
    def get_pending_scheduled_messages(self) -> list[dict[str, Any]]:
        """
        Get pending scheduled messages that are due

        Returns:
            List of scheduled message dictionaries
        """
        try:
            cursor = self.conn.cursor()
            now = datetime.now().strftime(DB_TIMESTAMP_FORMAT)

            cursor.execute(
                """
            SELECT * FROM scheduled_messages
            WHERE status = 'pending' AND scheduled_time <= ?
            ORDER BY scheduled_time
            """,
                (now,),
            )

            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error("Error getting pending scheduled messages: %s", e)
            return []

    @db_locked
    def update_scheduled_message_status(
        self, message_id: int, status: str, completed_at: str = None
    ) -> bool:
        """
        Update status of a scheduled message

        Args:
            message_id: Message ID
            status: New status
            completed_at: Completion time (for completed messages)

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            if completed_at:
                cursor.execute(
                    """
                UPDATE scheduled_messages
                SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                    (status, completed_at, message_id),
                )
            else:
                cursor.execute(
                    """
                UPDATE scheduled_messages
                SET status = ?
                WHERE id = ?
                """,
                    (status, message_id),
                )

            self.conn.commit()
            self.logger.info(
                "Scheduled message status updated: ID %s, status %s",
                message_id,
                status,
            )
            return True

        except sqlite3.Error as e:
            self.logger.error("Error updating scheduled message status: %s", e)
            return False

    @db_locked
    def delete_scheduled_message(self, message_id: int) -> bool:
        """
        Delete a scheduled message

        Args:
            message_id: ID of the message to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM scheduled_messages WHERE id = ?", (message_id,))
            self.conn.commit()
            self.logger.info("Scheduled message deleted: ID %s", message_id)
            return True

        except sqlite3.Error as e:
            self.logger.error("Error deleting scheduled message: %s", e)
            return False

    @db_locked
    def save_message_template(
        self, name: str, content: str, template_id: int | None = None
    ) -> bool:
        """
        Save a message template

        Args:
            name: Template name
            content: Template content
            template_id: When set, update the template with this ID

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            if template_id is not None:
                cursor.execute(
                    """
                UPDATE message_templates
                SET name = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                    (name, content, template_id),
                )
                if not cursor.rowcount:
                    self.logger.error("Template not found for update: %s", template_id)
                    return False
            else:
                # Check if template already exists with this name
                cursor.execute(
                    "SELECT id FROM message_templates WHERE name = ?", (name,)
                )

                if cursor.fetchone():
                    # Update existing template
                    cursor.execute(
                        """
                UPDATE message_templates
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
                """,
                        (content, name),
                    )
                else:
                    # Insert new template
                    cursor.execute(
                        """
                INSERT INTO message_templates (name, content)
                VALUES (?, ?)
                """,
                        (name, content),
                    )

            self.conn.commit()
            self.logger.info("Message template saved: %s", name)
            return True

        except sqlite3.Error as e:
            self.logger.error("Error saving message template: %s", e)
            return False

    @db_locked
    def get_message_templates(self) -> list[dict[str, Any]]:
        """
        Get all message templates

        Returns:
            List of template dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM message_templates ORDER BY name")
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            self.logger.error("Error getting message templates: %s", e)
            return []

    @db_locked
    def delete_message_template(self, template_id: int) -> bool:
        """
        Delete a message template

        Args:
            template_id: ID of the template to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM message_templates WHERE id = ?", (template_id,))
            self.conn.commit()

            return True

        except sqlite3.Error as e:
            self.logger.error("Error deleting message template: %s", e)
            return False

    @property
    def cursor(self):
        """
        Property that returns the database cursor

        Returns:
            SQLite cursor object
        """
        return self.conn.cursor()

    @property
    def connection(self):
        """
        Property that returns the database connection

        Returns:
            SQLite connection object
        """
        return self.conn

    @db_locked
    def update_scheduled_message(
        self,
        message_id: int,
        *,
        recipient: str = None,
        message: str = None,
        scheduled_time: datetime = None,
        service: str = None,
        recurring: str = None,
        recurring_interval: int = None,
        status: str = None,
    ) -> bool:
        """
        Update a scheduled message

        Args:
            message_id: ID of the message to update
            recipient: New recipient phone number
            message: New message content
            scheduled_time: New scheduled time
            service: New service name
            recurring: New recurring type
            recurring_interval: New recurring interval
            status: New status

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Build the update statement
            updates = []
            params = []

            if recipient is not None:
                updates.append("recipient = ?")
                params.append(recipient)

            if message is not None:
                updates.append("message = ?")
                params.append(message)

            if scheduled_time is not None:
                scheduled_time = format_db_timestamp(scheduled_time)
                updates.append("scheduled_time = ?")
                params.append(scheduled_time)

            if service is not None:
                updates.append("service = ?")
                params.append(service)

            if recurring is not None:
                updates.append("recurring = ?")
                params.append(recurring)

            if recurring_interval is not None:
                updates.append("recurring_interval = ?")
                params.append(recurring_interval)

            if status is not None:
                updates.append("status = ?")
                params.append(status)

            # If nothing to update, return early
            if not updates:
                return True

            # Add the WHERE clause
            params.append(message_id)

            # Execute the update (column names are whitelisted literals only)
            update_clause = ", ".join(updates)
            cursor.execute(  # nosec B608
                f"UPDATE scheduled_messages SET {update_clause} WHERE id = ?",
                params,
            )

            self.conn.commit()
            self.logger.info("Scheduled message updated: ID %s", message_id)
            return True

        except sqlite3.Error as e:
            self.logger.error("Error updating scheduled message: %s", e)
            return False
