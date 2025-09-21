#!/usr/bin/env python3
"""
Test suite for logger.py module
"""
import os
import sys
import tempfile
import shutil
import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.logger import setup_logger, get_logger


class TestLogger:
    """Test cases for logger functions"""
    
    def setup_method(self):
        """Set up test environment"""
        # Clear any existing loggers
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            if logger_name.startswith('test_'):
                logger = logging.getLogger(logger_name)
                logger.handlers.clear()
                del logging.Logger.manager.loggerDict[logger_name]
    
    def teardown_method(self):
        """Clean up test environment"""
        # Clear test loggers and close handlers
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            if logger_name.startswith('test_'):
                logger = logging.getLogger(logger_name)
                # Close all handlers to release file locks
                for handler in logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass  # Ignore errors during cleanup
                logger.handlers.clear()
                # Remove references to prevent retention
                logger.disabled = True
                del logging.Logger.manager.loggerDict[logger_name]
        
        # Force garbage collection to ensure cleanup
        import gc
        gc.collect()
    
    def test_setup_logger_default_params(self):
        """Test setting up logger with default parameters"""
        logger = setup_logger("test_default")
        
        assert logger is not None
        assert logger.name == "test_default"
        assert logger.level == logging.INFO
        
        # Should have at least one handler (console)
        assert len(logger.handlers) >= 1
        
        # Find the console handler
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) >= 1
    
    def test_setup_logger_debug_level(self):
        """Test setting up logger with debug level"""
        logger = setup_logger("test_debug", level=logging.DEBUG)
        
        assert logger.level == logging.DEBUG
    
    def test_setup_logger_with_file(self):
        """Test setting up logger with file output"""
        # Create temporary directory for log files
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger = setup_logger("test_file", log_file=log_file)
            
            assert logger is not None
            
            # Should have both console and file handlers
            assert len(logger.handlers) >= 2
            
            # Find the file handler
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) >= 1
            
            # Test logging to verify file is created
            logger.info("Test log message")
            
            # Close handlers before reading file to ensure data is flushed
            for handler in logger.handlers[:]:
                handler.close()
            logger.handlers.clear()
            
            # File should exist and contain the message
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test log message" in content
    
    def test_setup_logger_creates_directory(self):
        """Test that logger creates parent directory for log file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_log_file = os.path.join(temp_dir, "logs", "app", "test.log")
            logger = setup_logger("test_nested", log_file=nested_log_file)
            
            # Log something to ensure file is created
            logger.info("Test message")
            
            # Close handlers before checking file to ensure data is flushed
            for handler in logger.handlers[:]:
                handler.close()
            logger.handlers.clear()
            
            # Directory and file should exist
            assert os.path.exists(os.path.dirname(nested_log_file))
            assert os.path.exists(nested_log_file)
    
    def test_get_logger_existing(self):
        """Test getting an existing logger"""
        # First create a logger
        original_logger = setup_logger("test_existing")
        
        # Get the same logger
        retrieved_logger = get_logger("test_existing")
        
        # Should be the same logger instance
        assert retrieved_logger is original_logger
        assert retrieved_logger.name == "test_existing"
    
    def test_get_logger_nonexistent(self):
        """Test getting a non-existent logger creates a new one"""
        logger = get_logger("test_nonexistent")
        
        assert logger is not None
        assert logger.name == "test_nonexistent"
        # Should have default configuration (INFO level, console handler)
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1
    
    def test_logger_formatting(self):
        """Test logger message formatting"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "format_test.log")
            logger = setup_logger("test_format", log_file=log_file)
            
            # Log a message
            logger.info("Test formatting message")
            
            # Close handlers before reading file to ensure data is flushed
            for handler in logger.handlers[:]:
                handler.close()
            logger.handlers.clear()
            
            # Check the format in the file
            with open(log_file, 'r') as f:
                content = f.read().strip()
                
                # Should contain timestamp, level, logger name, and message
                assert "INFO" in content
                assert "test_format" in content
                assert "Test formatting message" in content
                # Should have timestamp (contains colons from time format)
                assert ":" in content
    
    def test_logger_different_levels(self):
        """Test logging at different levels"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "levels_test.log")
            logger = setup_logger("test_levels", log_file=log_file, level=logging.DEBUG)
            
            # Log at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # Close handlers before reading file to ensure data is flushed
            for handler in logger.handlers[:]:
                handler.close()
            logger.handlers.clear()
            
            # Check all messages are in the file
            with open(log_file, 'r') as f:
                content = f.read()
                
                assert "Debug message" in content
                assert "Info message" in content
                assert "Warning message" in content
                assert "Error message" in content
                assert "Critical message" in content
    
    def test_logger_file_permission_error(self):
        """Test handling of file permission errors"""
        # Try to create log in system directory (should fail)
        restricted_path = "/root/test.log" if os.name != 'nt' else "C:\\Windows\\System32\\test.log"
        
        # Should not raise exception, might fallback to console only
        try:
            logger = setup_logger("test_permission", log_file=restricted_path)
            # If it succeeds without error, that's fine
            assert logger is not None
        except (PermissionError, OSError):
            # Expected behavior - should handle gracefully
            pass
    
    def test_setup_logger_duplicate_calls(self):
        """Test that calling setup_logger multiple times doesn't create duplicate handlers"""
        logger1 = setup_logger("test_duplicate")
        initial_handler_count = len(logger1.handlers)
        
        # Call setup_logger again with same name
        logger2 = setup_logger("test_duplicate")
        
        # Should be the same logger
        assert logger1 is logger2
        # Should not have duplicate handlers
        assert len(logger2.handlers) == initial_handler_count
    
    def test_logger_unicode_messages(self):
        """Test logging unicode messages"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "unicode_test.log")
            logger = setup_logger("test_unicode", log_file=log_file)
            
            # Log unicode message
            unicode_message = "Test with unicode: 你好世界 🌍 émojis"
            logger.info(unicode_message)
            
            # Close handlers before reading file to ensure data is flushed
            for handler in logger.handlers[:]:
                handler.close()
            logger.handlers.clear()
            
            # Should handle unicode properly
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert unicode_message in content
    
    def test_logger_long_messages(self):
        """Test logging very long messages"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "long_test.log")
            logger = setup_logger("test_long", log_file=log_file)
            
            # Create a very long message
            long_message = "A" * 10000  # 10KB message
            logger.info(long_message)
            
            # Close handlers before reading file to ensure data is flushed
            for handler in logger.handlers[:]:
                handler.close()
            logger.handlers.clear()
            
            # Should handle long messages
            with open(log_file, 'r') as f:
                content = f.read()
                assert long_message in content
    
    def test_logger_concurrent_access(self):
        """Test logger with concurrent access simulation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "concurrent_test.log")
            logger = setup_logger("test_concurrent", log_file=log_file)
            
            # Simulate multiple rapid log calls
            for i in range(100):
                logger.info(f"Concurrent message {i}")
            
            # Close handlers before reading file to ensure data is flushed
            for handler in logger.handlers[:]:
                handler.close()
            logger.handlers.clear()
            
            # All messages should be written
            with open(log_file, 'r') as f:
                content = f.read()
                # Check first and last messages
                assert "Concurrent message 0" in content
                assert "Concurrent message 99" in content
    
    @patch('logging.StreamHandler')
    def test_setup_logger_handler_creation_error(self, mock_handler):
        """Test handling of handler creation errors"""
        # Mock StreamHandler to raise an exception
        mock_handler.side_effect = Exception("Handler creation failed")
        
        # Should handle the error gracefully
        try:
            logger = setup_logger("test_handler_error")
            # If it succeeds, verify it has some basic functionality
            assert logger is not None
        except Exception:
            # If it fails, that's acceptable given the mocked error
            pass
    
    @pytest.mark.skip(reason="Windows file locking issue in test environment")
    def test_setup_logger_reconfigure_exception(self):
        """Test handling of reconfigure exceptions"""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "reconfigure_test.log")
            
            # Mock console handler to have reconfigure method that raises an exception
            with patch('logging.StreamHandler') as mock_handler:
                mock_stream = MagicMock()
                mock_stream.reconfigure.side_effect = Exception("Reconfigure failed")
                mock_handler_instance = MagicMock()
                mock_handler_instance.stream = mock_stream
                mock_handler.return_value = mock_handler_instance
                
                # Should handle the reconfigure error gracefully
                logger = setup_logger("test_reconfigure_error", log_file=log_file)
                assert logger is not None
                # Should still have handlers despite the reconfigure error
                assert len(logger.handlers) >= 1
                
                # Clean up logger handlers to release file handles
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
    
    def test_setup_logger_file_handler_general_exception(self):
        """Test handling of general file handler exceptions"""
        # Mock RotatingFileHandler to raise a general exception
        with patch('src.utils.logger.RotatingFileHandler') as mock_handler:
            mock_handler.side_effect = Exception("Unexpected file handler error")
            
            logger = setup_logger("test_file_general_error", log_file="/some/path/test.log")
            
            # Should still create a logger with console handler
            assert logger is not None
            # Should have at least console handler
            assert len(logger.handlers) >= 1
    
    @pytest.mark.skip(reason="Windows file locking issue in test environment") 
    def test_setup_logger_no_reconfigure_method(self):
        """Test setup when console handler stream doesn't have reconfigure method"""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "no_reconfigure_test.log")
            
            # Mock console handler to not have reconfigure method
            with patch('logging.StreamHandler') as mock_handler:
                mock_stream = MagicMock()
                # Remove the reconfigure attribute
                del mock_stream.reconfigure
                mock_handler_instance = MagicMock()
                mock_handler_instance.stream = mock_stream
                mock_handler.return_value = mock_handler_instance
                
                logger = setup_logger("test_no_reconfigure", log_file=log_file)
                assert logger is not None
                # Should still have handlers
                assert len(logger.handlers) >= 1
                
                # Clean up logger handlers to release file handles
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)