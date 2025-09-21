"""
Schedule Tab - UI for scheduling and automating messages
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit,
    QCheckBox, QSpinBox, QHeaderView, QAbstractItemView,
    QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QDate, QTime
from datetime import datetime, timedelta

class ScheduleTab(QWidget):
    """Schedule and automation tab"""
    
    def __init__(self, app):
        """Initialize the schedule tab"""
        super().__init__()
        self.app = app
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        self._create_components()
        self.load_scheduled_messages()
    
    def _create_components(self):
        """Create tab components"""
        # Create splitter for left and right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout().addWidget(splitter)
        
        # Left panel for scheduled messages list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Header and controls
        header_frame = QWidget()
        header_layout = QHBoxLayout(header_frame)
        
        title_label = QLabel("Scheduled Messages")
        title_label.setProperty("class", "title")
        header_layout.addWidget(title_label)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_scheduled_messages)
        header_layout.addStretch()
        header_layout.addWidget(refresh_button)
        
        left_layout.addWidget(header_frame)
        
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
            ["Recipient", "Scheduled Time", "Recurrence", "Status"])
        
        header = self.schedule_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.schedule_table.doubleClicked.connect(self._on_schedule_selected)
        
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
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self._clear_form)
        button_layout.addWidget(cancel_button)
        
        self.save_button = QPushButton("Schedule")
        self.save_button.clicked.connect(self._on_save_schedule)
        button_layout.addWidget(self.save_button)
        
        right_layout.addWidget(button_frame)
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
        except:
            self.service_combo.clear()
            self.service_combo.addItem("Default")
    
    def _load_templates(self):
        """Load message templates from the database"""
        try:
            templates = self.app.db.get_templates()
            
            self.template_combo.clear()
            self.template_combo.addItem("-- Select Template --")
            
            self.templates = {}
            for template in templates:
                name = template['name']
                self.template_combo.addItem(name)
                self.templates[name] = template['content']
        except:
            self.template_combo.clear()
            self.template_combo.addItem("-- No Templates Available --")
            self.templates = {}
    
    def _on_template_selected(self, template_name):
        """Handle template selection"""
        if template_name and template_name != "-- Select Template --" and template_name in self.templates:
            content = self.templates[template_name]
            self.message_text.setPlainText(content)
            self._update_char_count()
    
    def _update_char_count(self):
        """Update the character count display"""
        text = self.message_text.toPlainText()
        count = len(text)
        
        parts = count // 160 + (1 if count % 160 > 0 else 0)
        
        if parts > 1:
            self.char_count_label.setText(f"{count} characters ({parts} messages)")
        else:
            self.char_count_label.setText(f"{count}/160 characters")
    
    def _on_recurrence_changed(self, recurrence):
        """Handle recurrence selection change"""
        if recurrence == "Custom":
            self.custom_frame.show()
        else:
            self.custom_frame.hide()
    
    def _on_choose_contact(self):
        """Open contact selection dialog"""
        self.app.tab_widget.setCurrentIndex(1)  # Switch to Contacts tab
        if hasattr(self.app.tabs.get("contacts"), 'set_selection_mode'):
            self.app.tabs["contacts"].set_selection_mode(True)
    
    def load_scheduled_messages(self):
        """Load scheduled messages from the database"""
        try:
            status_filter = self.status_combo.currentText().lower()
            
            if status_filter == "all":
                messages = self.app.scheduler.get_scheduled_messages()
            else:
                messages = self.app.scheduler.get_scheduled_messages(status=status_filter)
            
            self.schedule_table.setRowCount(len(messages))
            
            for row, message in enumerate(messages):
                # Format schedule time
                schedule_time = message['scheduled_time']
                if schedule_time:
                    try:
                        dt = datetime.strptime(schedule_time, '%Y-%m-%d %H:%M:%S')
                        schedule_time = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                # Format recurrence
                recurrence = message.get('recurrence', 'Once') or 'Once'
                
                # Create table items
                recipient_item = QTableWidgetItem(message['recipient'])
                recipient_item.setData(Qt.ItemDataRole.UserRole, message['id'])
                self.schedule_table.setItem(row, 0, recipient_item)
                
                self.schedule_table.setItem(row, 1, QTableWidgetItem(str(schedule_time)))
                self.schedule_table.setItem(row, 2, QTableWidgetItem(recurrence.capitalize()))
                self.schedule_table.setItem(row, 3, QTableWidgetItem(message['status'].capitalize()))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load scheduled messages: {str(e)}")
    
    def _on_schedule_selected(self, index):
        """Handle schedule selection via double-click"""
        QMessageBox.information(self, "Edit Schedule", "Schedule editing will be implemented soon.")
    
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
        
        # Get schedule time
        date = self.date_edit.date().toPython()
        time = self.time_edit.time().toPython()
        schedule_time = datetime.combine(date, time)
        
        if schedule_time <= datetime.now():
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
        service = self.service_combo.currentText()
        if service == "Default":
            service = None
        
        try:
            message_id = self.app.scheduler.schedule_message(
                recipient=recipient,
                message=message,
                schedule_time=schedule_time,
                recurrence=recurrence,
                recurrence_data=recurrence_data,
                service=service
            )
            
            if message_id:
                QMessageBox.information(self, "Success", "Message scheduled successfully")
                self.load_scheduled_messages()
                self._clear_form()
            else:
                QMessageBox.critical(self, "Error", "Failed to schedule message")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to schedule message: {str(e)}")
    
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