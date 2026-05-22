from __future__ import annotations

import json
import asyncio

from jira_analyzer.analyzer.service import AnalysisService
from jira_analyzer.analyzer.core.llm.provider import LLMProvider


class FakeLLMProvider(LLMProvider):
    """Fake async provider for testing."""
    
    async def send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict:
        return {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "overall_conclusion": "ok",
            "criteria": {"completeness": {"title": "Completeness", "description": "Test", "scoring_system": "percent", "score": 100}},
            "criteria_scores": {"completeness": 100},
        }


def test_analysis_service_exposes_design_spec_methods(tmp_path):
    fake_provider = FakeLLMProvider()
    service = AnalysisService(
        prompt_template="{element_type}: {description}", 
        worker_count=1,
        llm_provider=fake_provider
    )

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
