#!/usr/bin/env python3
"""
Command Line Interface for FreeSMS Application
"""
import argparse
import sys
import os
import json
import pycountry
import phonenumbers
import csv
from datetime import datetime
from tabulate import tabulate

# Add the project root to the Python path if it's not already there
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models.database import Database
from src.api.service_manager import SMSServiceManager
from src.models.contact_manager import ContactManager
from src.automation.scheduler import MessageScheduler
from src.security.validation import InputValidator
from src.utils.logger import setup_logger, get_logger


class SMSCommandLineInterface:
    """Command line interface for FreeSMS application"""
    
    def __init__(self):
        """Initialize the CLI application"""
        # Set up logger
        self.logger = setup_logger("sms_sender_cli")
        
        # Initialize services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize application services"""
        # Database connection
        self.db = Database()
        
        # SMS service manager
        self.service_manager = SMSServiceManager(self.db)
        
        # Contact manager
        self.contact_manager = ContactManager(self.db)
        
        # Message scheduler
        self.scheduler = MessageScheduler(self.db, self.service_manager)
        
        # Input validator
        self.validator = InputValidator()
        
        # Start the scheduler
        self.scheduler.start()
    
    def send_message(self, recipient, message, service_name=None):
        """
        Send an SMS message
        
        Args:
            recipient: Phone number of recipient
            message: Message content
            service_name: Optional service name to use
        """
        # Validate inputs
        if not recipient:
            print("Error: Recipient phone number is required")
            return False
        
        if not message:
            print("Error: Message content is required")
            return False
        
        # Send message
        try:
            print(f"Sending message to {recipient}...")
            response = self.service_manager.send_sms(recipient, message, service_name)
            
            if response.success:
                print("Message sent successfully!")
                print(f"Message ID: {response.message_id}")
                return True
            else:
                print(f"Failed to send message: {response.error}")
                return False
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def list_contacts(self):
        """List all contacts in the database"""
        contacts = self.db.get_contacts()
        
        if not contacts:
            print("No contacts found.")
            return
        
        # Prepare data for tabulate
        table_data = []
        for contact in contacts:
            table_data.append([
                contact['id'],
                contact['name'],
                contact['phone'],
                contact['country'] or '',
                contact['notes'] or ''
            ])
        
        # Print table
        headers = ["ID", "Name", "Phone", "Country", "Notes"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def add_contact(self, name, phone, country=None, notes=None):
        """
        Add a new contact
        
        Args:
            name: Contact name
            phone: Phone number
            country: Optional country
            notes: Optional notes
        """
        if not name or not phone:
            print("Error: Name and phone number are required")
            return False
        
        # Add contact
        result = self.db.save_contact(name, phone, country or "", notes or "")
        
        if result:
            print(f"Contact '{name}' added successfully")
            return True
        else:
            print("Failed to add contact")
            return False
    
    def delete_contact(self, contact_id):
        """
        Delete a contact
        
        Args:
            contact_id: ID of contact to delete
        """
        if not contact_id:
            print("Error: Contact ID is required")
            return False
        
        # Get contact name for confirmation
        contact = self.db.get_contact(int(contact_id))
        if not contact:
            print(f"Error: Contact with ID {contact_id} not found")
            return False
        
        # Delete contact
        result = self.db.delete_contact(int(contact_id))
        
        if result:
            print(f"Contact '{contact['name']}' deleted successfully")
            return True
        else:
            print("Failed to delete contact")
            return False
    
    def list_message_history(self, limit=20):
        """
        List message history
        
        Args:
            limit: Maximum number of messages to show
        """
        messages = self.db.get_message_history(limit)
        
        if not messages:
            print("No message history found.")
            return
        
        # Prepare data for tabulate
        table_data = []
        for msg in messages:
            # Format message to show first 30 chars
            message_preview = msg['message']
            if len(message_preview) > 30:
                message_preview = message_preview[:27] + "..."
            
            table_data.append([
                msg['id'],
                msg['recipient'],
                message_preview,
                msg['service'],
                msg['status'],
                msg['sent_at']
            ])
        
        # Print table
        headers = ["ID", "Recipient", "Message", "Service", "Status", "Sent At"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def schedule_message(self, recipient, message, scheduled_time, service=None, recurring=None, interval=None):
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
        
        # Validate the scheduled time format
        try:
            # Try to parse the time
            dt = datetime.fromisoformat(scheduled_time)
            
            # Check if the time is in the future
            if dt <= datetime.now():
                print("Error: Scheduled time must be in the future")
                return False
                
            # Format it consistently
            scheduled_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            print("Error: Invalid scheduled time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
            return False
        
        # Validate recurring parameters
        if recurring and not interval:
            print(f"Warning: No interval specified for {recurring} recurrence. Using default interval of 1.")
            interval = 1
        elif interval and not recurring:
            print("Warning: Interval specified but no recurrence type. Message will be sent once.")
            interval = None
        
        # Validate interval is reasonable for the recurrence type
        if recurring and interval:
            if recurring == "daily" and interval > 30:
                print(f"Warning: Large interval ({interval} days) for daily recurrence.")
            elif recurring == "weekly" and interval > 12:
                print(f"Warning: Large interval ({interval} weeks) for weekly recurrence.")
            elif recurring == "monthly" and interval > 12:
                print(f"Warning: Large interval ({interval} months) for monthly recurrence.")
        
        # Add scheduled message
        try:
            # Prepare recurrence data if needed
            recurrence_data = None
            if recurring and interval:
                recurrence_data = {"days_interval": interval}
            
            message_id = self.db.save_scheduled_message(
                recipient=recipient, 
                message=message, 
                scheduled_time=scheduled_time, 
                service=service, 
                recurring=recurring, 
                recurring_interval=None,
                recurrence_data=recurrence_data
            )
            
            if message_id:
                print(f"Message scheduled successfully for {scheduled_time}")
                if recurring:
                    print(f"This message will recur {recurring} every {interval} {recurring[:-2] if recurring.endswith('ly') else recurring}")
                return True
            else:
                print("Failed to schedule message")
                return False
        except Exception as e:
            print(f"Error scheduling message: {e}")
            return False
    
    def list_scheduled_messages(self, include_completed=False):
        """
        List scheduled messages
        
        Args:
            include_completed: Whether to include completed messages
        """
        messages = self.db.get_scheduled_messages(include_completed)
        
        if not messages:
            print("No scheduled messages found.")
            return
        
        # Prepare data for tabulate
        table_data = []
        for msg in messages:
            # Format message to show first 30 chars
            message_preview = msg['message']
            if len(message_preview) > 30:
                message_preview = message_preview[:27] + "..."
            
            recurring_info = ""
            if msg['recurring']:
                interval_info = msg['recurring_interval']
                # Try to parse as JSON if it's a string
                if isinstance(interval_info, str):
                    try:
                        interval_data = json.loads(interval_info)
                        if 'days_interval' in interval_data:
                            interval_info = f"{interval_data['days_interval']} days"
                    except json.JSONDecodeError:
                        pass
                
                recurring_info = f"{msg['recurring']} (every {interval_info})"
            
            table_data.append([
                msg['id'],
                msg['recipient'],
                message_preview,
                msg['scheduled_time'],
                recurring_info,
                msg['status']
            ])
        
        # Print table
        headers = ["ID", "Recipient", "Message", "Scheduled Time", "Recurring", "Status"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def cancel_scheduled_message(self, message_id):
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
            result = self.scheduler.cancel_scheduled_message(message_id)
            
            if result:
                print(f"Scheduled message {message_id} cancelled successfully")
                return True
            else:
                print(f"Failed to cancel scheduled message {message_id}")
                return False
        except ValueError:
            print(f"Error: Invalid message ID format")
            return False
        except Exception as e:
            print(f"Error cancelling scheduled message: {e}")
            return False
    
    def list_templates(self):
        """List message templates"""
        templates = self.db.get_templates()
        
        if not templates:
            print("No message templates found.")
            return
        
        # Prepare data for tabulate
        table_data = []
        for template in templates:
            # Format content to show first 40 chars
            content_preview = template['content']
            if len(content_preview) > 40:
                content_preview = content_preview[:37] + "..."
            
            table_data.append([
                template['id'],
                template['name'],
                content_preview
            ])
        
        # Print table
        headers = ["ID", "Name", "Content"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def add_template(self, name, content):
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
        result = self.db.save_template(name, content)
        
        if result:
            print(f"Template '{name}' added successfully")
            return True
        else:
            print("Failed to add template")
            return False
    
    def delete_template(self, template_id):
        """
        Delete a message template
        
        Args:
            template_id: ID of template to delete
        """
        if not template_id:
            print("Error: Template ID is required")
            return False
        
        # Delete template
        result = self.db.delete_message_template(int(template_id))
        
        if result:
            print(f"Template {template_id} deleted successfully")
            return True
        else:
            print(f"Failed to delete template {template_id}")
            return False
    
    def list_services(self):
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
    
    def configure_service(self, service_name, credentials_json):
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
        
        # Get service
        service = self.service_manager.get_service_by_name(service_name)
        if not service:
            print(f"Error: Service '{service_name}' not found")
            return False
        
        # Save credentials
        result = self.db.save_api_credentials(service_name, credentials)
        
        if result:
            print(f"Service '{service_name}' configured successfully")
            
            # Configure the service
            if hasattr(service, 'configure'):
                service.configure(credentials)
            
            return True
        else:
            print(f"Failed to configure service '{service_name}'")
            return False
    
    def set_active_service(self, service_name):
        """
        Set the active SMS service
        
        Args:
            service_name: Name of service to set as active
        """
        if not service_name:
            print("Error: Service name is required")
            return False
        
        # Set active service
        result = self.service_manager.set_active_service(service_name)
        
        if result:
            print(f"Service '{service_name}' set as active")
            return True
        else:
            print(f"Failed to set service '{service_name}' as active")
            return False
    
    def test_service(self, service_name=None):
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
            print(f"Error: {'No active service configured' if not service_name else f'Service {service_name} not found'}")
            return False
        
        print(f"Testing service: {service.service_name}")
        
        # Validate credentials
        valid = service.validate_credentials()
        if valid:
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
            if isinstance(balance, dict) and not balance.get('error'):
                print("✓ Account is active and in good standing")
                if 'balance' in balance:
                    print(f"  Balance: {balance['balance']}")
                if 'quota' in balance:
                    print(f"  Quota: {balance['quota']}")
            else:
                error = balance.get('error', 'Unknown error')
                print(f"✗ Account issue: {error}")
                return False
        except Exception as e:
            print(f"✗ Error checking account: {e}")
            return False
        
        print("Service test completed successfully!")
        return True
    
    def shutdown(self):
        """Shut down CLI resources"""
        try:
            # Stop the scheduler
            if hasattr(self, 'scheduler'):
                self.scheduler.stop()
            
            # Close database connection
            if hasattr(self, 'db'):
                self.db.close()
        except Exception as e:
            print(f"Error during shutdown: {e}")
    
    def export_history(self, output_file, limit=1000):
        """
        Export message history to a CSV file
        
        Args:
            output_file: Path to output CSV file
            limit: Maximum number of messages to export
        """
        messages = self.db.get_message_history(limit)
        
        if not messages:
            print("No message history found to export.")
            return False
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Define CSV fields
                fieldnames = ['id', 'recipient', 'message', 'service', 'status', 'message_id', 'sent_at', 'details']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header
                writer.writeheader()
                
                # Write data
                for msg in messages:
                    # Ensure all fields exist (some might be None)
                    safe_msg = {field: msg.get(field, '') for field in fieldnames}
                    writer.writerow(safe_msg)
                
                print(f"Successfully exported {len(messages)} messages to {output_file}")
                return True
        except Exception as e:
            print(f"Error exporting message history: {e}")
            return False
    
    def import_contacts(self, input_file):
        """
        Import contacts from a CSV file
        
        Args:
            input_file: Path to input CSV file
        """
        if not os.path.exists(input_file):
            print(f"Error: File {input_file} not found")
            return False
        
        try:
            imported = 0
            skipped = 0
            errors = 0
            
            with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Validate required fields
                if not reader.fieldnames or not all(f in reader.fieldnames for f in ['name', 'phone']):
                    print("Error: CSV file must have 'name' and 'phone' columns")
                    return False
                
                # Process each row
                for row in reader:
                    name = row.get('name', '').strip()
                    phone = row.get('phone', '').strip()
                    country = row.get('country', '').strip()
                    notes = row.get('notes', '').strip()
                    
                    # Basic validation
                    if not name or not phone:
                        print(f"Warning: Skipping row with missing name or phone: {row}")
                        skipped += 1
                        continue
                    
                    # Validate phone number
                    valid, error = self.validator.validate_phone_input(phone)
                    if not valid:
                        print(f"Warning: Skipping invalid phone number '{phone}' for '{name}': {error}")
                        skipped += 1
                        continue
                    
                    # Add contact
                    try:
                        result = self.db.save_contact(name, phone, country, notes)
                        if result:
                            imported += 1
                        else:
                            print(f"Error saving contact: {name}, {phone}")
                            errors += 1
                    except Exception as e:
                        print(f"Error saving contact '{name}': {e}")
                        errors += 1
            
            # Print summary
            print(f"Import complete: {imported} imported, {skipped} skipped, {errors} errors")
            return imported > 0
            
        except Exception as e:
            print(f"Error importing contacts: {e}")
            return False
    
    def export_contacts(self, output_file):
        """
        Export contacts to a CSV file
        
        Args:
            output_file: Path to output CSV file
        """
        contacts = self.db.get_contacts()
        
        if not contacts:
            print("No contacts found to export.")
            return False
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Define CSV fields
                fieldnames = ['id', 'name', 'phone', 'country', 'notes', 'created_at', 'updated_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header
                writer.writeheader()
                
                # Write data
                for contact in contacts:
                    # Ensure all fields exist (some might be None)
                    safe_contact = {field: contact.get(field, '') for field in fieldnames}
                    writer.writerow(safe_contact)
                
                print(f"Successfully exported {len(contacts)} contacts to {output_file}")
                return True
        except Exception as e:
            print(f"Error exporting contacts: {e}")
            return False
    
    def create_contacts_template(self, output_file):
        """
        Create a template CSV file for contacts import
        
        Args:
            output_file: Path to output CSV file
        """
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Define CSV fields
                fieldnames = ['name', 'phone', 'country', 'notes']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header
                writer.writeheader()
                
                # Write sample data
                writer.writerow({
                    'name': 'John Doe',
                    'phone': '+12025551234',
                    'country': 'US',
                    'notes': 'Example contact'
                })
                writer.writerow({
                    'name': 'Jane Smith',
                    'phone': '+447911123456',
                    'country': 'GB',
                    'notes': 'Another example'
                })
                
                print(f"Successfully created contacts template at {output_file}")
                print("Edit this file with your contacts data and then import it with:")
                print(f"  python run.py cli contacts import {output_file}")
                return True
        except Exception as e:
            print(f"Error creating contacts template: {e}")
            return False


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='FreeSMS Command Line Interface')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Send message command
    send_parser = subparsers.add_parser('send', help='Send an SMS message')
    send_parser.add_argument('recipient', help='Recipient phone number')
    send_parser.add_argument('message', help='Message content')
    send_parser.add_argument('--service', help='Service to use (default: active service)')
    
    # Contact commands
    contacts_parser = subparsers.add_parser('contacts', help='Manage contacts')
    contacts_subparsers = contacts_parser.add_subparsers(dest='subcommand')
    
    # List contacts
    contacts_list_parser = contacts_subparsers.add_parser('list', help='List all contacts')
    
    # Add contact
    contacts_add_parser = contacts_subparsers.add_parser('add', help='Add a new contact')
    contacts_add_parser.add_argument('name', help='Contact name')
    contacts_add_parser.add_argument('phone', help='Phone number')
    contacts_add_parser.add_argument('--country', help='Country')
    contacts_add_parser.add_argument('--notes', help='Additional notes')
    
    # Delete contact
    contacts_delete_parser = contacts_subparsers.add_parser('delete', help='Delete a contact')
    contacts_delete_parser.add_argument('id', help='Contact ID')
    
    # Import contacts from CSV
    contacts_import_parser = contacts_subparsers.add_parser('import', help='Import contacts from CSV file')
    contacts_import_parser.add_argument('input_file', help='Path to input CSV file')
    
    # Export contacts to CSV
    contacts_export_parser = contacts_subparsers.add_parser('export', help='Export contacts to CSV file')
    contacts_export_parser.add_argument('output_file', help='Path to output CSV file')
    
    # Create contacts template
    contacts_template_parser = contacts_subparsers.add_parser('template', help='Create a template CSV file for contacts import')
    contacts_template_parser.add_argument('output_file', help='Path to output template CSV file')
    
    # History commands
    history_parser = subparsers.add_parser('history', help='Message history')
    history_subparsers = history_parser.add_subparsers(dest='subcommand')
    
    # List history
    history_list_parser = history_subparsers.add_parser('list', help='List message history')
    history_list_parser.add_argument('--limit', type=int, default=20, help='Maximum number of messages to show')
    
    # Export history
    history_export_parser = history_subparsers.add_parser('export', help='Export message history to CSV')
    history_export_parser.add_argument('output_file', help='Path to output CSV file')
    history_export_parser.add_argument('--limit', type=int, default=1000, help='Maximum number of messages to export')
    
    # Schedule commands
    schedule_parser = subparsers.add_parser('schedule', help='Manage scheduled messages')
    schedule_subparsers = schedule_parser.add_subparsers(dest='subcommand')
    
    # List scheduled messages
    schedule_list_parser = schedule_subparsers.add_parser('list', help='List scheduled messages')
    schedule_list_parser.add_argument('--all', action='store_true', help='Include completed messages')
    
    # Add scheduled message
    schedule_add_parser = schedule_subparsers.add_parser('add', help='Schedule a new message')
    schedule_add_parser.add_argument('recipient', help='Recipient phone number')
    schedule_add_parser.add_argument('message', help='Message content')
    schedule_add_parser.add_argument('time', help='Scheduled time in ISO format (YYYY-MM-DDTHH:MM:SS)')
    schedule_add_parser.add_argument('--service', help='Service to use (default: active service)')
    schedule_add_parser.add_argument('--recurring', choices=['daily', 'weekly', 'monthly'], help='Recurring schedule')
    schedule_add_parser.add_argument('--interval', type=int, default=1, help='Interval for recurring messages')
    
    # Cancel scheduled message
    schedule_cancel_parser = schedule_subparsers.add_parser('cancel', help='Cancel a scheduled message')
    schedule_cancel_parser.add_argument('id', help='Scheduled message ID')
    
    # Template commands
    templates_parser = subparsers.add_parser('templates', help='Manage message templates')
    templates_subparsers = templates_parser.add_subparsers(dest='subcommand')
    
    # List templates
    templates_list_parser = templates_subparsers.add_parser('list', help='List all templates')
    
    # Add template
    templates_add_parser = templates_subparsers.add_parser('add', help='Add a new template')
    templates_add_parser.add_argument('name', help='Template name')
    templates_add_parser.add_argument('content', help='Template content')
    
    # Delete template
    templates_delete_parser = templates_subparsers.add_parser('delete', help='Delete a template')
    templates_delete_parser.add_argument('id', help='Template ID')
    
    # Service commands
    services_parser = subparsers.add_parser('services', help='Manage SMS services')
    services_subparsers = services_parser.add_subparsers(dest='subcommand')
    
    # List services
    services_list_parser = services_subparsers.add_parser('list', help='List available services')
    
    # Configure service
    services_configure_parser = services_subparsers.add_parser('configure', help='Configure a service')
    services_configure_parser.add_argument('name', help='Service name')
    services_configure_parser.add_argument('credentials', help='Service credentials (JSON)')
    
    # Set active service
    services_activate_parser = services_subparsers.add_parser('activate', help='Set active service')
    services_activate_parser.add_argument('name', help='Service name')
    
    # Test service
    services_test_parser = services_subparsers.add_parser('test', help='Test an SMS service connection')
    services_test_parser.add_argument('--name', help='Service name (default: active service)')
    
    return parser.parse_args()


def main():
    """Main entry point for the CLI application"""
    args = parse_args()
    cli = SMSCommandLineInterface()
    
    try:
        if args.command == 'send':
            cli.send_message(args.recipient, args.message, args.service)
        
        elif args.command == 'contacts':
            if args.subcommand == 'list':
                cli.list_contacts()
            elif args.subcommand == 'add':
                cli.add_contact(args.name, args.phone, args.country, args.notes)
            elif args.subcommand == 'delete':
                cli.delete_contact(args.id)
            elif args.subcommand == 'import':
                cli.import_contacts(args.input_file)
            elif args.subcommand == 'export':
                cli.export_contacts(args.output_file)
            elif args.subcommand == 'template':
                cli.create_contacts_template(args.output_file)
            else:
                cli.list_contacts()
        
        elif args.command == 'history':
            if args.subcommand == 'list':
                cli.list_message_history(args.limit)
            elif args.subcommand == 'export':
                cli.export_history(args.output_file, args.limit)
            else:
                # Default to list if no subcommand provided
                cli.list_message_history(20)
        
        elif args.command == 'schedule':
            if args.subcommand == 'list':
                cli.list_scheduled_messages(args.all)
            elif args.subcommand == 'add':
                cli.schedule_message(args.recipient, args.message, args.time, 
                                    args.service, args.recurring, args.interval)
            elif args.subcommand == 'cancel':
                cli.cancel_scheduled_message(args.id)
            else:
                cli.list_scheduled_messages()
        
        elif args.command == 'templates':
            if args.subcommand == 'list':
                cli.list_templates()
            elif args.subcommand == 'add':
                cli.add_template(args.name, args.content)
            elif args.subcommand == 'delete':
                cli.delete_template(args.id)
            else:
                cli.list_templates()
        
        elif args.command == 'services':
            if args.subcommand == 'list':
                cli.list_services()
            elif args.subcommand == 'configure':
                cli.configure_service(args.name, args.credentials)
            elif args.subcommand == 'activate':
                cli.set_active_service(args.name)
            elif args.subcommand == 'test':
                cli.test_service(args.name)
            else:
                cli.list_services()
        
        else:
            # If no command is provided, show help
            parse_args(['--help'])
    finally:
        # Shutdown CLI resources
        cli.shutdown()


if __name__ == "__main__":
    main() 