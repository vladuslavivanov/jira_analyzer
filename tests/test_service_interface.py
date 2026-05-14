from __future__ import annotations

import json
import sys
from pathlib import Path
import types

from jira_analyzer.analyzer.service import AnalysisService


def test_analysis_service_exposes_design_spec_methods(monkeypatch, tmp_path):
    def fake_send_prompt(prompt, system_prompt=None):
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
        "key": "YA-1",
        "element type": "Task",
        "description": "Example task",
    }

    single_result = service.analyze_task(issue)
    assert single_result["key"] == "YA-1"
    assert single_result["overall_conclusion"] == "ok"

    dataset_path = tmp_path / "issues.json"
    dataset_path.write_text(
        json.dumps([
            {"key": "YA-2", "element type": "Task", "description": "Task two"},
        ]),
        encoding="utf-8",
    )

    dataset_results = service.analyze_dataset(str(dataset_path))
    assert isinstance(dataset_results, list)
    assert dataset_results[0]["key"] == "YA-2"

    json_report = service.generate_report(dataset_results, format="json")
    assert json.loads(json_report)[0]["key"] == "YA-2"

    markdown_report = service.generate_report(dataset_results, format="markdown")
    assert markdown_report.startswith("# Jira Task Analysis Report")
