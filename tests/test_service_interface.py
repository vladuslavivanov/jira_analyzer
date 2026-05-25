"""Tests for AnalysisService using new provider architecture."""

from __future__ import annotations

import json

import pytest

from jira_analyzer.analyzer.service import AnalysisService
from jira_analyzer.providers import BaseLLMProvider, LLMResponse


def test_analysis_service_exposes_design_spec_methods():
    """Test AnalysisService basic functionality using fake provider."""
    # Configure fake provider via environment (or pass directly)
    # For this test, we rely on the default provider resolution
    service = AnalysisService(prompt_template="{element_type}: {description}", worker_count=1)

    issue = {
        "jira_key": "YA-1",
        "element_type": "Task",
        "description": "Example task",
    }

    single_result = service.analyze_task(issue)
    assert single_result["jira_key"] == "YA-1"
    # Note: The fake provider returns canned response, so we just check structure
    assert "jira_key" in single_result

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


def test_analysis_service_with_custom_provider():
    """Test AnalysisService with custom FakeProvider."""
    from jira_analyzer.analyzer.core.llm.adapter import SyncToAsyncLLMAdapter
    from jira_analyzer.providers import FakeProvider

    # Create fake provider with specific JSON response
    fake_provider = FakeProvider('{"overall_conclusion": "pass", "criteria_scores": {"completeness": 100}}')
    async_provider = SyncToAsyncLLMAdapter(fake_provider)

    service = AnalysisService(
        prompt_template="{element_type}: {description}",
        worker_count=1,
        llm_provider=async_provider
    )

    issue = {"jira_key": "YA-1", "element_type": "Task", "description": "Test"}
    result = service.analyze_task(issue)

    assert result["jira_key"] == "YA-1"
    assert result["overall_conclusion"] == "pass"
    assert result["criteria_scores"]["completeness"] == 100


def test_analysis_service_error_handling():
    """Test AnalysisService handles provider errors gracefully."""
    from jira_analyzer.analyzer.core.llm.adapter import SyncToAsyncLLMAdapter

    class BrokenProvider(BaseLLMProvider):
        @property
        def provider_name(self) -> str:
            return "broken"

        def call_llm(self, messages, temperature=0.7, max_tokens=None) -> LLMResponse:
            raise Exception("Simulated provider failure")

    broken_adapter = SyncToAsyncLLMAdapter(BrokenProvider())

    service = AnalysisService(
        prompt_template="{element_type}: {description}",
        worker_count=1,
        llm_provider=broken_adapter
    )

    issue = {"jira_key": "YA-1", "element_type": "Task", "description": "Test"}
    result = service.analyze_task(issue)

    # Service should handle errors and still return result with error info
    assert "jira_key" in result
    assert "error" in result or "analysis" in result
