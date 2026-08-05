"""
Message Tab - UI for composing and sending SMS messages
"""

import phonenumbers
import pycountry
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.ui_helpers import (
    MessageTemplateMixin,
    create_tab_layout,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MessageTab(QWidget, MessageTemplateMixin):
    """Message composition and sending tab"""

    def __init__(self, app):
        """Initialize the message tab"""
        super().__init__()
        self.templates: dict[str, str] = {}
        create_tab_layout(self, app)
        self._create_components()

        # Populate countries
        self._populate_countries()

        # Set up validation and bindings
        self._setup_validation()

    def _create_components(self):
        """Create tab components"""
        layout = self.layout()

        # Recipient section
        recipient_group = QGroupBox("Recipient")
        recipient_layout = QFormLayout()

        # Country dropdown
        self.country_combo = QComboBox()
        recipient_layout.addRow("Country:", self.country_combo)

        # Phone number entry
        phone_layout = QHBoxLayout()
        self.recipient_entry = QLineEdit()
        self.recipient_entry.setPlaceholderText("Enter phone number...")
        phone_layout.addWidget(self.recipient_entry)

        self.contact_button = QPushButton("Choose Contact")
        self.contact_button.clicked.connect(self._on_choose_contact)
        phone_layout.addWidget(self.contact_button)

        recipient_layout.addRow("Phone Number:", phone_layout)
        recipient_group.setLayout(recipient_layout)
        layout.addWidget(recipient_group)

        # Message section
        message_group = QGroupBox("Message")
        message_layout = QVBoxLayout()

        # Template dropdown
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(self._on_template_selected)
        template_layout.addWidget(self.template_combo)
        template_layout.addStretch()
        message_layout.addLayout(template_layout)

        # Message text entry
        self.message_text = QTextEdit()
        self.message_text.setPlaceholderText("Enter your message here...")
        self.message_text.textChanged.connect(self._update_char_count)
        message_layout.addWidget(self.message_text)

        # Character counter
        self.char_count_label = QLabel("0/160 characters")
        self.char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        message_layout.addWidget(self.char_count_label)

        message_group.setLayout(message_layout)
        layout.addWidget(message_group)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._on_clear)
        button_layout.addWidget(self.clear_button)

        self.schedule_button = QPushButton("Schedule")
        self.schedule_button.clicked.connect(self._on_schedule_message)
        button_layout.addWidget(self.schedule_button)

        self.send_button = QPushButton("Send Message")
        self.send_button.setProperty("class", "primary")
        self.send_button.clicked.connect(self._on_send_message)
        button_layout.addWidget(self.send_button)

        layout.addLayout(button_layout)

    def _populate_countries(self):
        """Populate the country dropdown"""
        countries = []
        for country in pycountry.countries:
            try:
                phone_code = phonenumbers.country_code_for_region(country.alpha_2)
                if phone_code:
                    countries.append(f"{country.name} (+{phone_code})")
            except (KeyError, AttributeError):
                pass

        countries.sort()
        self.country_combo.addItems(countries)

        # Set default to United States
        for i, country in enumerate(countries):
            if country.startswith("United States"):
                self.country_combo.setCurrentIndex(i)
                break

    def _setup_validation(self):
        """Set up validation and event bindings"""
        self._load_templates()

    def _on_choose_contact(self):
        """Open contact selection dialog"""
        self.app.tab_widget.setCurrentIndex(1)  # Switch to Contacts tab
        if hasattr(self.app.tabs.get("contacts"), "set_selection_mode"):
            self.app.tabs["contacts"].set_selection_mode(True)

    def _on_send_message(self):
        """Handle send message button click"""
        recipient = self.recipient_entry.text().strip()
        message = self.message_text.toPlainText().strip()

        if not recipient:
            QMessageBox.critical(self, "Error", "Please enter a recipient phone number")
            self.recipient_entry.setFocus()
            return

        if not message:
            QMessageBox.critical(self, "Error", "Please enter a message")
            self.message_text.setFocus()
            return

        # Get the country code
        country = self.country_combo.currentText()
        country_code = ""
        if country:
            if (start := country.rfind("(+")) >= 0 and (
                end := country.rfind(")")
            ) > start:
                country_code = country[start : end + 1]

        # Format the recipient with country code if needed
        if country_code and not recipient.startswith("+"):
            recipient = f"{country_code[1:-1]}{recipient}"

        # Send the message
        self.app.send_message(recipient, message)

    def _on_schedule_message(self):
        """Open schedule dialog for this message"""
        recipient = self.recipient_entry.text().strip()
        message = self.message_text.toPlainText().strip()

        if not recipient:
            QMessageBox.critical(self, "Error", "Please enter a recipient phone number")
            self.recipient_entry.setFocus()
            return

        if not message:
            QMessageBox.critical(self, "Error", "Please enter a message")
            self.message_text.setFocus()
            return

        # Get the country code
        country = self.country_combo.currentText()
        country_code = ""
        if country:
            if (start := country.rfind("(+")) >= 0 and (
                end := country.rfind(")")
            ) > start:
                country_code = country[start : end + 1]

        # Format the recipient with country code if needed
        if country_code and not recipient.startswith("+"):
            recipient = f"{country_code[1:-1]}{recipient}"

        # Switch to scheduler tab
        self.app.tab_widget.setCurrentIndex(3)  # Index 3 is the Scheduler tab

        # Populate the scheduler with our message
        if hasattr(self.app.tabs.get("schedule"), "set_new_scheduled_message"):
            self.app.tabs["schedule"].set_new_scheduled_message(recipient, message)

    def _on_clear(self):
        """Clear the form"""
        self.recipient_entry.clear()
        self.message_text.clear()
        self.template_combo.setCurrentIndex(0)
        self._update_char_count()
        self.recipient_entry.setFocus()

    def set_recipient(self, phone):
        """Set the recipient field"""
        self.recipient_entry.setText(phone)
        self.message_text.setFocus()
