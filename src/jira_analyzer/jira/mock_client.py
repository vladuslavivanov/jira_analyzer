"""Mock Jira client for development and testing.

This fake service returns all data from a JSON dataset,
useful for development and testing without needing real Jira.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json


class MockJiraClient:
    """Fake Jira service returning all data from dataset or errors.

    Student implementation: Simple data loading without complex JQL parsing.

    For MVP: ALWAYS returns all data from dataset (ignores JQL).
    Special case: If JQL matches error_jql, raise error.
    """

    def __init__(
        self,
        dataset_path: str,
        error_jql: str = ""
    ):
        """Initialize with dataset and error trigger.

        Args:
            dataset_path: Path to JSON file with Jira task data
            error_jql: JQL query that triggers error (empty = no errors)
        """
        self._dataset_path = Path(dataset_path)
        self._error_jql = error_jql
        self._dataset: Optional[List[Dict[str, Any]]] = None

    def search_issues(
        self,
        jql: str = "",
        fields: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search Jira issues.

        For MVP: ALWAYS returns all data from dataset (ignores JQL).

        Args:
            jql: JQL query string (ignored in mock, except for error trigger)
            fields: List of fields to return (ignored in mock)
            limit: Max results (ignored in mock)

        Returns:
            List of Jira issue dictionaries

        Raises:
            ValueError: If jql matches error_jql
            FileNotFoundError: If dataset file doesn't exist

        Note:
            This implementation purposely returns all data without filtering
            to keep it simple and student-friendly. No JQL parsing,
            field filtering, or limit handling are implemented.
        """
        # Check for error trigger
        if self._error_jql and jql == self._error_jql:
            raise ValueError(f"Mock error triggered by JQL: {jql}")

        # Lazy load dataset
        if self._dataset is None:
            if not self._dataset_path.exists():
                raise FileNotFoundError(f"Dataset not found: {self._dataset_path}")
            self._dataset = json.loads(self._dataset_path.read_text(encoding="utf-8"))

        # Return all data (ignore jql, fields, limit)
        return self._dataset
