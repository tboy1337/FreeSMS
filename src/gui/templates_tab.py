"""
Templates Tab - UI for managing message templates
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.ui_helpers import (
    add_cancel_button_row,
    create_horizontal_splitter,
    create_split_left_panel,
    create_tab_layout,
    update_sms_char_count,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TemplatesTab(QWidget):
    """Message templates management tab"""

    def __init__(self, app):
        """Initialize the templates tab"""
        super().__init__()
        self.editing_template_id: int | None = None
        self.templates: dict[str, dict[str, object]] = {}
        create_tab_layout(self, app)
        self._create_components()
        self.load_templates()

    def _create_components(self):
        """Create tab components"""
        # Split into left and right panels
        splitter = create_horizontal_splitter(self)

        # Left panel for template list
        left_widget, left_layout, header_layout = create_split_left_panel("Templates")

        new_button = QPushButton("New Template")
        new_button.clicked.connect(self._on_new_template)
        header_layout.addStretch()
        header_layout.addWidget(new_button)

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
        button_layout = add_cancel_button_row(right_layout, self._clear_editor)

        save_button = QPushButton("Save Template")
        save_button.clicked.connect(self._on_save_template)
        button_layout.addWidget(save_button)
        right_layout.addStretch()

        splitter.addWidget(right_widget)

        # Set initial state
        self._clear_editor()

    def _update_char_count(self):
        """Update the character count display"""
        update_sms_char_count(self.char_count_label, self.content_text.toPlainText())

    def load_templates(self):
        """Load templates from the database"""
        try:
            self.template_list.clear()

            templates = self.app.db.get_message_templates()

            self.templates = {}

            for template in templates:
                template_id = template["id"]
                name = template["name"]

                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, template_id)
                self.template_list.addItem(item)

                self.templates[name] = {
                    "id": template_id,
                    "content": template["content"],
                }

        except (OSError, RuntimeError, KeyError, TypeError, ValueError) as exc:
            logger.exception("Failed to load templates: %s", exc)
            QMessageBox.critical(self, "Error", f"Failed to load templates: {exc!s}")

    def _on_template_selected(self):
        """Handle template selection"""
        if not (current_item := self.template_list.currentItem()):
            return

        name = current_item.text()
        self._load_template_for_editing(name)

    def _load_template_for_editing(self, name):
        """Load a template into the editor"""
        if name not in self.templates:
            return

        template = self.templates[name]

        self.name_entry.setText(name)
        self.content_text.setPlainText(template["content"])
        self._update_char_count()

        self.editor_header.setText(f"Edit Template: {name}")

        self.editing_template_id = template["id"]

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
        editing_id = self.editing_template_id
        if editing_id is None and name in self.templates:
            QMessageBox.critical(
                self, "Error", f"A template with the name '{name}' already exists"
            )
            self.name_entry.setFocus()
            return

        try:
            success = self.app.db.save_message_template(
                name, content, template_id=editing_id
            )

            if success:
                QMessageBox.information(
                    self, "Success", f"Template '{name}' saved successfully"
                )
                self.load_templates()
                self._clear_editor()
            else:
                QMessageBox.critical(self, "Error", f"Failed to save template '{name}'")

        except (OSError, RuntimeError, KeyError, TypeError, ValueError) as exc:
            logger.exception("Failed to save template: %s", exc)
            QMessageBox.critical(self, "Error", f"Failed to save template: {exc!s}")

    def _clear_editor(self):
        """Clear the template editor"""
        self.name_entry.clear()
        self.content_text.clear()
        self._update_char_count()

        self.editor_header.setText("New Template")

        self.editing_template_id = None

        self.name_entry.setFocus()
