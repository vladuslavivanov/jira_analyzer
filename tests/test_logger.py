"""Basic tests for logging system."""

from jira_analyzer.utils.logger import setup_logging, get_logger


def test_logging_works():
    """Test that logging configuration works - no assertion needed."""
    
    # Just verify logging can be called without crashing
    setup_logging(level="INFO", log_llm_prompts=False)
    logger = get_logger("test_module")
    logger.info("Test message")  # Should print to console: [INFO] Test message
    logger.debug("This should not be seen")  # Below INFO level
    logger.error("Error message")  # Should print to console: [ERROR] Error message
    
    # No assertion - just check it runs without crashes
    assert True  # Explicit assertion for pytest
