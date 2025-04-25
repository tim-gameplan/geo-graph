#!/usr/bin/env python3
"""
Logging Utilities for EPSG:3857 Pipeline

This module provides a centralized logging configuration for all scripts in the EPSG:3857 pipeline.
It ensures consistent logging format, file locations, and log rotation.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path

# Base directory for all logs
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Default log format
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logger(name, log_file=None, level=logging.INFO, console=True, 
                 format_str=DEFAULT_LOG_FORMAT, max_bytes=10485760, backup_count=5):
    """
    Set up a logger with file and console handlers.
    
    Args:
        name (str): Logger name
        log_file (str, optional): Log file name. If None, uses {name}.log
        level (int, optional): Logging level. Defaults to INFO.
        console (bool, optional): Whether to log to console. Defaults to True.
        format_str (str, optional): Log format string. Defaults to DEFAULT_LOG_FORMAT.
        max_bytes (int, optional): Maximum log file size before rotation. Defaults to 10MB.
        backup_count (int, optional): Number of backup log files to keep. Defaults to 5.
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(format_str)
    
    # Add file handler with rotation
    if log_file is None:
        log_file = f"{name}.log"
    
    # Ensure log_file is just a filename, not a path
    log_file = os.path.basename(log_file)
    log_path = LOGS_DIR / log_file
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_logger(name, **kwargs):
    """
    Get a logger with the specified name and configuration.
    
    This is a convenience function that calls setup_logger with the specified name
    and any additional configuration options.
    
    Args:
        name (str): Logger name
        **kwargs: Additional arguments to pass to setup_logger
        
    Returns:
        logging.Logger: Configured logger
    """
    return setup_logger(name, **kwargs)
