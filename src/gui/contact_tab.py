"""
Contact Tab - UI for managing contacts
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
    QFormLayout, QTextEdit, QComboBox, QHeaderView, QMessageBox,
    QAbstractItemView
)
from PySide6.QtCore import Qt
import pycountry
import phonenumbers

class ContactTab(QWidget):
    """Contact management tab"""
    
    def __init__(self, app):
        """Initialize the contacts tab"""
        super().__init__()
        self.app = app
        self.selection_mode = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        self._create_components()
        self.load_contacts()
    
    def _create_components(self):
        """Create tab components"""
        layout = self.layout()
        
        # Top frame for search and actions
        top_frame = QWidget()
        top_layout = QHBoxLayout(top_frame)
        
        # Search field
        search_label = QLabel("Search:")
        top_layout.addWidget(search_label)
        
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search contacts...")
        self.search_entry.returnPressed.connect(self._on_search)
        top_layout.addWidget(self.search_entry)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._on_search)
        top_layout.addWidget(self.search_button)
        
        top_layout.addStretch()
        
        # Action buttons
        self.add_button = QPushButton("Add Contact")
        self.add_button.clicked.connect(self._on_add_contact)
        top_layout.addWidget(self.add_button)
        
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self._on_import)
        top_layout.addWidget(self.import_button)
        
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self._on_export)
        top_layout.addWidget(self.export_button)
        
        layout.addWidget(top_frame)
        
        # Contact list
        self.contact_table = QTableWidget()
        self.contact_table.setColumnCount(3)
        self.contact_table.setHorizontalHeaderLabels(["Name", "Phone", "Country"])
        
        # Configure table
        header = self.contact_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        self.contact_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.contact_table.doubleClicked.connect(self._on_contact_selected)
        
        layout.addWidget(self.contact_table)
        
        # Contact details form
        details_group = QGroupBox("Contact Details")
        details_layout = QFormLayout()
        
        self.name_entry = QLineEdit()
        details_layout.addRow("Name:", self.name_entry)
        
        self.phone_entry = QLineEdit()
        details_layout.addRow("Phone:", self.phone_entry)
        
        self.country_combo = QComboBox()
        self._populate_countries()
        details_layout.addRow("Country:", self.country_combo)
        
        self.notes_entry = QTextEdit()
        self.notes_entry.setMaximumHeight(100)
        details_layout.addRow("Notes:", self.notes_entry)
        
        # Form buttons
        form_buttons = QWidget()
        form_button_layout = QHBoxLayout(form_buttons)
        form_button_layout.addStretch()
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_form)
        form_button_layout.addWidget(self.clear_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self._on_delete_contact)
        form_button_layout.addWidget(self.delete_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save_contact)
        form_button_layout.addWidget(self.save_button)
        
        details_layout.addRow(form_buttons)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        self._clear_form()
    
    def _populate_countries(self):
        """Populate the country dropdown"""
        countries = []
        self.country_codes = {}
        
        for country in pycountry.countries:
            try:
                phone_code = phonenumbers.country_code_for_region(country.alpha_2)
                if phone_code:
                    display_name = f"{country.name} (+{phone_code})"
                    countries.append((country.alpha_2, display_name))
                    self.country_codes[display_name] = country.alpha_2
            except:
                pass
        
        countries.sort(key=lambda x: x[1])
        
        for code, name in countries:
            self.country_combo.addItem(name)
        
        # Set default to United States
        for i in range(self.country_combo.count()):
            if self.country_combo.itemText(i).startswith("United States"):
                self.country_combo.setCurrentIndex(i)
                break
    
    def load_contacts(self):
        """Load contacts from the database"""
        try:
            contacts = self.app.contact_manager.get_all_contacts()
            
            self.contact_table.setRowCount(len(contacts))
            
            for row, contact in enumerate(contacts):
                # Name
                name_item = QTableWidgetItem(contact['name'])
                name_item.setData(Qt.ItemDataRole.UserRole, contact['id'])
                self.contact_table.setItem(row, 0, name_item)
                
                # Phone
                phone_item = QTableWidgetItem(contact['phone'])
                self.contact_table.setItem(row, 1, phone_item)
                
                # Country
                country_name = contact['country']
                try:
                    country = pycountry.countries.get(alpha_2=contact['country'])
                    if country:
                        country_name = country.name
                except:
                    pass
                
                country_item = QTableWidgetItem(country_name)
                self.contact_table.setItem(row, 2, country_item)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load contacts: {str(e)}")
    
    def _on_search(self):
        """Handle search button click"""
        query = self.search_entry.text().strip()
        
        if not query:
            self.load_contacts()
            return
        
        try:
            contacts = self.app.contact_manager.search_contacts(query)
            
            self.contact_table.setRowCount(len(contacts))
            
            for row, contact in enumerate(contacts):
                name_item = QTableWidgetItem(contact['name'])
                name_item.setData(Qt.ItemDataRole.UserRole, contact['id'])
                self.contact_table.setItem(row, 0, name_item)
                
                phone_item = QTableWidgetItem(contact['phone'])
                self.contact_table.setItem(row, 1, phone_item)
                
                country_name = contact['country']
                try:
                    country = pycountry.countries.get(alpha_2=contact['country'])
                    if country:
                        country_name = country.name
                except:
                    pass
                
                country_item = QTableWidgetItem(country_name)
                self.contact_table.setItem(row, 2, country_item)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Search failed: {str(e)}")
    
    def _on_add_contact(self):
        """Handle add contact button click"""
        self._clear_form()
    
    def _on_contact_selected(self, index):
        """Handle contact selection via double-click"""
        row = index.row()
        name_item = self.contact_table.item(row, 0)
        if not name_item:
            return
            
        contact_id = name_item.data(Qt.ItemDataRole.UserRole)
        
        if self.selection_mode:
            self.app.load_contact_to_message(contact_id)
            self.selection_mode = False
            return
        
        # Load for editing
        try:
            contact = self.app.contact_manager.get_contact(contact_id)
            if contact:
                self.contact_id = contact_id
                self.name_entry.setText(contact['name'])
                self.phone_entry.setText(contact['phone'])
                self.notes_entry.setPlainText(contact.get('notes', ''))
                
                # Set country
                country_code = contact.get('country_code', 'US')
                for i in range(self.country_combo.count()):
                    item_text = self.country_combo.itemText(i)
                    if self.country_codes.get(item_text) == country_code:
                        self.country_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load contact: {str(e)}")
    
    def _on_save_contact(self):
        """Handle save contact button click"""
        name = self.name_entry.text().strip()
        phone = self.phone_entry.text().strip()
        country = self.country_combo.currentText()
        notes = self.notes_entry.toPlainText()
        
        if not name:
            QMessageBox.critical(self, "Error", "Name is required")
            self.name_entry.setFocus()
            return
            
        if not phone:
            QMessageBox.critical(self, "Error", "Phone number is required")
            self.phone_entry.setFocus()
            return
            
        if not country:
            QMessageBox.critical(self, "Error", "Country is required")
            return
        
        country_code = self.country_codes.get(country, "US")
        
        try:
            if hasattr(self, 'contact_id'):
                success = self.app.contact_manager.update_contact(
                    self.contact_id, name, phone, country_code, notes)
            else:
                success = self.app.contact_manager.add_contact(name, phone, country_code, notes)
            
            if success:
                QMessageBox.information(self, "Success", "Contact saved successfully")
                self._clear_form()
                self.load_contacts()
            else:
                QMessageBox.critical(self, "Error", "Failed to save contact")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save contact: {str(e)}")
    
    def _on_delete_contact(self):
        """Handle delete contact button click"""
        if hasattr(self, 'contact_id'):
            reply = QMessageBox.question(self, "Confirm Delete", 
                                       "Are you sure you want to delete this contact?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    success = self.app.contact_manager.delete_contact(self.contact_id)
                    if success:
                        QMessageBox.information(self, "Success", "Contact deleted successfully")
                        self._clear_form()
                        self.load_contacts()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to delete contact")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete contact: {str(e)}")
        else:
            QMessageBox.information(self, "Information", "Please select a contact to delete")
    
    def _on_import(self):
        """Handle import button click"""
        QMessageBox.information(self, "Import", "Import functionality will be implemented soon.")
    
    def _on_export(self):
        """Handle export button click"""
        QMessageBox.information(self, "Export", "Export functionality will be implemented soon.")
    
    def _clear_form(self):
        """Clear the contact form"""
        self.name_entry.clear()
        self.phone_entry.clear()
        self.notes_entry.clear()
        
        # Reset country to default
        for i in range(self.country_combo.count()):
            if self.country_combo.itemText(i).startswith("United States"):
                self.country_combo.setCurrentIndex(i)
                break
        
        if hasattr(self, 'contact_id'):
            delattr(self, 'contact_id')
    
    def set_selection_mode(self, mode=True):
        """Set selection mode for choosing a contact"""
        self.selection_mode = mode
        
        if mode:
            self.app.set_status("Select a contact for the message")
        else:
            self.app.set_status("Ready")