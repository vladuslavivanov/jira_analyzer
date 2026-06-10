from __future__ import annotations

import hashlib
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
                    config_id INTEGER
                )
                """
            )
            
            # Create analysis_configs table to store deduplicated configs
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_configs (
                    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_hash TEXT UNIQUE,
                    config_json TEXT NOT NULL,
                    created_at TEXT
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
                    summary TEXT,
                    recommendations TEXT,
                    raw_response TEXT,
                    analyzed_at TEXT,
                FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
                )
                """
            )
            
            # Migrate existing databases: add config_id column if missing
            cursor = connection.execute("PRAGMA table_info(analysis_runs)")
            columns = [row[1] for row in cursor.fetchall()]
            if "config_id" not in columns:
                connection.execute(
                    "ALTER TABLE analysis_runs ADD COLUMN config_id INTEGER"
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
                CREATE INDEX IF NOT EXISTS idx_analysis_configs_hash
                ON analysis_configs(config_hash)
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
                    summary = ?,
                    recommendations = ?,
                    raw_response = ?,
                    analyzed_at = ?
                WHERE task_id = ?
                """,
                (summary, recommendations, raw_response, now, task_id),
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
        """Get all analysis results (all states: PENDING, PROCESSING, COMPLETED, FAILED)."""
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM analysis_results ORDER BY COALESCE(analyzed_at, created_at) DESC"
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
                    (task_id, title, description, status, assignee, created_at, updated_at, state, summary, recommendations, raw_response, analyzed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        title,
                        description,
                        status,
                        assignee,
                        created_at,
                        updated_at,
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
        return [r["analysis"] for r in full if r.get("analysis")]

    def get_latest_results(self) -> List[Dict[str, Any]]:
        """Retrieve the most recent analysis results (legacy)."""
        all_results = self.get_all_results()
        if all_results:
            all_results.sort(key=lambda x: x.get("analyzed_at", ""), reverse=True)
            return [r["analysis"] for r in all_results[:50] if r.get("analysis")]
        return []

    # Analysis run management methods

    def _find_config_by_hash(self, config_hash: str) -> int | None:
        """Find an existing config by its hash.
        
        Returns config_id if found, None otherwise.
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT config_id FROM analysis_configs WHERE config_hash = ? LIMIT 1",
                (config_hash,),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def _find_or_create_config(self, config_hash: str, config_json: str) -> int:
        """Find an existing config by hash or create a new one.
        
        Returns the config_id.
        """
        if config_hash:
            existing = self._find_config_by_hash(config_hash)
            if existing is not None:
                return existing

        now = datetime.now(timezone(timedelta(hours=3))).isoformat()
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_configs (config_hash, config_json, created_at)
                VALUES (?, ?, ?)
                """,
                (config_hash, config_json, now),
            )
            conn.commit()
            return cursor.lastrowid

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
        
        The configuration (prompts, criteria, settings) is stored in the
        analysis_configs table and deduplicated by config_hash. Each run
        is an individual session referencing a config.
        """
        # Find or create the config (deduplicates by hash)
        config_id = None
        if config_hash and config_json:
            config_id = self._find_or_create_config(config_hash, config_json)

        now = datetime.now(timezone(timedelta(hours=3))).isoformat()
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO analysis_runs 
                (run_name, created_at, config_id)
                VALUES (?, ?, ?)
                """,
                (
                    run_name,
                    now,
                    config_id,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def save_criteria(
        self,
        run_id: int,
        criteria: list[dict]
    ) -> None:
        """Save criteria definitions for an analysis run.
        
        Criteria are stored inside the config JSON in analysis_configs,
        so this is a no-op. Kept for interface compatibility.
        """

    def get_analysis_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get analysis run by ID.
        
        Merges config data (prompts, criteria, settings) from
        analysis_configs when the run has a config_id reference.
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT run_id, run_name, created_at, config_id FROM analysis_runs WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            columns = [description[0] for description in cursor.description]
            data = dict(zip(columns, row))

            # Merge config data from analysis_configs
            config_id = data.get("config_id")
            if config_id is not None:
                config_cursor = conn.execute(
                    "SELECT config_json FROM analysis_configs WHERE config_id = ?",
                    (config_id,),
                )
                config_row = config_cursor.fetchone()
                if config_row:
                    try:
                        config_data = json.loads(config_row[0])
                        for key in ("system_prompt", "general_prompt", "include_overall_conclusion", "split_by_criterion", "reasoning_enabled", "reasoning_effort"):
                            if key in config_data:
                                data[key] = config_data[key]
                    except json.JSONDecodeError:
                        pass

            return data

    def get_analysis_runs(self) -> List[Dict[str, Any]]:
        """Get all analysis runs.
        
        Merges config data from analysis_configs when available.
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT run_id, run_name, created_at, config_id FROM analysis_runs ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))

                # Merge config data from analysis_configs
                config_id = data.get("config_id")
                if config_id is not None:
                    config_cursor = conn.execute(
                        "SELECT config_json FROM analysis_configs WHERE config_id = ?",
                        (config_id,),
                    )
                    config_row = config_cursor.fetchone()
                    if config_row:
                        try:
                            config_data = json.loads(config_row[0])
                            for key in ("system_prompt", "general_prompt", "include_overall_conclusion", "split_by_criterion", "reasoning_enabled", "reasoning_effort"):
                                if key in config_data:
                                    data[key] = config_data[key]
                        except json.JSONDecodeError:
                            pass

                results.append(data)
            return results

    def get_criteria(self, run_id: int) -> List[Dict[str, Any]]:
        """Get criteria definitions for an analysis run.
        
        Criteria are read from the config JSON stored in analysis_configs.
        Returns an empty list if the run has no config reference.
        """
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(
                "SELECT config_id FROM analysis_runs WHERE run_id = ?",
                (run_id,),
            )
            run_row = cursor.fetchone()
            if not run_row:
                return []
            config_id = run_row[0]
            if config_id is None:
                return []

            config_cursor = conn.execute(
                "SELECT config_json FROM analysis_configs WHERE config_id = ?",
                (config_id,),
            )
            config_row = config_cursor.fetchone()
            if not config_row:
                return []

            try:
                config_data = json.loads(config_row[0])
                criteria = config_data.get("criteria", [])
                return [
                    {
                        "title": c.get("title", ""),
                        "description": c.get("description", ""),
                        "scoring_system": c.get("scoring_system", "percent"),
                        "include_review": bool(c.get("include_review", False)),
                        "criterion_key": c.get("key", ""),
                    }
                    for c in criteria
                ]
            except json.JSONDecodeError:
                return []
