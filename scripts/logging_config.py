#!/usr/bin/env python3
"""
Logging Configuration Module

Provides unified logging configuration for all scripts in the repository.
This module ensures consistent log formatting and output across all scripts.

Usage:
    from logging_config import setup_logging, get_logger
    
    # In your script's main() or at module level:
    setup_logging()
    logger = get_logger(__name__)
    
    # Then use the logger:
    logger.info("Starting process")
    logger.debug("Processing item: %s", item)
    logger.warning("Skipping item due to: %s", reason)
    logger.error("Failed to process item: %s", error)
"""

import logging
import sys
from pathlib import Path
from typing import Optional


DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_loggers: dict[str, logging.Logger] = {}
_configured: bool = False
_log_level: int = logging.INFO
_log_to_file: Optional[Path] = None


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
) -> None:
    """
    Configure the root logger for all scripts.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        format_string: Optional custom format string
        date_format: Optional custom date format
    """
    global _configured, _log_level, _log_to_file
    
    _log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    _log_to_file = Path(log_file) if log_file else None
    
    formatter = logging.Formatter(
        fmt=format_string or DEFAULT_FORMAT,
        datefmt=date_format or DEFAULT_DATE_FORMAT,
    )
    
    handlers: list[logging.Handler] = []
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    if _log_to_file:
        _log_to_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(_log_to_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(_log_level)
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)
    
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name, typically __name__ from the calling script
        
    Returns:
        A configured logger instance
    """
    if not _configured:
        setup_logging()
    
    if name not in _loggers:
        logger = logging.getLogger(name)
        logger.setLevel(_log_level)
        _loggers[name] = logger
    
    return _loggers[name]


def set_log_level(level: str) -> None:
    """
    Change the log level for all loggers.
    
    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    global _log_level
    _log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    
    logging.getLogger().setLevel(_log_level)
    for logger in _loggers.values():
        logger.setLevel(_log_level)


class LogContext:
    """Context manager for temporary log level changes."""
    
    def __init__(self, level: str = "INFO"):
        self.new_level = LOG_LEVELS.get(level.upper(), logging.INFO)
        self.old_level = _log_level
    
    def __enter__(self) -> None:
        set_log_level(logging.getLevelName(self.new_level))
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        set_log_level(logging.getLevelName(self.old_level))


def log_entry_exit(logger: logging.Logger):
    """
    Decorator to log function entry and exit with execution time.
    
    Usage:
        @log_entry_exit(logger)
        def my_function(args):
            pass
    """
    import functools
    import time
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug("Entering: %s", func.__name__)
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.debug("Exiting: %s (%.3fs)", func.__name__, elapsed)
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error("Failed: %s (%.3fs) - %s: %s", 
                           func.__name__, elapsed, type(e).__name__, e)
                raise
        return wrapper
    return decorator


def log_section(logger: logging.Logger, title: str, level: int = logging.INFO) -> None:
    """
    Log a section header for better readability in logs.
    
    Args:
        logger: The logger instance
        title: Section title
        level: Log level for the section header
    """
    separator = "=" * 60
    logger.log(level, separator)
    logger.log(level, title.center(58))
    logger.log(level, separator)


if __name__ == "__main__":
    print("logging_config.py is a module, not a script.")
    print("Import it to use in other scripts:")
    print("    from scripts.logging_config import setup_logging, get_logger")
