from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AnalysisResultRepository(ABC):
    """Abstract repository for analysis results."""

    def save_pending(self, task_id: str, task_data: Dict[str, Any], run_id: int | None = None) -> None:
        """Save a pending analysis entry for a task."""
        raise NotImplementedError()

    @abstractmethod
    def update_processing(self, task_id: str, run_id: int | None = None) -> None:
        """Update the state to processing for a task.

        Args:
            task_id: The task ID.
            run_id: The analysis run ID. If None, updates the latest result
                    for this task.
        """
        raise NotImplementedError()

    @abstractmethod
    def save_result(self, task_id: str, result: Dict[str, Any], run_id: int | None = None) -> None:
        """Save the analysis result for a task.

        Args:
            task_id: The task ID.
            result: The analysis result data.
            run_id: The analysis run ID. If None, saves to the latest run
                    for this task.
        """
        raise NotImplementedError()

    @abstractmethod
    def save_failed(self, task_id: str, error: str, run_id: int | None = None) -> None:
        """Save a failed analysis for a task.

        Args:
            task_id: The task ID.
            error: Error description.
            run_id: The analysis run ID. If None, saves to the latest run
                    for this task.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_state(self, task_id: str, run_id: int | None = None) -> Optional[str]:
        """Get the current state of a task analysis.

        Args:
            task_id: The task ID.
            run_id: The analysis run ID. If None, returns the state of the
                    latest result for this task.

        Returns:
            The state string or None if not found.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_result(self, task_id: str, run_id: int | None = None) -> Optional[Dict[str, Any]]:
        """Get the analysis result for a task.

        Args:
            task_id: The task ID.
            run_id: The analysis run ID. If None, returns the latest result
                    for this task.

        Returns:
            The result dict or None if not found.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get all analysis results (across all runs, without deduplication)."""
        raise NotImplementedError()

    @abstractmethod
    def get_latest_results_per_task(self) -> List[Dict[str, Any]]:
        """Get the most recent analysis result for each task.

        When the same task appears in multiple runs, only the result from
        the most recent run (highest run_id) is returned.

        Returns:
            List of result dicts, at most one per task.
        """
        raise NotImplementedError()

    # Analysis run management methods
    def create_analysis_run(
        self,
        run_name: str | None = None,
        system_prompt: str = "",
        general_prompt: str = "",
        include_overall_conclusion: bool = True,
        split_by_criterion: bool = False,
        reasoning_enabled: bool = False,
        reasoning_effort: str = "high",
        config_hash: str | None = None,
        config_json: str | None = None,
    ) -> int:
        """Create a new analysis run and return its ID.
        
        The configuration (prompts, criteria, settings) should be stored
        in a separate config store (e.g. analysis_configs table) and
        deduplicated by config_hash. Each run is an individual session
        referencing a config via config_id.
        
        Legacy implementations may ignore config_hash/config_json and
        store config fields directly on the run.
        """
        raise NotImplementedError()

    def save_criteria(
        self,
        run_id: int,
        criteria: list[dict]
    ) -> None:
        """Save criteria definitions for an analysis run."""
        raise NotImplementedError()

    def get_analysis_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get analysis run configuration by ID."""
        raise NotImplementedError()

    def get_analysis_runs(self) -> List[Dict[str, Any]]:
        """Get all analysis runs."""
        raise NotImplementedError()

    def get_criteria(self, run_id: int) -> List[Dict[str, Any]]:
        """Get criteria definitions for an analysis run."""
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
        """Retrieve the most recent analysis results (legacy)."""
        raise NotImplementedError()
