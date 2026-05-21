"""Mock Jira service module.

This module provides a simple mock Jira client that returns
pre-defined data from a JSON file. Useful for development and
testing without requiring a real Jira instance.
"""

from .mock_client import MockJiraClient

__all__ = ["MockJiraClient"]
