from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from jira_analyzer.tasktracker.jira import (
    JiraConnectionConfig,
    JiraTaskClient,
    jira_issue_to_analysis_input,
)
from jira_analyzer.tasktracker.jira.jira_parser import load_issues


class TasksRepository(ABC):
    """Abstract interface for task acquisition from different sources."""

    @abstractmethod
    def get_task(self, task_id: str) -> Dict[str, Any]:
        raise NotImplementedError()

    @abstractmethod
    def search_tasks(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError()

    @abstractmethod
    def load_dataset(self, path: str) -> List[Dict[str, Any]]:
        raise NotImplementedError()


class JiraTasksRepository(TasksRepository):
    def __init__(self, config: JiraConnectionConfig):
        self.client = JiraTaskClient(config)

    def get_task(self, task_id: str) -> Dict[str, Any]:
        try:
            issue = self.client.get_issue(task_id)
            return jira_issue_to_analysis_input(issue)
        except Exception as e:
            raise ValueError(f"Failed to fetch Jira issue {task_id}: {str(e)}")

    def search_tasks(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        try:
            issues = self.client.search_issues(jql, max_results=max_results)
            return [jira_issue_to_analysis_input(issue) for issue in issues]
        except Exception as e:
            raise ValueError(f"Failed to search Jira issues with JQL '{jql}': {str(e)}")

    def load_dataset(self, path: str) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "JiraTasksRepository does not support loading local datasets."
        )


class JsonFileTasksRepository(TasksRepository):
    def get_task(self, task_id: str) -> Dict[str, Any]:
        raise NotImplementedError(
            "JsonFileTasksRepository does not support fetching individual Jira tasks."
        )

    def search_tasks(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "JsonFileTasksRepository does not support Jira JQL search."
        )

    def load_dataset(self, path: str) -> List[Dict[str, Any]]:
        try:
            file_path = Path(path)
            return load_issues(str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to load dataset from {path}: {str(e)}")
