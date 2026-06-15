"""Tests for analysis run / config separation and deduplication.

These verify that:
- Analysis configs are stored separately in analysis_configs and deduplicated by hash
- Each analysis run is an independent session with its own run_id
- Run names default to current datetime
- Criteria are read from config JSON for new-style runs
- Legacy runs (pre-migration) remain readable
- Existing databases upgrade cleanly
"""

import json
import re
import sqlite3
from pathlib import Path

from jira_analyzer.analyzer.core.config import AnalysisConfig, CriterionDefinition, ReasoningEffort
from jira_analyzer.analyzer.service import AnalysisService
from jira_analyzer.storage.sqlite_repository import SqliteAnalysisResultRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    system_prompt: str = "You are a code reviewer.",
    general_prompt: str = "Analyze the following.",
    criteria: list | None = None,
    include_overall_conclusion: bool = True,
) -> AnalysisConfig:
    if criteria is None:
        criteria = [
            CriterionDefinition(title="Quality", description="Code quality",
                            scoring_system="percent", include_review=False, key="quality"),
        ]
    return AnalysisConfig(
        system_prompt=system_prompt,
        general_prompt=general_prompt,
        criteria=criteria,
        include_overall_conclusion=include_overall_conclusion,
    )


def _create_legacy_database(db_path: Path) -> None:
    """Create a database matching the pre-migration schema (without config_id)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_name TEXT,
            created_at TEXT,
            system_prompt TEXT,
            general_prompt TEXT,
            include_overall_conclusion INTEGER,
            split_by_criterion INTEGER DEFAULT 0,
            reasoning_enabled INTEGER DEFAULT 0,
            reasoning_effort TEXT DEFAULT 'high'
        )
    """)
    conn.execute("""
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
            analyzed_at TEXT
        )
    """)
    conn.execute(
        """INSERT INTO analysis_runs (run_name, created_at, system_prompt,
           general_prompt, include_overall_conclusion, split_by_criterion,
           reasoning_enabled, reasoning_effort)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("Legacy Run", "2026-01-01T00:00:00", "Old system prompt",
         "Old general prompt", 1, 0, 0, "high"),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConfigDeduplication:
    """Verify that identical configs share one row in analysis_configs."""

    def test_same_config_creates_single_config_row(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)
        config = _make_config()

        svc1 = AnalysisService(prompt_config=config, repo=repo,
                               split_by_criterion=False, reasoning_effort=ReasoningEffort.HIGH)
        svc2 = AnalysisService(prompt_config=config, repo=repo,
                               split_by_criterion=False, reasoning_effort=ReasoningEffort.HIGH)

        run_id1 = svc1.create_analysis_run()
        run_id2 = svc2.create_analysis_run()

        # Runs are independent
        assert run_id1 != run_id2, "Each run must have its own ID"

        # Only one config row
        conn = sqlite3.connect(str(db))
        rows = conn.execute("SELECT config_id FROM analysis_configs").fetchall()
        conn.close()
        assert len(rows) == 1, "Identical configs should produce one config row"

    def test_different_configs_create_separate_rows(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        cfg_a = _make_config(system_prompt="Prompt A")
        cfg_b = _make_config(system_prompt="Prompt B")

        svc_a = AnalysisService(prompt_config=cfg_a, repo=repo)
        svc_b = AnalysisService(prompt_config=cfg_b, repo=repo)

        svc_a.create_analysis_run()
        svc_b.create_analysis_run()

        conn = sqlite3.connect(str(db))
        rows = conn.execute("SELECT config_id FROM analysis_configs").fetchall()
        conn.close()
        assert len(rows) == 2, "Different configs should produce separate config rows"

    def test_config_hash_differs_when_criteria_differ(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        criteria_a = [CriterionDefinition(title="A", description="Desc A", key="a")]
        criteria_b = [CriterionDefinition(title="B", description="Desc B", key="b")]

        svc_a = AnalysisService(
            prompt_config=_make_config(criteria=criteria_a), repo=repo,
        )
        svc_b = AnalysisService(
            prompt_config=_make_config(criteria=criteria_b), repo=repo,
        )

        svc_a.create_analysis_run()
        svc_b.create_analysis_run()

        conn = sqlite3.connect(str(db))
        hashes = [r[0] for r in conn.execute(
            "SELECT config_hash FROM analysis_configs ORDER BY config_id"
        ).fetchall()]
        conn.close()
        assert hashes[0] != hashes[1], "Different criteria must produce different hashes"

    def test_config_hash_differs_when_reasoning_differs(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)
        config = _make_config()

        svc_high = AnalysisService(prompt_config=config, repo=repo,
                                   reasoning_effort=ReasoningEffort.HIGH)
        svc_low = AnalysisService(prompt_config=config, repo=repo,
                                  reasoning_effort=ReasoningEffort.LOW)

        svc_high.create_analysis_run()
        svc_low.create_analysis_run()

        conn = sqlite3.connect(str(db))
        rows = conn.execute("SELECT config_id FROM analysis_configs").fetchall()
        conn.close()
        assert len(rows) == 2, "Different reasoning_effort must produce different configs"


class TestRunIndependence:
    """Each run is its own session with a unique ID."""

    def test_runs_have_increasing_ids(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)
        config = _make_config()

        ids = []
        for i in range(5):
            svc = AnalysisService(prompt_config=config, repo=repo)
            ids.append(svc.create_analysis_run())

        assert ids == [1, 2, 3, 4, 5], "Runs must get sequential IDs"

    def test_all_runs_listed_in_get_analysis_runs(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)
        config = _make_config()

        for i in range(3):
            svc = AnalysisService(prompt_config=config, repo=repo)
            svc.create_analysis_run()

        runs = repo.get_analysis_runs()
        assert len(runs) == 3

    def test_run_has_created_at_timestamp(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)
        config = _make_config()

        svc = AnalysisService(prompt_config=config, repo=repo)
        run_id = svc.create_analysis_run()

        run = repo.get_analysis_run(run_id)
        assert run.get("created_at") is not None


class TestRunNameDefaults:
    """Run name should default to current datetime when not provided."""

    def test_default_run_name_is_datetime_string(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)
        config = _make_config()

        svc = AnalysisService(prompt_config=config, repo=repo)
        run_id = svc.create_analysis_run()

        run = repo.get_analysis_run(run_id)
        name = run.get("run_name", "")
        # Should look like "2026-06-10 12:01:45"
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", name), \
            f"Expected datetime format, got: {name}"

    def test_custom_run_name_is_preserved(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)
        config = _make_config()

        svc = AnalysisService(prompt_config=config, repo=repo)
        run_id = svc.create_analysis_run(run_name="My Custom Run")

        run = repo.get_analysis_run(run_id)
        assert run["run_name"] == "My Custom Run"

    def test_multiple_runs_with_same_name_all_unique(self, tmp_path):
        """Even with explicit same name, runs are independent sessions."""
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)
        config = _make_config()

        svc1 = AnalysisService(prompt_config=config, repo=repo)
        svc2 = AnalysisService(prompt_config=config, repo=repo)

        rid1 = svc1.create_analysis_run(run_name="Daily Check")
        rid2 = svc2.create_analysis_run(run_name="Daily Check")

        assert rid1 != rid2
        assert repo.get_analysis_run(rid1)["run_name"] == "Daily Check"
        assert repo.get_analysis_run(rid2)["run_name"] == "Daily Check"


class TestCriteriaResolution:
    """get_criteria reads from config JSON for new runs, falls back for legacy."""

    def test_criteria_from_config_json(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        criteria = [
            CriterionDefinition(title="Perf", description="Performance",
                            scoring_system="percent", key="perf"),
            CriterionDefinition(title="Sec", description="Security",
                            scoring_system="binary", include_review=True, key="sec"),
        ]
        config = _make_config(criteria=criteria)

        svc = AnalysisService(prompt_config=config, repo=repo)
        run_id = svc.create_analysis_run()

        result = repo.get_criteria(run_id)
        assert len(result) == 2
        assert result[0]["title"] == "Perf"
        assert result[0]["scoring_system"] == "percent"
        assert result[1]["title"] == "Sec"
        assert result[1]["include_review"] is True

    def test_criteria_empty_when_no_criteria_defined(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        config = AnalysisConfig(
            system_prompt="Test",
            general_prompt="Test",
            criteria=[],
            include_overall_conclusion=False,
        )
        svc = AnalysisService(prompt_config=config, repo=repo)
        run_id = svc.create_analysis_run()

        assert repo.get_criteria(run_id) == []

    def test_criteria_returns_empty_for_run_without_config(self, tmp_path):
        """Runs with no config_id return empty criteria."""
        db = tmp_path / "legacy.db"
        _create_legacy_database(db)
        repo = SqliteAnalysisResultRepository(db)

        result = repo.get_criteria(1)
        assert result == []


class TestConfigMerging:
    """get_analysis_run / get_analysis_runs merge config data from analysis_configs."""

    def test_get_analysis_run_merges_config_data(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        config = _make_config(
            system_prompt="Custom system",
            general_prompt="Custom general",
        )

        svc = AnalysisService(prompt_config=config, repo=repo,
                              split_by_criterion=True, reasoning_effort=ReasoningEffort.LOW)
        run_id = svc.create_analysis_run()

        run = repo.get_analysis_run(run_id)
        assert run["system_prompt"] == "Custom system"
        assert run["general_prompt"] == "Custom general"
        assert run["include_overall_conclusion"] is True
        assert run["split_by_criterion"] is True
        assert run["reasoning_enabled"] is True  # because effort != "none"
        assert run["reasoning_effort"] == "low"
        assert run["config_id"] is not None

    def test_get_analysis_runs_merges_config_data(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        config = _make_config(system_prompt="SysPrompt")
        svc = AnalysisService(prompt_config=config, repo=repo)
        svc.create_analysis_run()

        runs = repo.get_analysis_runs()
        assert len(runs) == 1
        assert runs[0]["system_prompt"] == "SysPrompt"

    def test_legacy_run_returns_no_config_fields(self, tmp_path):
        """A legacy run (no config_id) returns only basic run fields."""
        db = tmp_path / "legacy.db"
        _create_legacy_database(db)
        repo = SqliteAnalysisResultRepository(db)

        run = repo.get_analysis_run(1)
        # Legacy run has no config_id, so no config fields are merged
        assert run["run_name"] == "Legacy Run"
        assert run.get("config_id") is None
        # Config fields come from analysis_configs merge only
        assert "system_prompt" not in run


class TestSaveCriteria:
    """save_criteria is a no-op (criteria live in config_json)."""

    def test_save_criteria_noop(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        criteria = [CriterionDefinition(title="Original", description="Original desc", key="orig")]
        config = _make_config(criteria=criteria)

        svc = AnalysisService(prompt_config=config, repo=repo)
        run_id = svc.create_analysis_run()

        # Attempt to save via the legacy path — should be a no-op
        repo.save_criteria(run_id, [{"title": "Should Be Ignored"}])

        # Criteria still come from config_json
        result = repo.get_criteria(run_id)
        assert len(result) == 1
        assert result[0]["title"] == "Original"


class TestDatabaseMigration:
    """Existing databases without analysis_configs/config_id upgrade cleanly."""

    def test_migration_adds_config_id_column(self, tmp_path):
        db = tmp_path / "legacy.db"
        _create_legacy_database(db)

        # Migrate by constructing repo
        SqliteAnalysisResultRepository(db)

        conn = sqlite3.connect(str(db))
        cols = [r[1] for r in conn.execute(
            "PRAGMA table_info(analysis_runs)"
        ).fetchall()]
        conn.close()
        assert "config_id" in cols

    def test_migration_creates_analysis_configs_table(self, tmp_path):
        db = tmp_path / "legacy.db"
        _create_legacy_database(db)
        SqliteAnalysisResultRepository(db)

        conn = sqlite3.connect(str(db))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "analysis_configs" in tables

    def test_legacy_data_readable_after_migration(self, tmp_path):
        """Legacy data is still readable after migration."""
        db = tmp_path / "legacy.db"
        _create_legacy_database(db)
        repo = SqliteAnalysisResultRepository(db)

        run = repo.get_analysis_run(1)
        assert run["run_name"] == "Legacy Run"

        runs = repo.get_analysis_runs()
        assert len(runs) == 1

    def test_legacy_run_has_no_config_id(self, tmp_path):
        """Legacy run's config_id should be None."""
        db = tmp_path / "legacy.db"
        _create_legacy_database(db)
        repo = SqliteAnalysisResultRepository(db)

        run = repo.get_analysis_run(1)
        assert run.get("config_id") is None

    def test_migration_idempotent(self, tmp_path):
        """Running migration twice should be harmless."""
        db = tmp_path / "legacy.db"
        _create_legacy_database(db)

        SqliteAnalysisResultRepository(db)
        SqliteAnalysisResultRepository(db)

        conn = sqlite3.connect(str(db))
        cols = [r[1] for r in conn.execute(
            "PRAGMA table_info(analysis_runs)"
        ).fetchall()]
        conn.close()
        assert "config_id" in cols
        assert "analysis_configs" in [r[0] for r in sqlite3.connect(str(db)).execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]


class TestConfigExport:
    """Export data used by the results viewer should work correctly."""

    def test_export_contains_all_config_fields(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        config = _make_config(
            system_prompt="Export test",
            general_prompt="Export general",
        )
        svc = AnalysisService(prompt_config=config, repo=repo)
        run_id = svc.create_analysis_run()

        run = repo.get_analysis_run(run_id)
        criteria = repo.get_criteria(run_id)

        export = {
            "run_id": run_id,
            "config_id": run.get("config_id"),
            "system_prompt": run.get("system_prompt"),
            "general_prompt": run.get("general_prompt"),
            "criteria": criteria,
        }
        export_json = json.dumps(export, ensure_ascii=False, indent=2)
        assert export["config_id"] is not None
        assert export["system_prompt"] == "Export test"
        assert len(export["criteria"]) == 1
        json.loads(export_json)

    def test_legacy_export_has_no_config_fields(self, tmp_path):
        """Legacy run export has no merged config fields."""
        db = tmp_path / "legacy.db"
        _create_legacy_database(db)
        repo = SqliteAnalysisResultRepository(db)

        run = repo.get_analysis_run(1)
        criteria = repo.get_criteria(1)

        assert run.get("system_prompt") is None
        assert criteria == []


class TestCreateAnalysisRunDirect:
    """Test the repository-level create_analysis_run directly."""

    def test_direct_create_generates_new_run(self, tmp_path):
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        run_id = repo.create_analysis_run(run_name="Direct Run")
        run = repo.get_analysis_run(run_id)
        assert run["run_name"] == "Direct Run"
        assert run.get("config_id") is None  # no config data passed
        assert run_id == 1

    def test_direct_create_with_config_json(self, tmp_path):
        """Even creating runs directly with config data works."""
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        config_dict = {
            "system_prompt": "Direct",
            "general_prompt": "Direct general",
            "criteria": [{"title": "Direct Crit", "key": "dc"}],
        }
        config_json = json.dumps(config_dict, sort_keys=True, ensure_ascii=False)
        import hashlib
        config_hash = hashlib.sha256(config_json.encode("utf-8")).hexdigest()

        run_id = repo.create_analysis_run(
            run_name="Direct with Config",
            config_hash=config_hash,
            config_json=config_json,
        )
        run = repo.get_analysis_run(run_id)
        assert run["config_id"] is not None
        assert run["system_prompt"] == "Direct"

        criteria = repo.get_criteria(run_id)
        assert len(criteria) == 1
        assert criteria[0]["title"] == "Direct Crit"

    def test_direct_create_dedups_config(self, tmp_path):
        """Two runs sharing config via direct API should dedup configs."""
        db = tmp_path / "test.db"
        repo = SqliteAnalysisResultRepository(db)

        config_dict = {"system_prompt": "Shared", "general_prompt": "", "criteria": []}
        config_json = json.dumps(config_dict, sort_keys=True, ensure_ascii=False)
        import hashlib
        config_hash = hashlib.sha256(config_json.encode("utf-8")).hexdigest()

        r1 = repo.create_analysis_run(
            run_name="A", config_hash=config_hash, config_json=config_json,
        )
        r2 = repo.create_analysis_run(
            run_name="B", config_hash=config_hash, config_json=config_json,
        )

        assert r1 != r2  # different runs
        conn = sqlite3.connect(str(db))
        config_count = conn.execute(
            "SELECT COUNT(*) FROM analysis_configs"
        ).fetchone()[0]
        conn.close()
        assert config_count == 1  # single config row
