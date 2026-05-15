from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


from typing import Optional

class AnalysisResultRepository(ABC):
    """Abstract repository for analysis results."""

    @abstractmethod
    def save_pending(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save a pending analysis entry for a task."""
        raise NotImplementedError()

    @abstractmethod
    def update_processing(self, task_id: str) -> None:
        """Update the state to processing for a task."""
        raise NotImplementedError()

    @abstractmethod
    def save_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Save the analysis result for a task."""
        raise NotImplementedError()

    @abstractmethod
    def save_failed(self, task_id: str, error: str) -> None:
        """Save a failed analysis for a task."""
        raise NotImplementedError()

    @abstractmethod
    def get_state(self, task_id: str) -> Optional[str]:
        """Get the current state of a task analysis."""
        raise NotImplementedError()

    @abstractmethod
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the analysis result for a task."""
        raise NotImplementedError()

    @abstractmethod
    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get all analysis results."""
        raise NotImplementedError()

    # Legacy methods for batch operations
    @abstractmethod
    def save_results(self, results: List[Dict[str, Any]], run_name: str | None = None) -> int:
        """Save a list of analysis results and return a run identifier."""
        raise NotImplementedError()

    @abstractmethod
    def get_results(self, run_id: int) -> List[Dict[str, Any]]:
        """Retrieve saved analysis results by run identifier."""
        raise NotImplementedError()

    @abstractmethod
    def get_latest_results(self) -> List[Dict[str, Any]]:
        """Retrieve the most recent analysis results."""
        raise NotImplementedError()
