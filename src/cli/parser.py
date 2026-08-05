"""Argument parser construction for the FreeSMS CLI."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="FreeSMS Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Send message command
    send_parser = subparsers.add_parser("send", help="Send an SMS message")
    send_parser.add_argument("recipient", help="Recipient phone number")
    send_parser.add_argument("message", help="Message content")
    send_parser.add_argument(
        "--service", help="Service to use (default: active service)"
    )

    # Contact commands
    contacts_parser = subparsers.add_parser("contacts", help="Manage contacts")
    contacts_subparsers = contacts_parser.add_subparsers(dest="subcommand")

    contacts_subparsers.add_parser("list", help="List all contacts")

    contacts_add_parser = contacts_subparsers.add_parser(
        "add", help="Add a new contact"
    )
    contacts_add_parser.add_argument("name", help="Contact name")
    contacts_add_parser.add_argument("phone", help="Phone number")
    contacts_add_parser.add_argument("--country", help="Country")
    contacts_add_parser.add_argument("--notes", help="Additional notes")

    contacts_delete_parser = contacts_subparsers.add_parser(
        "delete", help="Delete a contact"
    )
    contacts_delete_parser.add_argument("id", help="Contact ID")

    contacts_import_parser = contacts_subparsers.add_parser(
        "import", help="Import contacts from CSV file"
    )
    contacts_import_parser.add_argument("input_file", help="Path to input CSV file")

    contacts_export_parser = contacts_subparsers.add_parser(
        "export", help="Export contacts to CSV file"
    )
    contacts_export_parser.add_argument("output_file", help="Path to output CSV file")

    contacts_template_parser = contacts_subparsers.add_parser(
        "template", help="Create a template CSV file for contacts import"
    )
    contacts_template_parser.add_argument(
        "output_file", help="Path to output template CSV file"
    )

    # History commands
    history_parser = subparsers.add_parser("history", help="Message history")
    history_subparsers = history_parser.add_subparsers(dest="subcommand")

    history_list_parser = history_subparsers.add_parser(
        "list", help="List message history"
    )
    history_list_parser.add_argument(
        "--limit", type=int, default=20, help="Maximum number of messages to show"
    )

    history_export_parser = history_subparsers.add_parser(
        "export", help="Export message history to CSV"
    )
    history_export_parser.add_argument("output_file", help="Path to output CSV file")
    history_export_parser.add_argument(
        "--limit", type=int, default=1000, help="Maximum number of messages to export"
    )

    # Schedule commands
    schedule_parser = subparsers.add_parser(
        "schedule", help="Manage scheduled messages"
    )
    schedule_subparsers = schedule_parser.add_subparsers(dest="subcommand")

    schedule_list_parser = schedule_subparsers.add_parser(
        "list", help="List scheduled messages"
    )
    schedule_list_parser.add_argument(
        "--all", action="store_true", help="Include completed messages"
    )

    schedule_add_parser = schedule_subparsers.add_parser(
        "add", help="Schedule a new message"
    )
    schedule_add_parser.add_argument("recipient", help="Recipient phone number")
    schedule_add_parser.add_argument("message", help="Message content")
    schedule_add_parser.add_argument(
        "time", help="Scheduled time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )
    schedule_add_parser.add_argument(
        "--service", help="Service to use (default: active service)"
    )
    schedule_add_parser.add_argument(
        "--recurring", choices=["daily", "weekly", "monthly"], help="Recurring schedule"
    )
    schedule_add_parser.add_argument(
        "--interval", type=int, default=1, help="Interval for recurring messages"
    )

    schedule_cancel_parser = schedule_subparsers.add_parser(
        "cancel", help="Cancel a scheduled message"
    )
    schedule_cancel_parser.add_argument("id", help="Scheduled message ID")

    # Template commands
    templates_parser = subparsers.add_parser(
        "templates", help="Manage message templates"
    )
    templates_subparsers = templates_parser.add_subparsers(dest="subcommand")

    templates_subparsers.add_parser("list", help="List all templates")

    templates_add_parser = templates_subparsers.add_parser(
        "add", help="Add a new template"
    )
    templates_add_parser.add_argument("name", help="Template name")
    templates_add_parser.add_argument("content", help="Template content")

    templates_delete_parser = templates_subparsers.add_parser(
        "delete", help="Delete a template"
    )
    templates_delete_parser.add_argument("id", help="Template ID")

    # Service commands
    services_parser = subparsers.add_parser("services", help="Manage SMS services")
    services_subparsers = services_parser.add_subparsers(dest="subcommand")

    services_subparsers.add_parser("list", help="List available services")

    services_configure_parser = services_subparsers.add_parser(
        "configure", help="Configure a service"
    )
    services_configure_parser.add_argument("name", help="Service name")
    services_configure_parser.add_argument(
        "credentials", help="Service credentials (JSON)"
    )

    services_activate_parser = services_subparsers.add_parser(
        "activate", help="Set active service"
    )
    services_activate_parser.add_argument("name", help="Service name")

    services_test_parser = services_subparsers.add_parser(
        "test", help="Test an SMS service connection"
    )
    services_test_parser.add_argument(
        "--name", help="Service name (default: active service)"
    )

    return parser
