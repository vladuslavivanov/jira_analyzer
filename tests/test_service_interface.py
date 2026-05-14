from __future__ import annotations

import json
import sys
from pathlib import Path
import types

from jira_analyzer.analyzer.service import AnalysisService


def test_analysis_service_exposes_design_spec_methods(monkeypatch, tmp_path):
    async def fake_send_prompt(prompt, system_prompt=None):
            return {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "overall_conclusion": "ok",
                "criteria": {"completeness": {"title": "Completeness", "description": "Test", "scoring_system": "percent", "score": 100}},
                "criteria_scores": {"completeness": 100},
            }

    fake_module = types.ModuleType("jira_analyzer.analyzer.core.llm.deepseek_client")
    fake_module.send_prompt = fake_send_prompt
    monkeypatch.setitem(sys.modules, "jira_analyzer.analyzer.core.llm.deepseek_client", fake_module)

    service = AnalysisService(prompt_template="{element_type}: {description}", worker_count=1)

    issue = {
        "jira_key": "YA-1",
        "element_type": "Task",
        "description": "Example task",
    }

    single_result = service.analyze_task(issue)
    assert single_result["jira_key"] == "YA-1"
    assert single_result["overall_conclusion"] == "ok"

    issues = [
        {"jira_key": "YA-2", "element_type": "Task", "description": "Task two"},
    ]

    dataset_results = service.analyze_issues(issues)
    assert isinstance(dataset_results, list)
    assert dataset_results[0]["jira_key"] == "YA-2"

    json_report = service.generate_report(dataset_results, format="json")
    assert json.loads(json_report)[0]["jira_key"] == "YA-2"

    markdown_report = service.generate_report(dataset_results, format="markdown")
    assert markdown_report.startswith("# Jira Task Analysis Report")


def test_merge_split_results_preserves_duplicate_criterion_keys():
    service = AnalysisService(prompt_template="{element_type}: {description}", worker_count=1)

    responses = [
        {
            "criteria": {
                "criterion_1": {
                    "title": "First",
                    "description": "First criterion",
                    "scoring_system": "percent",
                    "score": 10,
                }
            },
            "criteria_scores": {"criterion_1": 10},
        },
        {
            "criteria": {
                "criterion_1": {
                    "title": "Second",
                    "description": "Second criterion",
                    "scoring_system": "percent",
                    "score": 20,
                }
            },
            "criteria_scores": {"criterion_1": 20},
        },
        {
            "criteria": {
                "criterion_1": {
                    "title": "Third",
                    "description": "Third criterion",
                    "scoring_system": "percent",
                    "score": 30,
                }
            },
            "criteria_scores": {"criterion_1": 30},
        },
    ]

    merged = service._merge_split_results(responses)

    assert merged["criteria"]["criterion_1"]["score"] == 10
    assert merged["criteria"]["criterion_2"]["score"] == 20
    assert merged["criteria"]["criterion_3"]["score"] == 30
    assert merged["criteria_scores"]["criterion_1"] == 10
    assert merged["criteria_scores"]["criterion_2"] == 20
    assert merged["criteria_scores"]["criterion_3"] == 30
