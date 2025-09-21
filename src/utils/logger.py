"""
Logging utilities for SMS application
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

def setup_logger(name="sms_sender", log_level=logging.INFO, level=None, log_file=None):
    """
    Set up a logger with console and file handlers
    
    Args:
        name: Logger name (default: "sms_sender")
        log_level: Logging level (default: logging.INFO)
        level: Alternative parameter name for log_level (for compatibility)
        log_file: Optional specific log file path (overrides default location)
        
    Returns:
        Configured logger instance
    """
    # Handle parameter compatibility
    if level is not None:
        log_level = level
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return logger
    
    # Create formatters
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # Create console handler with UTF-8 support
        import sys
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(log_level)
        # Ensure UTF-8 encoding for console output
        if hasattr(console_handler.stream, 'reconfigure'):
            try:
                console_handler.stream.reconfigure(encoding='utf-8')
            except Exception:
                pass  # Ignore if reconfigure not available
        logger.addHandler(console_handler)
    except Exception as e:
        # Fallback if console handler fails
        print(f"Warning: Could not create console handler: {e}")
    
    # Create file handler
    try:
        if log_file:
            # Use specified log file
            log_path = Path(log_file)
            # Create parent directory if it doesn't exist
            log_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Use default log file location
            log_dir = Path.home() / '.sms_sender' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            today = datetime.now().strftime('%Y-%m-%d')
            log_path = log_dir / f"sms_sender_{today}.log"
        
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # Fallback if file handler fails (permission issues, etc.)
        print(f"Warning: Could not create file handler for {log_file or 'default location'}: {e}")
    except Exception as e:
        print(f"Warning: Unexpected error creating file handler: {e}")
    
    return logger

def get_logger(name="sms_sender"):
    """
    Get an existing logger or create a new one
    
    Args:
        name: Logger name (default: "sms_sender")
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If the logger doesn't exist or has no handlers, set it up
    if not logger.handlers:
        logger = setup_logger(name)
        
    return logger 