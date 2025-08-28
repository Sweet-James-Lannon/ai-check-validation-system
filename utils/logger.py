import logging
import sys
from datetime import datetime

def setup_logging(app_name="SweetJames", level=logging.INFO):
    """Set up clean, structured logging"""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger

def get_logger(name):
    """Get a logger for a specific component"""
    return logging.getLogger(name)

# Pre-configured loggers for different components
def get_auth_logger():
    return logging.getLogger("AUTH")

def get_db_logger():
    return logging.getLogger("DATABASE")

def get_api_logger():
    return logging.getLogger("API")

def get_app_logger():
    return logging.getLogger("APP")