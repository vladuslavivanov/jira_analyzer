"""Jira service module.

This module provides both real Jira client integration
and simple mock service for development and testing.
"""

from typing import Union
from .client_factory import create_jira_client, MockJiraClient

# Type alias for Jira client (either mock or real)
JiraClient = Union[MockJiraClient, object]  # object for JiraTaskClient

__all__ = [
    "create_jira_client",
    "MockJiraClient", 
    "JiraClient",
]
