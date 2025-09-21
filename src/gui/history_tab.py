"""
History Tab - UI for viewing message history
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QComboBox, QPushButton, QGroupBox,
    QFormLayout, QTextEdit, QHeaderView, QAbstractItemView,
    QMessageBox
)
from PySide6.QtCore import Qt
from datetime import datetime

class HistoryTab(QWidget):
    """Message history view tab"""
    
    def __init__(self, app):
        """Initialize the history tab"""
        super().__init__()
        self.app = app
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        self._create_components()
        self.load_history()
    
    def _create_components(self):
        """Create tab components"""
        layout = self.layout()
        
        # Top control frame
        top_frame = QWidget()
        top_layout = QHBoxLayout(top_frame)
        
        # Filter options
        filter_group = QGroupBox("Filter")
        filter_layout = QHBoxLayout(filter_group)
        
        filter_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Sent", "Failed", "Delivered"])
        filter_layout.addWidget(self.status_combo)
        
        filter_layout.addWidget(QLabel("Service:"))
        self.service_combo = QComboBox()
        self.service_combo.addItem("All")
        filter_layout.addWidget(self.service_combo)
        
        self.filter_button = QPushButton("Apply Filter")
        self.filter_button.clicked.connect(self.load_history)
        filter_layout.addWidget(self.filter_button)
        
        top_layout.addWidget(filter_group)
        
        # Message count
        self.count_label = QLabel("0 messages")
        top_layout.addStretch()
        top_layout.addWidget(self.count_label)
        
        layout.addWidget(top_frame)
        
        # Message list
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Recipient", "Message", "Status", "Service", "Date/Time"])
        
        # Configure table
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.doubleClicked.connect(self._on_message_selected)
        
        layout.addWidget(self.history_table)
        
        # Message details frame
        details_group = QGroupBox("Message Details")
        details_layout = QFormLayout()
        
        self.detail_recipient = QLabel("")
        details_layout.addRow("Recipient:", self.detail_recipient)
        
        self.detail_status = QLabel("")
        details_layout.addRow("Status:", self.detail_status)
        
        self.detail_date = QLabel("")
        details_layout.addRow("Date:", self.detail_date)
        
        self.detail_service = QLabel("")
        details_layout.addRow("Service:", self.detail_service)
        
        self.detail_message_id = QLabel("")
        details_layout.addRow("Message ID:", self.detail_message_id)
        
        self.detail_message = QTextEdit()
        self.detail_message.setMaximumHeight(100)
        self.detail_message.setReadOnly(True)
        details_layout.addRow("Message:", self.detail_message)
        
        # Action buttons
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.addStretch()
        
        self.check_status_button = QPushButton("Check Status")
        self.check_status_button.setEnabled(False)
        self.check_status_button.clicked.connect(self._on_check_status)
        button_layout.addWidget(self.check_status_button)
        
        self.resend_button = QPushButton("Resend")
        self.resend_button.setEnabled(False)
        self.resend_button.clicked.connect(self._on_resend)
        button_layout.addWidget(self.resend_button)
        
        details_layout.addRow(button_frame)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        self._clear_details()
    
    def load_history(self):
        """Load message history from the database"""
        try:
            status_filter = self.status_combo.currentText()
            service_filter = self.service_combo.currentText()
            
            messages = self.app.db.get_message_history(limit=100)
            
            # Filter messages
            filtered_messages = []
            services = set(["All"])
            
            for message in messages:
                services.add(message['service'])
                
                if status_filter != "All" and status_filter.lower() != message['status'].lower():
                    continue
                if service_filter != "All" and service_filter != message['service']:
                    continue
                    
                filtered_messages.append(message)
            
            # Update service filter dropdown
            current_service = self.service_combo.currentText()
            self.service_combo.clear()
            for service in sorted(services):
                self.service_combo.addItem(service)
            
            # Restore selection if possible
            index = self.service_combo.findText(current_service)
            if index >= 0:
                self.service_combo.setCurrentIndex(index)
            
            # Update count
            self.count_label.setText(f"{len(filtered_messages)} messages")
            
            # Populate table
            self.history_table.setRowCount(len(filtered_messages))
            
            for row, message in enumerate(filtered_messages):
                # Format date/time
                sent_at = message['sent_at']
                if sent_at:
                    try:
                        dt = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S')
                        sent_at = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                # Truncate message for display
                msg_text = message['message']
                if len(msg_text) > 50:
                    msg_text = msg_text[:47] + "..."
                
                # Create table items
                recipient_item = QTableWidgetItem(message['recipient'])
                recipient_item.setData(Qt.ItemDataRole.UserRole, message['id'])
                self.history_table.setItem(row, 0, recipient_item)
                
                self.history_table.setItem(row, 1, QTableWidgetItem(msg_text))
                self.history_table.setItem(row, 2, QTableWidgetItem(message['status']))
                self.history_table.setItem(row, 3, QTableWidgetItem(message['service']))
                self.history_table.setItem(row, 4, QTableWidgetItem(str(sent_at)))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load history: {str(e)}")
    
    def _on_message_selected(self, index):
        """Handle message selection via double-click"""
        row = index.row()
        recipient_item = self.history_table.item(row, 0)
        if not recipient_item:
            return
            
        message_id = recipient_item.data(Qt.ItemDataRole.UserRole)
        
        try:
            self.app.db.cursor.execute('SELECT * FROM message_history WHERE id = ?', (message_id,))
            message = self.app.db.cursor.fetchone()
            
            if message:
                self.current_message = message
                
                self.detail_recipient.setText(message['recipient'])
                self.detail_status.setText(message['status'])
                self.detail_service.setText(message['service'])
                
                # Format date
                sent_at = message['sent_at']
                if sent_at:
                    try:
                        dt = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S')
                        sent_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                self.detail_date.setText(str(sent_at))
                
                msg_id = message['message_id'] or "N/A"
                self.detail_message_id.setText(str(msg_id))
                
                self.detail_message.setPlainText(message['message'])
                
                # Enable/disable buttons
                if message['status'] == 'sent' and message['message_id']:
                    self.check_status_button.setEnabled(True)
                else:
                    self.check_status_button.setEnabled(False)
                    
                self.resend_button.setEnabled(True)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load message details: {str(e)}")
    
    def _on_check_status(self):
        """Check delivery status of selected message"""
        QMessageBox.information(self, "Check Status", "Status checking will be implemented soon.")
    
    def _on_resend(self):
        """Resend the selected message"""
        if hasattr(self, 'current_message') and self.current_message:
            reply = QMessageBox.question(self, "Confirm Resend", 
                                       f"Resend this message to {self.current_message['recipient']}?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                recipient = self.current_message['recipient']
                message_text = self.current_message['message']
                service = self.current_message['service']
                
                self.app.send_message(recipient, message_text, service)
        else:
            QMessageBox.information(self, "Information", "Please select a message first")
    
    def _clear_details(self):
        """Clear the details display"""
        self.detail_recipient.clear()
        self.detail_status.clear()
        self.detail_service.clear()
        self.detail_date.clear()
        self.detail_message_id.clear()
        self.detail_message.clear()
        
        self.check_status_button.setEnabled(False)
        self.resend_button.setEnabled(False)
        
        if hasattr(self, 'current_message'):
            delattr(self, 'current_message')