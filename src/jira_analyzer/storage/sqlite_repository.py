from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from jira_analyzer.storage.repository import AnalysisResultRepository


class SqliteAnalysisResultRepository(AnalysisResultRepository):
    """SQLite-backed repository for analysis results."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _initialize_database(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_name TEXT,
                    created_at TEXT NOT NULL,
                    results_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save_results(self, results: List[Dict[str, Any]], run_name: str | None = None) -> int:
        serialized = json.dumps(results, ensure_ascii=False)
        created_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO analysis_results (run_name, created_at, results_json) VALUES (?, ?, ?)",
                (run_name, created_at, serialized),
            )
            connection.commit()
            return cursor.lastrowid

    def get_results(self, run_id: int) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "SELECT results_json FROM analysis_results WHERE id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(f"Analysis results with id {run_id} not found.")
            return json.loads(row[0])

    def get_latest_results(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute(
                "SELECT results_json FROM analysis_results ORDER BY created_at DESC, id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row is None:
                return []
            return json.loads(row[0])
