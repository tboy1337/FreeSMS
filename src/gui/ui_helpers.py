"""
Shared GUI helper utilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.models.database import Database


def create_tab_layout(widget: QWidget, app: object) -> QVBoxLayout:
    """Create the standard vertical layout used by application tabs."""
    widget.app = app
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    return layout


def create_horizontal_splitter(parent: QWidget) -> QSplitter:
    """Create a horizontal splitter attached to the parent widget layout."""
    splitter = QSplitter(Qt.Orientation.Horizontal)
    parent.layout().addWidget(splitter)
    return splitter


def create_split_left_panel(title: str) -> tuple[QWidget, QVBoxLayout, QHBoxLayout]:
    """Create a left split panel with a titled header row."""
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    header_frame = QWidget()
    header_layout = QHBoxLayout(header_frame)
    title_label = QLabel(title)
    title_label.setProperty("class", "title")
    header_layout.addWidget(title_label)
    left_layout.addWidget(header_frame)
    return left_widget, left_layout, header_layout


def add_cancel_button_row(parent_layout: QVBoxLayout, on_cancel: object) -> QHBoxLayout:
    """Add a right-aligned row containing a Cancel button."""
    button_frame = QWidget()
    button_layout = QHBoxLayout(button_frame)
    button_layout.addStretch()
    cancel_button = QPushButton("Cancel")
    cancel_button.clicked.connect(on_cancel)
    button_layout.addWidget(cancel_button)
    parent_layout.addWidget(button_frame)
    return button_layout


def update_sms_char_count(label: QLabel, text: str) -> None:
    """Update an SMS character count label for the given message text."""
    count = len(text)
    if (parts := count // 160 + (1 if count % 160 > 0 else 0)) > 1:
        label.setText(f"{count} characters ({parts} messages)")
    else:
        label.setText(f"{count}/160 characters")


def load_message_templates(
    template_combo: QComboBox,
    db: Database,
    templates: dict[str, str],
    *,
    empty_label: str = "-- Select Template --",
    error_label: str = "-- No Templates Available --",
) -> None:
    """Populate a template combo box from the database."""
    try:
        template_rows = db.get_message_templates()

        template_combo.clear()
        template_combo.addItem(empty_label)

        templates.clear()
        for template in template_rows:
            name = template["name"]
            template_combo.addItem(name)
            templates[name] = template["content"]
    except (OSError, RuntimeError, KeyError, TypeError, ValueError):
        template_combo.clear()
        template_combo.addItem(error_label)
        templates.clear()


def apply_selected_template(
    template_name: str,
    templates: dict[str, str],
    message_text: Any,
    char_count_label: QLabel,
) -> None:
    """Apply a selected template name to a message text widget."""
    if (
        template_name
        and template_name != "-- Select Template --"
        and template_name in templates
    ):
        message_text.setPlainText(templates[template_name])
        update_sms_char_count(char_count_label, message_text.toPlainText())


class MessageTemplateMixin:
    """Shared template selection and character count helpers for tabs."""

    templates: dict[str, str]
    template_combo: QComboBox
    message_text: Any
    char_count_label: QLabel

    def _load_templates(self) -> None:
        """Load message templates from the database."""
        load_message_templates(self.template_combo, self.app.db, self.templates)

    def _on_template_selected(self, template_name: str) -> None:
        """Handle template selection."""
        apply_selected_template(
            template_name,
            self.templates,
            self.message_text,
            self.char_count_label,
        )

    def _update_char_count(self) -> None:
        """Update the character count display."""
        update_sms_char_count(self.char_count_label, self.message_text.toPlainText())
