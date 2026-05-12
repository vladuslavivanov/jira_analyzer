from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AnalysisResultRepository(ABC):
    """Abstract repository for analysis results."""

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
        """Retrieve the most recent saved analysis results."""
        raise NotImplementedError()
