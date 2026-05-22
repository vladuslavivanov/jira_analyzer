"""Jira service module.

This module provides both real Jira client integration
and simple mock service for development and testing.
"""

from typing import Optional, Union
from jira_analyzer.config.models import JiraConfig

# Import both implementations
from .mock_client import MockJiraClient

# Try to import existing real Jira client (may fail if jira package not installed)
try:
    from jira_analyzer.tasktracker.jira import JiraTaskClient
    REAL_JIRA_AVAILABLE = True
except ImportError:
    REAL_JIRA_AVAILABLE = False
    JiraTaskClient = None


def create_jira_client(config: JiraConfig) -> Union[MockJiraClient, JiraTaskClient]:
    """Create appropriate Jira client based on configuration.
    
    This factory function creates either:
    - MockJiraClient: When use_mock=True (development/testing)
    - JiraTaskClient: When use_mock=False (production/real Jira)
    
    Args:
        config: JiraConfig with connection settings
        
    Returns:
        Appropriate Jira client instance
        
    Raises:
        ValueError: If use_mock=False but required fields are missing
        ImportError: If use_mock=False but jira package not installed
        
    Example:
        # Use mock service
        mock_config = JiraConfig(use_mock=True, ...)
        client = create_jira_client(mock_config)
        
        # Use real Jira
        real_config = JiraConfig(
            use_mock=False,
            server_url="https://jira.company.com",
            api_token="your-token"
        )
        client = create_jira_client(real_config)
    """
    if config.use_mock:
        # Use mock service (development/testing)
        return MockJiraClient(
            dataset_path=config.mock_dataset_path,
            error_jql=config.error_on_jql
        )
    else:
        # Use real Jira service (production)
        
        # Validate required fields for real Jira connection
        if not config.server_url:
            raise ValueError(
                "server_url is required when use_mock=False. "
                "Please provide Jira server URL (e.g., 'https://jira.company.com')."
            )
        
        # Check if real Jira client is available
        if not REAL_JIRA_AVAILABLE:
            raise ImportError(
                "Real Jira client requires 'jira' Python package. "
                "Install with 'uv sync' or set use_mock=True for development."
            )
        
        # Create real Jira connection configuration
        jira_connection_config = JiraTaskClient.__annotations__.get("config") or object()
        jira_connection_config.server = config.server_url
        jira_connection_config.username = config.username
        jira_connection_config.token = config.api_token
        jira_connection_config.verify_ssl = config.verify_ssl
        
        # Create and return real Jira client
        return JiraTaskClient(jira_connection_config)


__all__ = ["create_jira_client", "MockJiraClient"]
