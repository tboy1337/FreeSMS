"""Tests for ContactManager."""

import os
import sys
import tempfile

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.models.contact_manager import ContactManager
from src.models.database import Database


@pytest.fixture
def contact_manager():
    """ContactManager backed by a temporary database."""
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    db = Database(db_path=db_path)
    manager = ContactManager(db)
    yield manager
    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


def test_add_contact_invalid_phone(contact_manager):
    """Invalid phone numbers are rejected."""
    assert not contact_manager.add_contact("Alice", "invalid", "US")


def test_get_contact_missing(contact_manager):
    """Missing contacts return None."""
    assert contact_manager.get_contact(9999) is None


def test_update_contact_missing(contact_manager):
    """Updating a missing contact returns False."""
    assert not contact_manager.update_contact(9999, name="Nobody")


def test_update_contact_invalid_phone(contact_manager):
    """Phone validation runs when phone or country changes."""
    contact_manager.add_contact("Bob", "+12125551234", "US")
    contact = contact_manager.get_all_contacts()[0]
    assert not contact_manager.update_contact(contact["id"], phone="bad", country="US")


def test_delete_contact(contact_manager):
    """Contacts can be deleted."""
    contact_manager.add_contact("Carol", "+12125551234", "US")
    contact = contact_manager.get_all_contacts()[0]
    assert contact_manager.delete_contact(contact["id"])


def test_search_contacts(contact_manager):
    """Contacts can be searched by name."""
    contact_manager.add_contact("Dave", "+12125551234", "US")
    results = contact_manager.search_contacts("Dave")
    assert len(results) == 1


def test_import_contacts_from_csv_invalid_header(contact_manager):
    """CSV without headers is rejected."""
    count, errors = contact_manager.import_contacts_from_csv("no-header-data")
    assert count == 0
    assert errors


def test_import_contacts_from_csv_missing_phone_column(contact_manager):
    """CSV missing required columns is rejected."""
    csv_data = "name\nAlice\n"
    count, errors = contact_manager.import_contacts_from_csv(csv_data)
    assert count == 0
    assert any("phone" in error for error in errors)


def test_import_contacts_from_csv_row_errors(contact_manager):
    """CSV rows with missing fields are reported as errors."""
    csv_data = "name,phone,country,notes\n,5551234,US,\nAlice,,US,\n"
    count, errors = contact_manager.import_contacts_from_csv(csv_data)
    assert count == 0
    assert len(errors) >= 2


def test_import_contacts_from_csv_success(contact_manager):
    """Valid CSV rows are imported."""
    csv_data = "name,phone,country,notes\nEve,+12125551234,US,note\n"
    count, errors = contact_manager.import_contacts_from_csv(csv_data)
    assert count == 1
    assert not errors


def test_import_contacts_skips_empty_rows(contact_manager):
    """Blank CSV rows are skipped without error."""
    csv_data = "name,phone,country,notes\n,,,\nGina,+12125551234,US,\n"
    count, errors = contact_manager.import_contacts_from_csv(csv_data)
    assert count == 1
    assert not errors


def test_import_contacts_defaults_country_on_parse_error(contact_manager):
    """Invalid phone parsing defaults country to US before validation."""
    csv_data = "name,phone,notes\nHenry,not-a-phone,note\n"
    count, errors = contact_manager.import_contacts_from_csv(csv_data)
    assert count == 0
    assert any("Henry" in error for error in errors)


def test_import_contacts_reports_add_failure(contact_manager, monkeypatch):
    """Failed contact inserts are reported per CSV row."""
    monkeypatch.setattr(contact_manager, "add_contact", lambda *_args, **_kwargs: False)
    csv_data = "name,phone,country,notes\nIvy,+12125551234,US,\n"
    count, errors = contact_manager.import_contacts_from_csv(csv_data)
    assert count == 0
    assert any("Ivy" in error for error in errors)


def test_import_contacts_extract_country_from_phone(contact_manager):
    """Country can be inferred from an E.164 phone number."""
    csv_data = "name,phone,notes\nFrank,+12125551234,note\n"
    count, errors = contact_manager.import_contacts_from_csv(csv_data)
    assert count == 1
    assert not errors


def test_export_contacts_empty(contact_manager):
    """Exporting with no contacts returns header only."""
    exported = contact_manager.export_contacts_to_csv()
    assert exported == "name,phone,country,notes\n"


def test_export_contacts_with_data(contact_manager):
    """Contacts are exported as CSV rows."""
    contact_manager.add_contact("Grace", "+12125551234", "US", "friend")
    exported = contact_manager.export_contacts_to_csv()
    assert "Grace" in exported
    assert "+12125551234" in exported
