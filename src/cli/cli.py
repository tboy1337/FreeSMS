#!/usr/bin/env python3
"""
Command Line Interface for FreeSMS Application
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

from tabulate import tabulate

# Add the project root to the Python path if it's not already there
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cli.parser import build_parser
from src.services.app_services import initialize_core_services
from src.utils.logger import setup_logger


class SMSCommandLineInterface:
    """Command line interface for FreeSMS application"""

    def __init__(self) -> None:
        """Initialize the CLI application"""
        # Set up logger
        self.logger = setup_logger("freesms_cli")

        # Initialize services
        self._initialize_services()

    def _initialize_services(self) -> None:
        """Initialize application services"""
        initialize_core_services(self)

    def send_message(
        self,
        recipient: str,
        message: str,
        service_name: str | None = None,
    ) -> bool:
        """
        Send an SMS message

        Args:
            recipient: Phone number of recipient
            message: Message content
            service_name: Optional service name to use
        """
        # Validate inputs
        valid_phone, phone_error = self.validator.validate_phone_input(recipient)
        if not valid_phone:
            print(f"Error: {phone_error}")
            return False

        valid_msg, msg_error = self.validator.validate_message(message)
        if not valid_msg:
            print(f"Error: {msg_error}")
            return False

        # Send message
        print(f"Sending message to {recipient}...")
        response = self.service_manager.send_sms(recipient, message, service_name)

        if response.success:
            print("Message sent successfully!")
            print(f"Message ID: {response.message_id}")
            return True

        print(f"Failed to send message: {response.error}")
        return False

    def list_contacts(self) -> None:
        """List all contacts in the database"""
        if not (contacts := self.db.get_contacts()):
            print("No contacts found.")
            return

        # Prepare data for tabulate
        table_data = []
        for contact in contacts:
            table_data.append(
                [
                    contact["id"],
                    contact["name"],
                    contact["phone"],
                    contact["country"] or "",
                    contact["notes"] or "",
                ]
            )

        # Print table
        headers = ["ID", "Name", "Phone", "Country", "Notes"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def add_contact(
        self,
        name: str,
        phone: str,
        country: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """
        Add a new contact

        Args:
            name: Contact name
            phone: Phone number
            country: Optional country
            notes: Optional notes
        """
        if not name:
            print("Error: Name is required")
            return False

        valid_phone, phone_error = self.validator.validate_phone_input(phone)
        if not valid_phone:
            print(f"Error: {phone_error}")
            return False

        if country:
            valid_country, country_error = self.validator.validate_country_code(country)
            if not valid_country:
                print(f"Error: {country_error}")
                return False

        # Add contact
        if _ := self.db.save_contact(name, phone, country or "", notes or ""):
            print(f"Contact {name} added successfully")
            return True

        print("Failed to add contact")
        return False

    def delete_contact(self, contact_id: str | int) -> bool:
        """
        Delete a contact

        Args:
            contact_id: ID of contact to delete
        """
        if not contact_id:
            print("Error: Contact ID is required")
            return False

        # Get contact name for confirmation
        if not (contact := self.db.get_contact(int(contact_id))):
            print(f"Error: Contact with ID {contact_id} not found")
            return False

        # Delete contact
        if _ := self.db.delete_contact(int(contact_id)):
            contact_name = contact["name"]
            print(f"Contact {contact_name} deleted successfully")
            return True

        print("Failed to delete contact")
        return False

    def list_message_history(self, limit: int = 20) -> None:
        """
        List message history

        Args:
            limit: Maximum number of messages to show
        """
        if not (messages := self.db.get_message_history(limit)):
            print("No message history found.")
            return

        # Prepare data for tabulate
        table_data = []
        for msg in messages:
            # Format message to show first 30 chars
            message_preview = msg["message"]
            if len(message_preview) > 30:
                message_preview = message_preview[:27] + "..."

            table_data.append(
                [
                    msg["id"],
                    msg["recipient"],
                    message_preview,
                    msg["service"],
                    msg["status"],
                    msg["sent_at"],
                ]
            )

        # Print table
        headers = ["ID", "Recipient", "Message", "Service", "Status", "Sent At"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def schedule_message(
        self,
        recipient: str,
        message: str,
        scheduled_time: str,
        *,
        service: str | None = None,
        recurring: str | None = None,
        interval: int | None = None,
    ) -> bool:
        """
        Schedule a message for later delivery

        Args:
            recipient: Phone number of recipient
            message: Message content
            scheduled_time: When to send the message (ISO format)
            service: Optional service name to use
            recurring: Optional recurring type (daily, weekly, monthly)
            interval: Optional interval for recurring messages
        """
        if not recipient or not message or not scheduled_time:
            print("Error: Recipient, message, and scheduled time are required")
            return False

        valid_phone, phone_error = self.validator.validate_phone_input(recipient)
        if not valid_phone:
            print(f"Error: {phone_error}")
            return False

        valid_msg, msg_error = self.validator.validate_message(message)
        if not valid_msg:
            print(f"Error: {msg_error}")
            return False

        # Validate the scheduled time format
        try:
            if (dt := datetime.fromisoformat(scheduled_time)) <= datetime.now():
                print("Error: Scheduled time must be in the future")
                return False
        except ValueError:
            print(
                "Error: Invalid scheduled time format. "
                "Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
            return False

        # Format it consistently
        scheduled_time = dt.strftime("%Y-%m-%d %H:%M:%S")

        # Validate recurring parameters
        if recurring and not interval:
            print(
                f"Warning: No interval specified for {recurring} recurrence. "
                "Using default interval of 1."
            )
            interval = 1
        elif interval and not recurring:
            print(
                "Warning: Interval specified but no recurrence type. "
                "Message will be sent once."
            )
            interval = None

        # Validate interval is reasonable for the recurrence type
        if recurring and interval:
            if recurring == "daily" and interval > 30:
                print(
                    f"Warning: Large interval ({interval} days) "
                    "for daily recurrence."
                )
            elif recurring == "weekly" and interval > 12:
                print(
                    f"Warning: Large interval ({interval} weeks) "
                    "for weekly recurrence."
                )
            elif recurring == "monthly" and interval > 12:
                print(
                    f"Warning: Large interval ({interval} months) "
                    "for monthly recurrence."
                )

        # Add scheduled message via scheduler
        try:
            recurrence_data = None
            if recurring and interval:
                recurrence_data = {"days_interval": interval}

            message_id = self.scheduler.schedule_message(
                recipient=recipient,
                message=message,
                schedule_time=dt,
                recurrence=recurring,
                recurrence_data=recurrence_data,
                service=service,
            )

            if message_id:
                print(f"Message scheduled successfully for {scheduled_time}")
                if recurring:
                    recur_unit = (
                        recurring[:-2] if recurring.endswith("ly") else recurring
                    )
                    print(
                        f"This message will recur {recurring} "
                        f"every {interval} {recur_unit}"
                    )
                return True

            print("Failed to schedule message")
            return False
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            print(f"Error scheduling message: {exc}")
            return False

    def list_scheduled_messages(self, include_completed: bool = False) -> None:
        """
        List scheduled messages

        Args:
            include_completed: Whether to include completed messages
        """
        if not (messages := self.db.get_scheduled_messages(include_completed)):
            print("No scheduled messages found.")
            return

        # Prepare data for tabulate
        table_data = []
        for msg in messages:
            # Format message to show first 30 chars
            message_preview = msg["message"]
            if len(message_preview) > 30:
                message_preview = message_preview[:27] + "..."

            recurring_info = ""
            if msg["recurring"]:
                interval_info = msg["recurring_interval"]
                # Try to parse as JSON if it's a string
                if isinstance(interval_info, str):
                    try:
                        interval_data = json.loads(interval_info)
                        if "days_interval" in interval_data:
                            days = interval_data["days_interval"]
                            interval_info = f"{days} days"
                    except json.JSONDecodeError:
                        pass

                recurring_type = msg["recurring"]
                recurring_info = f"{recurring_type} (every {interval_info})"

            table_data.append(
                [
                    msg["id"],
                    msg["recipient"],
                    message_preview,
                    msg["scheduled_time"],
                    recurring_info,
                    msg["status"],
                ]
            )

        # Print table
        headers = [
            "ID",
            "Recipient",
            "Message",
            "Scheduled Time",
            "Recurring",
            "Status",
        ]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def cancel_scheduled_message(self, message_id: str | int) -> bool:
        """
        Cancel a scheduled message

        Args:
            message_id: ID of scheduled message to cancel
        """
        if not message_id:
            print("Error: Message ID is required")
            return False

        # Cancel the scheduled message using the scheduler
        try:
            message_id = int(message_id)
        except ValueError:
            print("Error: Invalid message ID format")
            return False

        if _ := self.scheduler.cancel_scheduled_message(message_id):
            print(f"Scheduled message {message_id} cancelled successfully")
            return True

        print(f"Failed to cancel scheduled message {message_id}")
        return False

    def list_templates(self) -> None:
        """List message templates"""
        if not (templates := self.db.get_message_templates()):
            print("No message templates found.")
            return

        # Prepare data for tabulate
        table_data = []
        for template in templates:
            # Format content to show first 40 chars
            content_preview = template["content"]
            if len(content_preview) > 40:
                content_preview = content_preview[:37] + "..."

            table_data.append([template["id"], template["name"], content_preview])

        # Print table
        headers = ["ID", "Name", "Content"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def add_template(self, name: str, content: str) -> bool:
        """
        Add a new message template

        Args:
            name: Template name
            content: Template content
        """
        if not name or not content:
            print("Error: Name and content are required")
            return False

        # Add template
        if _ := self.db.save_message_template(name, content):
            print(f"Template {name} added successfully")
            return True

        print("Failed to add template")
        return False

    def delete_template(self, template_id: str | int) -> bool:
        """
        Delete a message template

        Args:
            template_id: ID of template to delete
        """
        if not template_id:
            print("Error: Template ID is required")
            return False

        # Delete template
        if _ := self.db.delete_message_template(int(template_id)):
            print(f"Template {template_id} deleted successfully")
            return True

        print(f"Failed to delete template {template_id}")
        return False

    def list_services(self) -> None:
        """List available SMS services"""
        # Get services
        available_services = self.service_manager.get_available_services()
        configured_services = self.service_manager.get_configured_services()

        # Get active service
        active_service_name = None
        if self.service_manager.active_service:
            active_service_name = self.service_manager.active_service.service_name

        # Prepare data for tabulate
        table_data = []
        for service_name in available_services:
            status = "Available"
            if service_name in configured_services:
                status = "Configured"
            if service_name == active_service_name:
                status = "Active"

            table_data.append([service_name, status])

        # Print table
        headers = ["Service", "Status"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def configure_service(self, service_name: str, credentials_json: str) -> bool:
        """
        Configure an SMS service

        Args:
            service_name: Name of service to configure
            credentials_json: JSON string of credentials
        """
        if not service_name or not credentials_json:
            print("Error: Service name and credentials are required")
            return False

        # Parse credentials
        try:
            credentials = json.loads(credentials_json)
        except json.JSONDecodeError:
            print("Error: Invalid JSON for credentials")
            return False

        if not self.service_manager.get_service_by_name(service_name):
            print(f"Error: Service {service_name} not found")
            return False

        result = self.service_manager.configure_service(
            service_name, credentials, validate=True
        )

        if result:
            print(f"Service {service_name} configured successfully")
            return True

        print(f"Failed to configure service {service_name}")
        return False

    def set_active_service(self, service_name: str) -> bool:
        """
        Set the active SMS service

        Args:
            service_name: Name of service to set as active
        """
        if not service_name:
            print("Error: Service name is required")
            return False

        # Set active service
        if _ := self.service_manager.set_active_service(service_name):
            print(f"Service {service_name} set as active")
            return True

        print(f"Failed to set service {service_name} as active")
        return False

    def test_service(self, service_name: str | None = None) -> bool:
        """
        Test an SMS service connection

        Args:
            service_name: Name of service to test (None for active service)
        """
        # Get the service to test
        service = None
        if service_name:
            service = self.service_manager.get_service_by_name(service_name)
        else:
            service = self.service_manager.active_service
            service_name = "active service" if service else None

        if not service:
            if not service_name:
                print("Error: No active service configured")
            else:
                print(f"Error: Service {service_name} not found")
            return False

        print(f"Testing service: {service.service_name}")

        # Validate credentials
        if service.validate_credentials():
            print("✓ Credentials are valid")
        else:
            print("✗ Invalid credentials")
            return False

        # Check quota
        quota = service.get_remaining_quota()
        print(f"✓ Daily quota remaining: {quota}")

        # Check balance if available
        try:
            balance = service.check_balance()
            if isinstance(balance, dict) and not balance.get("error"):
                print("✓ Account is active and in good standing")
                if "balance" in balance:
                    balance_amount = balance["balance"]
                    print(f"  Balance: {balance_amount}")
                if "quota" in balance:
                    quota_amount = balance["quota"]
                    print(f"  Quota: {quota_amount}")
            else:
                error = balance.get("error", "Unknown error")
                print(f"✗ Account issue: {error}")
                return False
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            print(f"✗ Error checking account: {exc}")
            return False

        print("Service test completed successfully!")
        return True

    def shutdown(self) -> None:
        """Shut down CLI resources"""
        try:
            if hasattr(self, "scheduler"):
                self.scheduler.stop()
        except (OSError, RuntimeError) as exc:
            self.logger.error("Error stopping scheduler during shutdown: %s", exc)

        try:
            if hasattr(self, "db"):
                self.db.close()
        except (OSError, RuntimeError) as exc:
            self.logger.error("Error closing database during shutdown: %s", exc)

    def export_history(self, output_file: str, limit: int = 1000) -> bool:
        """
        Export message history to a CSV file

        Args:
            output_file: Path to output CSV file
            limit: Maximum number of messages to export
        """
        if not (messages := self.db.get_message_history(limit)):
            print("No message history found to export.")
            return False

        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                # Define CSV fields
                fieldnames = [
                    "id",
                    "recipient",
                    "message",
                    "service",
                    "status",
                    "message_id",
                    "sent_at",
                    "details",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header
                writer.writeheader()

                # Write data
                for msg in messages:
                    # Ensure all fields exist (some might be None)
                    safe_msg = {field: msg.get(field, "") for field in fieldnames}
                    writer.writerow(safe_msg)

                print(
                    f"Successfully exported {len(messages)} messages to {output_file}"
                )
                return True
        except (OSError, csv.Error, ValueError) as exc:
            print(f"Error exporting message history: {exc}")
            return False

    def import_contacts(self, input_file: str) -> bool:
        """
        Import contacts from a CSV file

        Args:
            input_file: Path to input CSV file
        """
        if not os.path.exists(input_file):
            print(f"Error: File {input_file} not found")
            return False

        try:
            with open(input_file, "r", encoding="utf-8") as csvfile:
                csv_data = csvfile.read()

            imported, import_errors = self.contact_manager.import_contacts_from_csv(
                csv_data
            )

            for error in import_errors:
                print(f"Warning: {error}")

            print(f"Import complete: {imported} imported, {len(import_errors)} errors")
            return imported > 0

        except (OSError, csv.Error, ValueError) as exc:
            print(f"Error importing contacts: {exc}")
            return False

    def export_contacts(self, output_file: str) -> bool:
        """
        Export contacts to a CSV file

        Args:
            output_file: Path to output CSV file
        """
        if not (contacts := self.db.get_contacts()):
            print("No contacts found to export.")
            return False

        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                # Define CSV fields
                fieldnames = [
                    "id",
                    "name",
                    "phone",
                    "country",
                    "notes",
                    "created_at",
                    "updated_at",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header
                writer.writeheader()

                # Write data
                for contact in contacts:
                    # Ensure all fields exist (some might be None)
                    safe_contact = {
                        field: contact.get(field, "") for field in fieldnames
                    }
                    writer.writerow(safe_contact)

                print(
                    f"Successfully exported {len(contacts)} contacts to {output_file}"
                )
                return True
        except (OSError, csv.Error, ValueError) as exc:
            print(f"Error exporting contacts: {exc}")
            return False

    def create_contacts_template(self, output_file: str) -> bool:
        """
        Create a template CSV file for contacts import

        Args:
            output_file: Path to output CSV file
        """
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                # Define CSV fields
                fieldnames = ["name", "phone", "country", "notes"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header
                writer.writeheader()

                # Write sample data
                writer.writerow(
                    {
                        "name": "John Doe",
                        "phone": "+12025551234",
                        "country": "US",
                        "notes": "Example contact",
                    }
                )
                writer.writerow(
                    {
                        "name": "Jane Smith",
                        "phone": "+447911123456",
                        "country": "GB",
                        "notes": "Another example",
                    }
                )

                print(f"Successfully created contacts template at {output_file}")
                print("Edit this file with your contacts data and then import it with:")
                print(f"  freesms-cli contacts import {output_file}")
                return True
        except (OSError, csv.Error, ValueError) as exc:
            print(f"Error creating contacts template: {exc}")
            return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments"""
    parser = build_parser()
    return parser.parse_args(argv)


def main() -> int:
    """Main entry point for the CLI application"""
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 0

    cli = SMSCommandLineInterface()
    exit_code = 0

    def mark_failure(result: object) -> None:
        nonlocal exit_code
        if result is False:
            exit_code = 1

    try:
        if args.command == "send":
            mark_failure(cli.send_message(args.recipient, args.message, args.service))

        elif args.command == "contacts":
            if args.subcommand == "list":
                cli.list_contacts()
            elif args.subcommand == "add":
                mark_failure(
                    cli.add_contact(args.name, args.phone, args.country, args.notes)
                )
            elif args.subcommand == "delete":
                mark_failure(cli.delete_contact(args.id))
            elif args.subcommand == "import":
                mark_failure(cli.import_contacts(args.input_file))
            elif args.subcommand == "export":
                mark_failure(cli.export_contacts(args.output_file))
            elif args.subcommand == "template":
                mark_failure(cli.create_contacts_template(args.output_file))
            else:
                cli.list_contacts()

        elif args.command == "history":
            if args.subcommand == "list":
                cli.list_message_history(args.limit)
            elif args.subcommand == "export":
                mark_failure(cli.export_history(args.output_file, args.limit))
            else:
                cli.list_message_history(20)

        elif args.command == "schedule":
            if args.subcommand == "list":
                cli.list_scheduled_messages(args.all)
            elif args.subcommand == "add":
                mark_failure(
                    cli.schedule_message(
                        args.recipient,
                        args.message,
                        args.time,
                        service=args.service,
                        recurring=args.recurring,
                        interval=args.interval,
                    )
                )
            elif args.subcommand == "cancel":
                mark_failure(cli.cancel_scheduled_message(args.id))
            else:
                cli.list_scheduled_messages()

        elif args.command == "templates":
            if args.subcommand == "list":
                cli.list_templates()
            elif args.subcommand == "add":
                mark_failure(cli.add_template(args.name, args.content))
            elif args.subcommand == "delete":
                mark_failure(cli.delete_template(args.id))
            else:
                cli.list_templates()

        elif args.command == "services":
            if args.subcommand == "list":
                cli.list_services()
            elif args.subcommand == "configure":
                mark_failure(cli.configure_service(args.name, args.credentials))
            elif args.subcommand == "activate":
                mark_failure(cli.set_active_service(args.name))
            elif args.subcommand == "test":
                mark_failure(cli.test_service(args.name))
            else:
                cli.list_services()

    except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
        cli.logger.exception("CLI error: %s", exc)
        print(f"Error: {exc}")
        exit_code = 1
    finally:
        cli.shutdown()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
