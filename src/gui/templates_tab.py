"""
Templates Tab - UI for managing message templates
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QTextEdit, QGroupBox, QFormLayout,
    QSplitter, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt

class TemplatesTab(QWidget):
    """Message templates management tab"""
    
    def __init__(self, app):
        """Initialize the templates tab"""
        super().__init__()
        self.app = app
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        self._create_components()
        self.load_templates()
    
    def _create_components(self):
        """Create tab components"""
        # Split into left and right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout().addWidget(splitter)
        
        # Left panel for template list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Header
        header_frame = QWidget()
        header_layout = QHBoxLayout(header_frame)
        
        title_label = QLabel("Templates")
        title_label.setProperty("class", "title")
        header_layout.addWidget(title_label)
        
        new_button = QPushButton("New Template")
        new_button.clicked.connect(self._on_new_template)
        header_layout.addStretch()
        header_layout.addWidget(new_button)
        
        left_layout.addWidget(header_frame)
        
        # Template list
        self.template_list = QListWidget()
        self.template_list.itemSelectionChanged.connect(self._on_template_selected)
        left_layout.addWidget(self.template_list)
        
        splitter.addWidget(left_widget)
        
        # Right panel for template editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.editor_header = QLabel("New Template")
        self.editor_header.setProperty("class", "title")
        right_layout.addWidget(self.editor_header)
        
        # Form group
        form_group = QGroupBox()
        form_layout = QFormLayout(form_group)
        
        # Template name
        self.name_entry = QLineEdit()
        form_layout.addRow("Template Name:", self.name_entry)
        
        # Template content
        content_group = QGroupBox("Template Content")
        content_layout = QVBoxLayout(content_group)
        
        self.content_text = QTextEdit()
        self.content_text.textChanged.connect(self._update_char_count)
        content_layout.addWidget(self.content_text)
        
        # Character counter
        self.char_count_label = QLabel("0/160 characters")
        self.char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        content_layout.addWidget(self.char_count_label)
        
        form_layout.addRow(content_group)
        
        right_layout.addWidget(form_group)
        
        # Buttons
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self._clear_editor)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("Save Template")
        save_button.clicked.connect(self._on_save_template)
        button_layout.addWidget(save_button)
        
        right_layout.addWidget(button_frame)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        
        # Set initial state
        self._clear_editor()
    
    def _update_char_count(self):
        """Update the character count display"""
        text = self.content_text.toPlainText()
        count = len(text)
        
        parts = count // 160 + (1 if count % 160 > 0 else 0)
        
        if parts > 1:
            self.char_count_label.setText(f"{count} characters ({parts} messages)")
        else:
            self.char_count_label.setText(f"{count}/160 characters")
    
    def load_templates(self):
        """Load templates from the database"""
        try:
            self.template_list.clear()
            
            templates = self.app.db.get_templates()
            
            self.templates = {}
            
            for template in templates:
                template_id = template['id']
                name = template['name']
                
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, template_id)
                self.template_list.addItem(item)
                
                self.templates[name] = {
                    'id': template_id,
                    'content': template['content']
                }
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load templates: {str(e)}")
    
    def _on_template_selected(self):
        """Handle template selection"""
        current_item = self.template_list.currentItem()
        if not current_item:
            return
            
        name = current_item.text()
        self._load_template_for_editing(name)
    
    def _load_template_for_editing(self, name):
        """Load a template into the editor"""
        if name not in self.templates:
            return
            
        template = self.templates[name]
        
        self.name_entry.setText(name)
        self.content_text.setPlainText(template['content'])
        self._update_char_count()
        
        self.editor_header.setText(f"Edit Template: {name}")
        
        self.editing_template_id = template['id']
    
    def _on_new_template(self):
        """Create a new template"""
        self._clear_editor()
    
    def _on_save_template(self):
        """Save the current template"""
        name = self.name_entry.text().strip()
        content = self.content_text.toPlainText().strip()
        
        if not name:
            QMessageBox.critical(self, "Error", "Template name is required")
            self.name_entry.setFocus()
            return
            
        if not content:
            QMessageBox.critical(self, "Error", "Template content is required")
            self.content_text.setFocus()
            return
        
        # Check for duplicate name when creating new template
        if not hasattr(self, 'editing_template_id'):
            if name in self.templates:
                QMessageBox.critical(self, "Error", f"A template with the name '{name}' already exists")
                self.name_entry.setFocus()
                return
        
        try:
            success = self.app.db.save_template(name, content)
            
            if success:
                QMessageBox.information(self, "Success", f"Template '{name}' saved successfully")
                self.load_templates()
                self._clear_editor()
            else:
                QMessageBox.critical(self, "Error", f"Failed to save template '{name}'")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template: {str(e)}")
    
    def _clear_editor(self):
        """Clear the template editor"""
        self.name_entry.clear()
        self.content_text.clear()
        self._update_char_count()
        
        self.editor_header.setText("New Template")
        
        if hasattr(self, 'editing_template_id'):
            delattr(self, 'editing_template_id')
            
        self.name_entry.setFocus()