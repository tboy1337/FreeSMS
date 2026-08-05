"""
Schedule Tab - UI for scheduling and automating messages
"""

from datetime import datetime

from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.ui_helpers import (
    MessageTemplateMixin,
    add_cancel_button_row,
    create_horizontal_splitter,
    create_split_left_panel,
    create_tab_layout,
)
from src.security.validation import InputValidator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScheduleTab(QWidget, MessageTemplateMixin):
    """Schedule and automation tab"""

    def __init__(self, app):
        """Initialize the schedule tab"""
        super().__init__()
        self.templates: dict[str, str] = {}
        create_tab_layout(self, app)

        self._create_components()
        self.load_scheduled_messages()

    def _create_components(self):
        """Create tab components"""
        # Create splitter for left and right panels
        splitter = create_horizontal_splitter(self)

        # Left panel for scheduled messages list
        left_widget, left_layout, header_layout = create_split_left_panel(
            "Scheduled Messages"
        )

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_scheduled_messages)
        header_layout.addStretch()
        header_layout.addWidget(refresh_button)

        # Filter frame
        filter_frame = QWidget()
        filter_layout = QHBoxLayout(filter_frame)

        filter_layout.addWidget(QLabel("Show:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Pending", "Sent", "Failed"])
        filter_layout.addWidget(self.status_combo)

        filter_button = QPushButton("Apply Filter")
        filter_button.clicked.connect(self.load_scheduled_messages)
        filter_layout.addWidget(filter_button)

        filter_layout.addStretch()
        left_layout.addWidget(filter_frame)

        # Message list
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(4)
        self.schedule_table.setHorizontalHeaderLabels(
            ["Recipient", "Scheduled Time", "Recurrence", "Status"]
        )

        header = self.schedule_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.schedule_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        left_layout.addWidget(self.schedule_table)
        splitter.addWidget(left_widget)

        # Right panel for schedule form
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        form_title = QLabel("Schedule Message")
        form_title.setProperty("class", "title")
        right_layout.addWidget(form_title)

        # Form group
        form_group = QGroupBox()
        form_layout = QFormLayout(form_group)

        # Recipient
        recipient_layout = QHBoxLayout()
        self.recipient_entry = QLineEdit()
        recipient_layout.addWidget(self.recipient_entry)

        contact_button = QPushButton("Choose Contact")
        contact_button.clicked.connect(self._on_choose_contact)
        recipient_layout.addWidget(contact_button)

        form_layout.addRow("Recipient:", recipient_layout)

        # Date and time
        datetime_layout = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate().addDays(1))
        datetime_layout.addWidget(self.date_edit)

        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(12, 0))
        datetime_layout.addWidget(self.time_edit)

        form_layout.addRow("Date & Time:", datetime_layout)

        # Recurrence
        recurrence_layout = QVBoxLayout()
        self.recurrence_combo = QComboBox()
        self.recurrence_combo.addItems(["Once", "Daily", "Weekly", "Monthly", "Custom"])
        self.recurrence_combo.currentTextChanged.connect(self._on_recurrence_changed)
        recurrence_layout.addWidget(self.recurrence_combo)

        # Custom recurrence frame (hidden by default)
        self.custom_frame = QWidget()
        custom_layout = QHBoxLayout(self.custom_frame)
        custom_layout.addWidget(QLabel("Every"))
        self.custom_days_spin = QSpinBox()
        self.custom_days_spin.setMinimum(1)
        self.custom_days_spin.setMaximum(365)
        self.custom_days_spin.setValue(1)
        custom_layout.addWidget(self.custom_days_spin)
        custom_layout.addWidget(QLabel("days"))
        custom_layout.addStretch()

        self.custom_frame.hide()
        recurrence_layout.addWidget(self.custom_frame)

        form_layout.addRow("Recurrence:", recurrence_layout)

        # SMS Service
        self.service_combo = QComboBox()
        self.service_combo.addItem("Default")
        self._update_services()
        form_layout.addRow("SMS Service:", self.service_combo)

        # Message text
        self.message_text = QTextEdit()
        self.message_text.setMaximumHeight(200)
        self.message_text.textChanged.connect(self._update_char_count)
        form_layout.addRow("Message:", self.message_text)

        # Character counter
        self.char_count_label = QLabel("0/160 characters")
        self.char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addRow(self.char_count_label)

        # Template dropdown
        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(self._on_template_selected)
        form_layout.addRow("Template:", self.template_combo)

        right_layout.addWidget(form_group)

        # Buttons
        button_layout = add_cancel_button_row(right_layout, self._clear_form)

        self.save_button = QPushButton("Schedule")
        self.save_button.clicked.connect(self._on_save_schedule)
        button_layout.addWidget(self.save_button)
        right_layout.addStretch()

        splitter.addWidget(right_widget)

        # Load templates
        self._load_templates()
        self._clear_form()

    def _update_services(self):
        """Update the services dropdown"""
        try:
            services = ["Default"] + self.app.service_manager.get_configured_services()
            self.service_combo.clear()
            for service in services:
                self.service_combo.addItem(service)
        except (OSError, RuntimeError, KeyError, TypeError, ValueError):
            logger.debug("Could not load SMS services for schedule tab", exc_info=True)
            self.service_combo.clear()
            self.service_combo.addItem("Default")

    def _on_recurrence_changed(self, recurrence):
        """Handle recurrence selection change"""
        if recurrence == "Custom":
            self.custom_frame.show()
        else:
            self.custom_frame.hide()

    def _on_choose_contact(self):
        """Open contact selection dialog"""
        self.app.tab_widget.setCurrentIndex(1)  # Switch to Contacts tab
        if hasattr(self.app.tabs.get("contacts"), "set_selection_mode"):
            self.app.tabs["contacts"].set_selection_mode(True)

    def load_scheduled_messages(self):
        """Load scheduled messages from the database"""
        try:
            if (status_filter := self.status_combo.currentText().lower()) == "all":
                messages = self.app.scheduler.get_scheduled_messages()
            else:
                messages = self.app.scheduler.get_scheduled_messages(
                    status=status_filter
                )

            self.schedule_table.setRowCount(len(messages))

            for row, message in enumerate(messages):
                # Format schedule time
                if schedule_time := message["scheduled_time"]:
                    try:
                        dt = datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
                        schedule_time = dt.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        pass

                # Format recurrence
                recurrence = message.get("recurring", "Once") or "Once"

                # Create table items
                recipient_item = QTableWidgetItem(message["recipient"])
                recipient_item.setData(Qt.ItemDataRole.UserRole, message["id"])
                self.schedule_table.setItem(row, 0, recipient_item)

                self.schedule_table.setItem(
                    row, 1, QTableWidgetItem(str(schedule_time))
                )
                self.schedule_table.setItem(
                    row, 2, QTableWidgetItem(recurrence.capitalize())
                )
                self.schedule_table.setItem(
                    row, 3, QTableWidgetItem(message["status"].capitalize())
                )

        except (OSError, RuntimeError, KeyError, TypeError, ValueError) as exc:
            logger.exception("Failed to load scheduled messages: %s", exc)
            QMessageBox.critical(
                self, "Error", f"Failed to load scheduled messages: {exc!s}"
            )

    def _on_save_schedule(self):
        """Save or update a scheduled message"""
        recipient = self.recipient_entry.text().strip()
        message = self.message_text.toPlainText().strip()

        if not recipient:
            QMessageBox.critical(self, "Error", "Recipient is required")
            return

        if not message:
            QMessageBox.critical(self, "Error", "Message is required")
            return

        valid_phone, phone_error = InputValidator.validate_phone_input(recipient)
        if not valid_phone:
            QMessageBox.critical(self, "Invalid Phone Number", phone_error)
            return

        valid_msg, msg_error = InputValidator.validate_message(message)
        if not valid_msg:
            QMessageBox.critical(self, "Invalid Message", msg_error)
            return

        # Get schedule time
        date = self.date_edit.date().toPython()
        time = self.time_edit.time().toPython()
        if (schedule_time := datetime.combine(date, time)) <= datetime.now():
            QMessageBox.critical(self, "Error", "Schedule time must be in the future")
            return

        # Get recurrence
        recurrence = self.recurrence_combo.currentText().lower()
        if recurrence == "once":
            recurrence = None
            recurrence_data = None
        elif recurrence == "custom":
            days = self.custom_days_spin.value()
            recurrence_data = {"days_interval": days}
        else:
            recurrence_data = None

        # Get service
        if (service := self.service_combo.currentText()) == "Default":
            service = None

        try:
            message_id = self.app.scheduler.schedule_message(
                recipient=recipient,
                message=message,
                schedule_time=schedule_time,
                recurrence=recurrence,
                recurrence_data=recurrence_data,
                service=service,
            )

            if message_id:
                QMessageBox.information(
                    self, "Success", "Message scheduled successfully"
                )
                self.load_scheduled_messages()
                self._clear_form()
            else:
                QMessageBox.critical(self, "Error", "Failed to schedule message")

        except (OSError, RuntimeError, KeyError, TypeError, ValueError) as exc:
            logger.exception("Failed to schedule message: %s", exc)
            QMessageBox.critical(self, "Error", f"Failed to schedule message: {exc!s}")

    def _clear_form(self):
        """Clear the schedule form"""
        self.recipient_entry.clear()
        self.message_text.clear()

        # Reset date/time to tomorrow at noon
        tomorrow = QDate.currentDate().addDays(1)
        self.date_edit.setDate(tomorrow)
        self.time_edit.setTime(QTime(12, 0))

        # Reset recurrence
        self.recurrence_combo.setCurrentText("Once")
        self.custom_frame.hide()
        self.custom_days_spin.setValue(1)

        # Reset service
        self.service_combo.setCurrentText("Default")

        # Reset template
        self.template_combo.setCurrentIndex(0)

        # Update char count
        self._update_char_count()

        # Reset button text
        self.save_button.setText("Schedule")

    def set_new_scheduled_message(self, recipient, message):
        """Set up a new scheduled message with the given recipient and message"""
        self._clear_form()

        self.recipient_entry.setText(recipient)
        self.message_text.setPlainText(message)
        self._update_char_count()

        self.date_edit.setFocus()
