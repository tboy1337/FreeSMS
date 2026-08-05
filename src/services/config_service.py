"""
Configuration service for SMS application
Manages application settings with JSON persistence
"""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.paths import get_app_dir, get_config_path


class ConfigService:
    """Service for managing application configuration"""

    def __init__(self, app_name: str = "freesms", config_path: Optional[str] = None):
        """Initialize the configuration service"""
        self.app_name = app_name
        if config_path:
            self.config_file = Path(config_path)
            self.config_dir = self.config_file.parent
        else:
            self.config_dir = get_app_dir()
            self.config_file = get_config_path()

        self.settings: Dict[str, Any] = {}

        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as file_handle:
                    self.settings = json.load(file_handle)
            except json.JSONDecodeError:
                self.settings = self._get_default_settings()
                self._save_config()
        else:
            self.settings = self._get_default_settings()
            self._save_config()

    def _save_config(self) -> bool:
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as file_handle:
                json.dump(self.settings, file_handle, indent=2)
            return True
        except OSError:
            return False

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default application settings"""
        return {
            "general": {
                "start_minimized": False,
                "check_updates": True,
                "save_window_position": True,
            },
            "notification": {
                "show_notifications": True,
                "play_sound": True,
            },
            "scheduler": {
                "check_interval": 1,
                "start_on_boot": False,
            },
            "message": {
                "default_country": "US",
                "character_warning": 160,
                "save_drafts": True,
            },
            "ui": {
                "theme": "system",
                "font_size": "medium",
                "window_width": 900,
                "window_height": 700,
            },
            "services": {
                "active_service": None,
                "last_used_service": None,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value

        Args:
            key: Setting key path (e.g., "general.start_minimized")
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        keys = key.split(".")
        value: Any = self.settings

        try:
            for part in keys:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> bool:
        """
        Set a configuration value

        Args:
            key: Setting key path (e.g., "general.start_minimized")
            value: Setting value

        Returns:
            True if successful, False otherwise
        """
        keys = key.split(".")
        setting: Dict[str, Any] = self.settings

        for part in keys[:-1]:
            if part not in setting:
                setting[part] = {}
            setting = setting[part]

        setting[keys[-1]] = value
        return self._save_config()

    def reset(self, section: Optional[str] = None) -> bool:
        """
        Reset settings to default

        Args:
            section: Section to reset (None for all settings)

        Returns:
            True if successful, False otherwise
        """
        defaults = self._get_default_settings()

        if section is None:
            self.settings = defaults
        elif section in defaults:
            self.settings[section] = defaults[section]
        else:
            return False

        return self._save_config()

    def get_all(self) -> Dict[str, Any]:
        """Get all settings."""
        return deepcopy(self.settings)

    def save(self) -> bool:
        """Save current settings."""
        return self._save_config()
