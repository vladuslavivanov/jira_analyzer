"""Logging system for Jira Analyzer.

Configures standard Python logging module for console output only.
Uses simple format: [LEVEL] message for clarity and student-friendliness.
"""

import logging
from typing import Optional


def setup_logging(level: str = "INFO", log_llm_prompts: bool = False):
    """Configure logging to console with given level.

    Args:
        level: Log level - "DEBUG", "INFO", "WARNING", "ERROR"
        log_llm_prompts: If True, log LLM request/response

    Configuration:
        - Console handler for output
        - Simple format: [LEVEL] message
        - No timestamps, module names, or complex formatting
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(numeric_level)

    # Simple format exactly as specified
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(handler)

    # Store flag for LLM logging (optional optimization)
    if log_llm_prompts:
        setattr(root_logger, "_log_llm_prompts", True)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module.

    Args:
        name: Module name (use __name__)

    Returns:
        Logger instance for the specified module

    Example:
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    return logging.getLogger(name)
