from jira_analyzer.app.output_handler import save_results
from jira_analyzer.storage.sqlite_repository import SqliteAnalysisResultRepository


def test_sqlite_analysis_result_repository_saves_and_loads_results(tmp_path):
    database_path = tmp_path / "analysis.db"
    repository = SqliteAnalysisResultRepository(database_path)

    results = [
        {
            "jira_key": "YA-1",
            "input_element_type": "Task",
            "criteria": {
                "criterion_1": {
                    "title": "Completeness",
                    "scoring_system": "percent",
                    "score": 90,
                }
            },
        }
    ]

    run_id = repository.save_results(results, run_name="test-run")
    assert isinstance(run_id, int)
    loaded_results = repository.get_results(run_id)

    assert loaded_results == results
    latest_results = repository.get_latest_results()
    assert latest_results == results


def test_save_results_writes_to_sqlite_db(tmp_path):
    database_path = tmp_path / "output.db"
    results = [
        {"jira_key": "YA-2", "input_element_type": "Risk", "criteria_scores": {"criterion_1": 50}}
    ]

    save_results(results, str(database_path))

    repository = SqliteAnalysisResultRepository(database_path)
    latest_results = repository.get_latest_results()

    assert latest_results == results
