"""
Contact Manager - Handles operations on contacts
"""

import csv
import io
from typing import Any

import phonenumbers

from src.models.database import Database


class ContactManager:
    """Manages contact operations"""

    def __init__(self, database: Database):
        """Initialize with a database connection"""
        self.db = database

    def add_contact(self, name: str, phone: str, country: str, notes: str = "") -> bool:
        """Add a new contact or update an existing one"""
        # Validate the phone number format
        valid, formatted = self._validate_phone_number(phone, country)
        if not valid:
            return False

        return self.db.save_contact(name, formatted, country, notes)

    def get_all_contacts(self) -> list[dict[str, Any]]:
        """Get all contacts"""
        contacts = self.db.get_contacts()
        return [dict(contact) for contact in contacts]

    def get_contact(self, contact_id: int) -> dict[str, Any] | None:
        """Get a contact by ID"""
        contact = self.db.get_contact(contact_id)
        return dict(contact) if contact else None

    def update_contact(
        self,
        contact_id: int,
        name: str | None = None,
        phone: str | None = None,
        country: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """Update a contact"""
        # Get current contact
        if not (current := self.db.get_contact(contact_id)):
            return False

        # Use current values if not provided
        name = name if name is not None else current["name"]
        phone = phone if phone is not None else current["phone"]
        country = country if country is not None else current.get("country", "")
        notes = notes if notes is not None else current.get("notes", "")

        # Validate phone number if changed
        if phone != current["phone"] or country != current.get("country", ""):
            valid, formatted = self._validate_phone_number(phone, country)
            if not valid:
                return False
            phone = formatted

        return self.db.save_contact(name, phone, country, notes)

    def delete_contact(self, contact_id: int) -> bool:
        """Delete a contact"""
        return self.db.delete_contact(contact_id)

    def search_contacts(self, query: str) -> list[dict[str, Any]]:
        """Search contacts by name or phone number"""
        contacts = self.db.search_contacts(query)
        return [dict(contact) for contact in contacts]

    def import_contacts_from_csv(self, csv_data: str) -> tuple[int, list[str]]:
        """Import contacts from CSV data"""
        success_count = 0
        errors = []

        csv_file = io.StringIO(csv_data)
        reader = csv.DictReader(csv_file)

        required_fields = ["name", "phone"]

        # Check if required fields are present
        if not (fieldnames := reader.fieldnames):
            return 0, ["Invalid CSV format: No header row found"]

        for field in required_fields:
            if field not in fieldnames:
                return 0, [f"Required field '{field}' missing from CSV"]

        # Process contacts
        line_num = 1  # Skip header row in count
        for row in reader:
            line_num += 1
            name = row.get("name", "").strip()
            phone = row.get("phone", "").strip()
            country = (
                row.get("country", "").strip() or row.get("country_code", "").strip()
            )
            notes = row.get("notes", "").strip()

            # Skip empty rows
            if not name and not phone:
                continue

            # Validate required fields
            if not name:
                errors.append(f"Line {line_num}: Name is required")
                continue

            if not phone:
                errors.append(f"Line {line_num}: Phone is required")
                continue

            # If country not provided in CSV, try to extract from phone
            if not country:
                try:
                    parsed = phonenumbers.parse(phone, None)
                    country = phonenumbers.region_code_for_number(parsed)
                except phonenumbers.NumberParseException:
                    country = "US"  # Default to US if not specified

            # Add the contact
            if self.add_contact(name, phone, country, notes):
                success_count += 1
            else:
                errors.append(f"Line {line_num}: Failed to add contact '{name}'")

        return success_count, errors

    def export_contacts_to_csv(self) -> str:
        """Export all contacts to CSV format"""
        if not (contacts := self.get_all_contacts()):
            return "name,phone,country,notes\n"

        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["name", "phone", "country", "notes"]
        )
        writer.writeheader()

        for contact in contacts:
            # Get country data from either 'country' or 'country_code' field
            country_code = contact.get("country", contact.get("country_code", ""))

            writer.writerow(
                {
                    "name": contact["name"],
                    "phone": contact["phone"],
                    "country": country_code,
                    "notes": contact.get("notes", ""),
                }
            )

        return output.getvalue()

    def _validate_phone_number(self, phone: str, country: str) -> tuple[bool, str]:
        """Validate and format a phone number"""
        try:
            region = (
                country.upper() if country and not country.startswith("+") else None
            )
            if phone.startswith("+"):
                parsed = phonenumbers.parse(phone, None)
            else:
                parsed = phonenumbers.parse(phone, region or "US")

            # Check if it's a valid number
            if not phonenumbers.is_valid_number(parsed):
                return False, ""

            # Format to E.164 format
            formatted = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )

            return True, formatted

        except phonenumbers.NumberParseException:
            return False, ""
