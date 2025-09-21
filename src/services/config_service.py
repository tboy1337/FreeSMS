"""
Configuration service for SMS application
Manages application settings with JSON persistence
"""
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

class ConfigService:
    """Service for managing application configuration"""
    
    def __init__(self, app_name="sms_sender"):
        """Initialize the configuration service"""
        self.app_name = app_name
        self.config_dir = Path.home() / f".{app_name}"
        self.config_file = self.config_dir / "config.json"
        self.settings = {}
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.settings = json.load(f)
            except json.JSONDecodeError:
                # If the file is corrupted, start with empty settings
                self.settings = {}
                self._save_config()
        else:
            # Initialize with default settings
            self.settings = self._get_default_settings()
            self._save_config()
    
    def _save_config(self):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception:
            return False
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default application settings"""
        return {
            "general": {
                "start_minimized": False,
                "check_updates": True,
                "save_window_position": True
            },
            "notification": {
                "show_notifications": True,
                "play_sound": True
            },
            "scheduler": {
                "check_interval": 1,  # minutes
                "start_on_boot": False
            },
            "message": {
                "default_country": "US",
                "character_warning": 160,
                "save_drafts": True
            },
            "ui": {
                "theme": "system",
                "font_size": "medium",
                "window_width": 900,
                "window_height": 700
            },
            "services": {
                "active_service": None,
                "last_used_service": None
            }
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
        keys = key.split('.')
        value = self.settings
        
        try:
            for k in keys:
                value = value[k]
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
        keys = key.split('.')
        setting = self.settings
        
        # Navigate to the appropriate nested dict
        for k in keys[:-1]:
            if k not in setting:
                setting[k] = {}
            setting = setting[k]
        
        # Set the value
        setting[keys[-1]] = value
        
        # Save the updated configuration
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
        """
        Get all settings
        
        Returns:
            Dictionary containing all settings
        """
        return self.settings.copy()
    
    def save(self) -> bool:
        """
        Save current settings
        
        Returns:
            True if successful, False otherwise
        """
        return self._save_config() 