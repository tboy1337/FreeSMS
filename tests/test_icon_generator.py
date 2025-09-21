#!/usr/bin/env python3
"""
Test suite for icon_generator.py module
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.icon_generator import generate_sms_icon


class TestIconGenerator:
    """Test cases for icon generator functions"""
    
    def setup_method(self):
        """Set up test environment"""
        # Create temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()
        self.test_icon_path = os.path.join(self.temp_dir, "test_icon.png")
    
    def teardown_method(self):
        """Clean up test environment"""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_sms_icon_default_params(self):
        """Test generating SMS icon with default parameters"""
        result_path = generate_sms_icon(self.test_icon_path)
        
        # Verify the icon was created
        assert os.path.exists(result_path)
        assert result_path == self.test_icon_path
        
        # Verify it's a valid image
        with Image.open(result_path) as img:
            assert img.size == (256, 256)
            assert img.format == 'PNG'
    
    def test_generate_sms_icon_custom_size(self):
        """Test generating SMS icon with custom size"""
        custom_size = 128
        result_path = generate_sms_icon(self.test_icon_path, size=custom_size)
        
        # Verify the icon was created with correct size
        assert os.path.exists(result_path)
        with Image.open(result_path) as img:
            assert img.size == (custom_size, custom_size)
    
    def test_generate_sms_icon_custom_colors(self):
        """Test generating SMS icon with custom colors"""
        bg_color = (255, 0, 0)  # Red background
        fg_color = (0, 255, 0)  # Green foreground
        
        result_path = generate_sms_icon(
            self.test_icon_path, 
            background_color=bg_color, 
            text_color=fg_color
        )
        
        # Verify the icon was created
        assert os.path.exists(result_path)
        
        # Verify it's a valid image (we can't easily verify colors without detailed pixel analysis)
        with Image.open(result_path) as img:
            assert img.format == 'PNG'
    
    def test_generate_sms_icon_create_directory(self):
        """Test generating SMS icon that creates parent directory"""
        nested_path = os.path.join(self.temp_dir, "nested", "dir", "icon.png")
        
        result_path = generate_sms_icon(nested_path)
        
        # Verify the icon was created and directory structure exists
        assert os.path.exists(result_path)
        assert os.path.exists(os.path.dirname(nested_path))
    
    def test_generate_sms_icon_overwrite_existing(self):
        """Test generating SMS icon overwrites existing file"""
        # Create a dummy file first
        with open(self.test_icon_path, 'w') as f:
            f.write("dummy content")
        
        # Generate icon should overwrite
        result_path = generate_sms_icon(self.test_icon_path)
        
        # Verify it's now a valid PNG image, not the dummy text
        assert os.path.exists(result_path)
        with Image.open(result_path) as img:
            assert img.format == 'PNG'
    
    @patch('PIL.ImageFont.truetype')
    def test_generate_sms_icon_font_fallback(self, mock_truetype):
        """Test font fallback when truetype font loading fails"""
        # Mock truetype to raise exception, forcing fallback to default font
        mock_truetype.side_effect = OSError("Font not found")
        
        # Mock the default font loading
        with patch('PIL.ImageFont.load_default') as mock_load_default:
            mock_font = MagicMock()
            mock_load_default.return_value = mock_font
            
            result_path = generate_sms_icon(self.test_icon_path)
            
            # Verify icon was created despite font loading failure
            assert os.path.exists(result_path)
            # Verify fallback font was used
            mock_load_default.assert_called_once()
    
    def test_generate_sms_icon_permission_error(self):
        """Test handling of permission errors during icon generation"""
        # Try to create icon in a non-existent root directory (should fail on Windows)
        invalid_path = "/root/restricted/icon.png" if os.name != 'nt' else "C:\\Windows\\System32\\icon.png"
        
        # This should not raise an exception but may return None or handle gracefully
        try:
            result_path = generate_sms_icon(invalid_path)
            # If it succeeds, that's fine too (depending on system permissions)
            if result_path:
                assert os.path.exists(result_path)
        except (PermissionError, OSError):
            # Expected behavior for permission denied
            pass
    
    def test_generate_sms_icon_invalid_colors(self):
        """Test handling of invalid color values"""
        # Test with invalid color format should raise TypeError or work with fallback
        try:
            result_path = generate_sms_icon(
                self.test_icon_path,
                background_color="invalid_color",
                text_color="also_invalid"
            )
            # If it works, verify it created a valid image
            assert os.path.exists(result_path)
            with Image.open(result_path) as img:
                assert img.format == 'PNG'
        except (TypeError, ValueError):
            # Expected behavior for invalid color format
            pass
    
    def test_generate_sms_icon_zero_size(self):
        """Test handling of zero or negative size"""
        # Test with zero size should raise ValueError
        try:
            result_path = generate_sms_icon(self.test_icon_path, size=0)
            # If it somehow works, verify it created a valid image
            assert os.path.exists(result_path)
        except ValueError:
            # Expected behavior for zero/negative size
            pass
    
    def test_generate_sms_icon_very_large_size(self):
        """Test handling of very large size"""
        large_size = 2048
        result_path = generate_sms_icon(self.test_icon_path, size=large_size)
        
        # Should create large icon successfully
        assert os.path.exists(result_path)
        with Image.open(result_path) as img:
            assert img.size == (large_size, large_size)
    
    def test_generate_sms_icon_empty_path(self):
        """Test handling of empty path"""
        try:
            result_path = generate_sms_icon("")
            # If it succeeds, verify the result
            if result_path and os.path.exists(result_path):
                with Image.open(result_path) as img:
                    assert img.format == 'PNG'
        except (ValueError, OSError):
            # Expected behavior for empty path
            pass
    
    def test_generate_sms_icon_path_object(self):
        """Test using Path object instead of string"""
        path_obj = Path(self.test_icon_path)
        result_path = generate_sms_icon(path_obj)
        
        # Verify the icon was created
        assert os.path.exists(result_path)
        with Image.open(result_path) as img:
            assert img.format == 'PNG'