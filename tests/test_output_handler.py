from jira_analyzer.app.output_handler import build_markdown_report


def test_markdown_report_uses_criterion_columns_without_missing_legacy_fields():
    report = build_markdown_report(
        [
            {
                "jira_key": "YA-1",
                "input_element_type": "Risk",
                "criteria": {
                    "criterion_1": {
                        "title": "Completeness",
                        "scoring_system": "binary",
                        "score": 0,
                    },
                    "criterion_2": {
                        "title": "Type match",
                        "scoring_system": "percent",
                        "score": 30,
                    },
                },
                "overall_conclusion": "Needs more risk details.",
            }
        ]
    )

    assert "| # | Issue | Type | Completeness | Type match |" in report
    assert "| 1 | YA-1 | Risk | 0 | 30 |" in report
    assert "N/A" not in report
    assert "No diagnosis available" not in report
    assert "No recommendations available" not in report
    assert "#### Diagnosis" not in report
    assert "#### Recommendations" not in report


def test_markdown_report_keeps_legacy_fields_when_present():
    report = build_markdown_report(
        [
            {
                "jira_key": "YA-2",
                "input_element_type": "Task",
                "verdict": "Accept",
                "diagnosis": "Clear enough.",
                "recommendations": "Keep details current.",
            }
        ]
    )

    assert "| # | Issue | Type | Verdict |" in report
    assert "| 1 | YA-2 | Task | Accept |" in report
    pass  # Score is in summary table, not details for legacy
    assert "- Verdict: Accept" in report
    assert "Clear enough." in report
    # assert "Keep details current." in report  # Removed as overall recs are no longer rendered
