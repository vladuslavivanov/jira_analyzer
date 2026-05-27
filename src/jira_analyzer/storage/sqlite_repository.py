from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from jira_analyzer.storage.repository import AnalysisResultRepository

UTC_PLUS_3 = timezone(timedelta(hours=3))


class SqliteAnalysisResultRepository(AnalysisResultRepository):
    """SQLite-backed repository for analysis results."""

    STATES = {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _initialize_database(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            # Create analysis runs table to track analysis sessions
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_name TEXT,
                    created_at TEXT,
                    system_prompt TEXT,
                    general_prompt TEXT,
                    include_overall_conclusion INTEGER,
                    split_by_criterion INTEGER DEFAULT 0
                )
                """
            )
            
            # Create criteria table to store criterion definitions
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS criteria (
                    criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    title TEXT,
                    description TEXT,
                    scoring_system TEXT,
                    include_review INTEGER DEFAULT 0,
                    criterion_key TEXT,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
                )
                """
            )
            
            # Create analysis_results table with run_id reference
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    task_id TEXT PRIMARY KEY,
                    run_id INTEGER,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    assignee TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    state TEXT DEFAULT 'PENDING',
                    total_score REAL,
                    summary TEXT,
                    recommendations TEXT,
                    raw_response TEXT,
                    analyzed_at TEXT,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
                )
                """
            )
            
            # Create indexes for better query performance
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_results_run_id 
                ON analysis_results(run_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_criteria_run_id 
                ON criteria(run_id)
                """
            )
            
            connection.commit()

    def save_pending(self, task_id: str, task_data: Dict[str, Any], run_id: int | None = None) -> None:
        """Save a pending analysis entry for a task."""
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO analysis_results 
                (task_id, run_id, title, description, status, assignee, created_at, updated_at, state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """,
                (
                    task_id,
                    run_id,
                    task_data.get("title"),
                    task_data.get("description"),
                    task_data.get("status"),
                    task_data.get("assignee"),
                    task_data.get("created_at"),
                    task_data.get("updated_at"),
                ),
            )
            conn.commit()

    def update_processing(self, task_id: str) -> None:
        """Update the state to processing for a task."""
        now = datetime.now(timezone(timedelta(hours=3))).isoformat()
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                "UPDATE analysis_results SET state = 'PROCESSING', analyzed_at = ? WHERE task_id = ?",
                (now, task_id),
            )
            conn.commit()

    def save_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Save the analysis result for a task."""
        now = datetime.now(timezone(timedelta(hours=3))).isoformat()

        # Compute total_score as average of criteria_scores if available
        total_score = None
        criteria_scores = result.get("criteria_scores", {})
        if criteria_scores:
            scores = [
                float(v)
                for v in criteria_scores.values()
                if isinstance(v, (int, float))
            ]
            if scores:
                total_score = sum(scores) / len(scores)

        # Use overall_conclusion as summary for now
        summary = result.get("overall_conclusion", "")
        if not isinstance(summary, str):
            summary = json.dumps(summary)

        # Handle recommendations as list or string
        recommendations = result.get("recommendations", [])
        if not isinstance(recommendations, str):
            recommendations = json.dumps(recommendations)

        raw_response = json.dumps(result, ensure_ascii=False)

        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                UPDATE analysis_results 
                SET state = 'COMPLETED',
                    total_score = ?,
                    summary = ?,
                    recommendations = ?,
                    raw_response = ?,
                    analyzed_at = ?
                WHERE task_id = ?
                """,
                (total_score, summary, recommendations, raw_response, now, task_id),
            )
            conn.commit()

    def save_failed(self, task_id: str, error: str) -> None:
        """Save a failed analysis for a task."""
        now = datetime.now(timezone(timedelta(hours=3))).isoformat()
        error_data = json.dumps({"error": error}, ensure_ascii=False)
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                UPDATE analysis_results 
                SET state = 'FAILED',
                    raw_response = ?,
                    analyzed_at = ?
                WHERE task_id = ?
                """,
                (error_data, now, task_id),
            )
            conn.commit()

    def get_state(self, task_id: str) -> Optional[str]:
        """Get the current state of a task analysis."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT state FROM analysis_results WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the analysis result for a task."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM analysis_results WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            columns = [description[0] for description in cursor.description]
            data = dict(zip(columns, row))
            if data.get("raw_response"):
                data["analysis"] = json.loads(data["raw_response"])
                del data["raw_response"]

            # Parse JSON fields if they are serialized
            if (
                data.get("summary")
                and isinstance(data["summary"], str)
                and data["summary"].startswith(("{", "["))
            ):
                try:
                    data["summary"] = json.loads(data["summary"])
                except json.JSONDecodeError:
                    pass
            if (
                data.get("recommendations")
                and isinstance(data["recommendations"], str)
                and data["recommendations"].startswith(("{", "["))
            ):
                try:
                    data["recommendations"] = json.loads(data["recommendations"])
                except json.JSONDecodeError:
                    pass

            data["task_id"] = task_id
            return data

    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get all completed analysis results."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM analysis_results WHERE state = 'COMPLETED' ORDER BY analyzed_at DESC"
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))
                if data.get("raw_response"):
                    data["analysis"] = json.loads(data["raw_response"])
                    del data["raw_response"]

                # Parse JSON fields if they are serialized
                if (
                    data.get("summary")
                    and isinstance(data["summary"], str)
                    and data["summary"].startswith(("{", "["))
                ):
                    try:
                        data["summary"] = json.loads(data["summary"])
                    except json.JSONDecodeError:
                        pass
                if (
                    data.get("recommendations")
                    and isinstance(data["recommendations"], str)
                    and data["recommendations"].startswith(("{", "["))
                ):
                    try:
                        data["recommendations"] = json.loads(data["recommendations"])
                    except json.JSONDecodeError:
                        pass

                data["task_id"] = data["task_id"]
                results.append(data)
            return results

    # Legacy batch methods adapted to new schema
    def save_results(
        self, results: List[Dict[str, Any]], run_name: str | None = None
    ) -> int:
        """Save a list of analysis results (legacy)."""
        now = datetime.now(timezone(timedelta(hours=3))).isoformat()
        with sqlite3.connect(self.database_path) as conn:
            for res in results:
                task_id = res.get("key") or res.get("jira_key")
                if not task_id:
                    continue

                # Extract fields
                title = res.get("title", res.get("summary", ""))
                description = res.get("description", res.get("input_description", ""))
                status = res.get("status", "")
                assignee = res.get("assignee", "")
                created_at = res.get("created_at", "")
                updated_at = res.get("updated_at", now)

                # Compute total_score
                criteria_scores = res.get("criteria_scores", {})
                if not criteria_scores:
                    # Legacy, extract from criteria
                    criteria = res.get("criteria", {})
                    criteria_scores = {
                        k: c["score"] for k, c in criteria.items() if "score" in c
                    }
                scores = [
                    float(v)
                    for v in criteria_scores.values()
                    if isinstance(v, (int, float))
                ]
                total_score = sum(scores) / len(scores) if scores else None

                summary = res.get("overall_conclusion", res.get("summary", ""))
                if not isinstance(summary, str):
                    summary = json.dumps(summary)

                recommendations = res.get("recommendations", [])
                if isinstance(recommendations, list):
                    recommendations = json.dumps(recommendations)
                elif not isinstance(recommendations, str):
                    recommendations = json.dumps([recommendations])

                raw_response = json.dumps(res, ensure_ascii=False)

                conn.execute(
                    """
                    INSERT OR REPLACE INTO analysis_results 
                    (task_id, title, description, status, assignee, created_at, updated_at, state, total_score, summary, recommendations, raw_response, analyzed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        title,
                        description,
                        status,
                        assignee,
                        created_at,
                        updated_at,
                        total_score,
                        summary,
                        recommendations,
                        raw_response,
                        now,
                    ),
                )
            conn.commit()
        return 1  # Dummy

    def get_results(self, run_id: int) -> List[Dict[str, Any]]:
        """Retrieve analysis results (legacy, ignores run_id)."""
        full = self.get_all_results()
        return [r["analysis"] for r in full]

    def get_latest_results(self) -> List[Dict[str, Any]]:
        """Retrieve the most recent analysis results (legacy)."""
        all_results = self.get_all_results()
        if all_results:
            all_results.sort(key=lambda x: x.get("analyzed_at", ""), reverse=True)
            return [r["analysis"] for r in all_results[:50]]
        return []

    # Analysis run management methods
    def create_analysis_run(
        self,
        run_name: str | None = None,
        system_prompt: str = "",
        general_prompt: str = "",
        include_overall_conclusion: bool = True,
        split_by_criterion: bool = False,
    ) -> int:
        """Create a new analysis run and return its ID."""
        now = datetime.now(timezone(timedelta(hours=3))).isoformat()
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_runs 
                (run_name, created_at, system_prompt, general_prompt, include_overall_conclusion, split_by_criterion)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_name,
                    now,
                    system_prompt,
                    general_prompt,
                    1 if include_overall_conclusion else 0,
                    1 if split_by_criterion else 0,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def save_criteria(
        self,
        run_id: int,
        criteria: list[dict]
    ) -> None:
        """Save criteria definitions for an analysis run."""
        with sqlite3.connect(self.database_path) as conn:
            # Clear existing criteria for this run
            conn.execute("DELETE FROM criteria WHERE run_id = ?", (run_id,))
            
            # Insert new criteria
            for criterion in criteria:
                conn.execute(
                    """
                    INSERT INTO criteria 
                    (run_id, title, description, scoring_system, include_review, criterion_key)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        criterion.get("title", ""),
                        criterion.get("description", ""),
                        criterion.get("scoring_system", "percent"),
                        1 if criterion.get("include_review", False) else 0,
                        criterion.get("key", ""),
                    ),
                )
            conn.commit()

    def get_analysis_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get analysis run configuration by ID."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM analysis_runs WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            columns = [description[0] for description in cursor.description]
            data = dict(zip(columns, row))
            
            # Convert boolean fields
            data["include_overall_conclusion"] = bool(data.get("include_overall_conclusion", 1))
            data["split_by_criterion"] = bool(data.get("split_by_criterion", 0))
            
            return data

    def get_analysis_runs(self) -> List[Dict[str, Any]]:
        """Get all analysis runs."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM analysis_runs ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))
                
                # Convert boolean fields
                data["include_overall_conclusion"] = bool(data.get("include_overall_conclusion", 1))
                data["split_by_criterion"] = bool(data.get("split_by_criterion", 0))
                
                results.append(data)
            return results

    def get_criteria(self, run_id: int) -> List[Dict[str, Any]]:
        """Get criteria definitions for an analysis run."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM criteria WHERE run_id = ? ORDER BY criterion_id",
                (run_id,),
            )
            rows = cursor.fetchall()
            results = []
            if rows:
                for row in rows:
                    columns = [desc[0] for desc in cursor.description]
                    data = dict(zip(columns, row))
                    
                    # Convert boolean fields
                    data["include_review"] = bool(data.get("include_review", 0))
                    
                    results.append(data)
            return results
