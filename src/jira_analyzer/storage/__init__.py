"""Storage abstractions for Jira Analyzer."""
from .repository import AnalysisResultRepository
from .sqlite_repository import SqliteAnalysisResultRepository

__all__ = [
    "AnalysisResultRepository",
    "SqliteAnalysisResultRepository",
]
