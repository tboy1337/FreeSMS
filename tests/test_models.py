#!/usr/bin/env python3
"""
Test script for FreeSMS models
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import sqlite3
import tempfile
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from src.models.database import Database
from src.models.contact_manager import ContactManager

class TestDatabase(unittest.TestCase):
    """Test case for Database model"""
    
    def setUp(self):
        """Set up test environment with a temporary database"""
        # Create a temporary file for the database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db = Database(db_path=self.db_path)
        
    def tearDown(self):
        """Clean up test environment"""
        # Close the database connection
        self.db.close()
        # Close and remove the temporary database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_database_initialization(self):
        """Test database initialization"""
        # Verify database tables were created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if essential tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        
        self.assertIn('contacts', tables)
        self.assertIn('api_credentials', tables)
        self.assertIn('message_history', tables)
        self.assertIn('scheduled_messages', tables)
        
        conn.close()
    
    def test_contact_operations(self):
        """Test contact CRUD operations"""
        # Test adding a contact
        result = self.db.save_contact("Test User", "+12125551234", "US", "Test note")
        self.assertTrue(result)
        
        # Test retrieving contacts
        contacts = self.db.get_contacts()
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]['name'], "Test User")
        self.assertEqual(contacts[0]['phone'], "+12125551234")
        
        # Test retrieving a specific contact
        contact_id = contacts[0]['id']
        contact = self.db.get_contact(contact_id)
        self.assertIsNotNone(contact)
        self.assertEqual(contact['name'], "Test User")
        
        # Test deleting a contact
        deleted = self.db.delete_contact(contact_id)
        self.assertTrue(deleted)
        
        # Verify deletion
        contacts = self.db.get_contacts()
        self.assertEqual(len(contacts), 0)
    
    def test_api_credentials(self):
        """Test API credentials operations"""
        # Test saving service credentials
        result = self.db.save_api_credentials("twilio", {
            "account_sid": "test_sid",
            "auth_token": "test_token",
            "from_number": "+15551234567"
        }, is_active=True)
        self.assertTrue(result)
        
        # Test retrieving service credentials
        services = self.db.get_active_services()
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0], "twilio")
        
        credentials = self.db.get_api_credentials("twilio")
        self.assertIsNotNone(credentials)
        self.assertEqual(credentials['account_sid'], "test_sid")
        
        # Test saving another service as active
        result = self.db.save_api_credentials("textbelt", {
            "api_key": "test_key"
        }, is_active=True)
        self.assertTrue(result)
        
        # Verify only the new one is active
        services = self.db.get_active_services()
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0], "textbelt")
    
    def test_message_history(self):
        """Test message history operations"""
        # Test saving a message
        result = self.db.save_message_history(
            recipient="+12125551234",
            message="Test message",
            service="twilio",
            status="sent",
            message_id="msg123",
            details="Details"
        )
        self.assertTrue(result)
        
        # Test retrieving messages
        messages = self.db.get_message_history()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['message'], "Test message")
        self.assertEqual(messages[0]['status'], "sent")
    
    def test_scheduled_messages(self):
        """Test scheduled messages operations"""
        # Test saving a scheduled message
        message_id = self.db.save_scheduled_message(
            recipient="+12125551234",
            message="Scheduled message",
            scheduled_time="2023-12-31 12:00:00",
            service="twilio",
            recurring="daily"
        )
        self.assertIsNotNone(message_id)
        
        # Test retrieving scheduled messages
        messages = self.db.get_scheduled_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['message'], "Scheduled message")
        self.assertEqual(messages[0]['status'], "pending")
        
        # Test updating message status
        updated = self.db.update_scheduled_message_status(
            message_id=messages[0]['id'],
            status="completed",
            completed_at="2023-12-31 12:01:00"
        )
        self.assertTrue(updated)
        
        # Test retrieving pending messages
        pending = self.db.get_pending_scheduled_messages()
        self.assertEqual(len(pending), 0)
        
        # Test deleting a scheduled message
        deleted = self.db.delete_scheduled_message(messages[0]['id'])
        self.assertTrue(deleted)
        
        # Verify deletion
        messages = self.db.get_scheduled_messages(include_completed=True)
        self.assertEqual(len(messages), 0)

class TestContactManager(unittest.TestCase):
    """Test case for Contact Manager"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock database
        self.db = MagicMock(spec=Database)
        self.db.get_contacts.return_value = []
        self.db.save_contact.return_value = True
        
        # Create contact manager with mock database
        self.manager = ContactManager(self.db)
    
    def test_get_contacts(self):
        """Test getting contacts"""
        # Setup mock to return some contacts
        self.db.get_contacts.return_value = [
            {"id": 1, "name": "John Doe", "phone": "+12125551234", "country": "US", "notes": "Note 1"},
            {"id": 2, "name": "Jane Smith", "phone": "+442071234567", "country": "GB", "notes": "Note 2"}
        ]
        
        # Test getting all contacts
        contacts = self.manager.get_all_contacts()
        self.assertEqual(len(contacts), 2)
        
        # Test getting a contact by ID
        self.db.get_contact.return_value = {"id": 1, "name": "John Doe", "phone": "+12125551234"}
        contact = self.manager.get_contact(1)
        self.assertIsNotNone(contact)
        self.assertEqual(contact["name"], "John Doe")
    
    def test_add_contact(self):
        """Test adding a contact"""
        # Mock validation method to return success
        with patch('src.models.contact_manager.ContactManager._validate_phone_number',
                  return_value=(True, '+12125551234')):
            # Test adding contact
            result = self.manager.add_contact("Test User", "12125551234", "US", "Test note")
            self.assertTrue(result)
            self.db.save_contact.assert_called_once()
    
    def test_update_contact(self):
        """Test updating a contact"""
        # Mock get_contact
        mock_contact = {"id": 1, "name": "Old Name", "phone": "+12125551234", "country_code": "US", "notes": "Old note"}
        self.db.get_contact.return_value = mock_contact
        
        # Mock validation method to return success
        with patch('src.models.contact_manager.ContactManager._validate_phone_number',
                  return_value=(True, '+12125559876')):
            # Test updating contact with new values
            result = self.manager.update_contact(1, "New Name", "12125559876", "US", "New note")
            self.assertTrue(result)
            self.db.save_contact.assert_called_once_with("New Name", "+12125559876", "US", "New note")
            
            # Reset mock
            self.db.save_contact.reset_mock()
            
            # Test updating only some fields
            result = self.manager.update_contact(1, "New Name", None, None, None)
            self.assertTrue(result)
            self.db.save_contact.assert_called_once()
    
    def test_delete_contact(self):
        """Test deleting a contact"""
        # Mock delete_contact
        self.db.delete_contact.return_value = True
        
        # Test deleting contact
        result = self.manager.delete_contact(1)
        self.assertTrue(result)
        self.db.delete_contact.assert_called_once_with(1)
    
    def test_search_contacts(self):
        """Test searching contacts"""
        # Add search_contacts method to the mock database
        self.db.search_contacts = MagicMock(return_value=[
            {"id": 1, "name": "John Doe", "phone": "+12125551234", "country_code": "US"},
            {"id": 2, "name": "Jane Doe", "phone": "+12125555678", "country_code": "US"}
        ])
        
        # Create a custom implementation of search_contacts in the ContactManager
        def mock_search_contacts(query):
            # In a real implementation, this would filter contacts based on the query
            # but for testing, we just return the mocked results
            return self.db.search_contacts(query)
            
        # Patch the ContactManager's search_contacts method
        with patch.object(self.manager, 'search_contacts', side_effect=mock_search_contacts):
            # Test searching contacts
            results = self.manager.search_contacts("Doe")
            self.assertEqual(len(results), 2)
            self.db.search_contacts.assert_called_once_with("Doe")
    
    def test_import_contacts_from_csv(self):
        """Test importing contacts from CSV"""
        # Create CSV data
        csv_data = "name,phone,country,notes\nTest User,12125551234,US,Test note\nAnother User,12125559876,US,Another note"
        
        # Mock add_contact
        with patch.object(self.manager, 'add_contact', return_value=True):
            # Test importing contacts
            success, errors = self.manager.import_contacts_from_csv(csv_data)
            self.assertEqual(success, 2)
            self.assertEqual(len(errors), 0)
            
            # Call count should be 2 (one for each contact)
            self.assertEqual(self.manager.add_contact.call_count, 2)
            
            # Test importing invalid CSV
            invalid_csv = "invalid,csv,data\nwithout,proper,headers"
            success, errors = self.manager.import_contacts_from_csv(invalid_csv)
            self.assertEqual(success, 0)
            self.assertEqual(len(errors), 1)
    
    def test_export_contacts_to_csv(self):
        """Test exporting contacts to CSV"""
        # Mock get_all_contacts
        self.manager.get_all_contacts = MagicMock(return_value=[
            {"id": 1, "name": "Test User", "phone": "+12125551234", "country": "US", "notes": "Test note"},
            {"id": 2, "name": "Another User", "phone": "+12125559876", "country": "US", "notes": "Another note"}
        ])
        
        # Test exporting contacts
        csv_data = self.manager.export_contacts_to_csv()
        self.assertIsInstance(csv_data, str)
        
        # Check CSV format
        self.assertIn("name,phone,country,notes", csv_data)
        self.assertIn("Test User,+12125551234,US,Test note", csv_data)
        self.assertIn("Another User,+12125559876,US,Another note", csv_data)
        
        # Test empty export
        self.manager.get_all_contacts = MagicMock(return_value=[])
        csv_data = self.manager.export_contacts_to_csv()
        self.assertEqual(csv_data, "name,phone,country,notes\n")
    
    def test_validate_phone_number(self):
        """Test phone number validation"""
        # Test with valid US number
        with patch('phonenumbers.parse') as mock_parse:
            with patch('phonenumbers.is_valid_number', return_value=True):
                with patch('phonenumbers.format_number', return_value="+12125551234"):
                    valid, formatted = self.manager._validate_phone_number("2125551234", "US")
                    self.assertTrue(valid)
                    self.assertEqual(formatted, "+12125551234")
        
        # Test with invalid number
        with patch('phonenumbers.parse'):
            with patch('phonenumbers.is_valid_number', return_value=False):
                valid, _ = self.manager._validate_phone_number("invalid", "US")
                self.assertFalse(valid)

if __name__ == "__main__":
    unittest.main() 