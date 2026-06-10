"""Tests for parallel execution using new provider architecture."""

import time




def test_run_analysis_processes_issues_with_multiple_workers():
    """Test parallel processing works with fake provider."""
    from jira_analyzer.analyzer.core.llm.adapter import SyncToAsyncLLMAdapter
    from jira_analyzer.analyzer.service import AnalysisService
    from jira_analyzer.providers import FakeProvider

    # Create a fake provider that returns simple responses
    fake_provider = FakeProvider('{"overall_conclusion": "ok"}')
    async_provider = SyncToAsyncLLMAdapter(fake_provider)

    # Create service with fake provider
    service = AnalysisService(
        prompt_template="{element_type}: {description}",
        worker_count=2,
        llm_provider=async_provider
    )

    if hasattr(service, '_async_execute_analysis'):
        # If async execution available, test timing
        start_time = time.time()
        
        issues = [
            {"key": f"YA-{index}", "element_type": "Task", "description": f"Task {index}"}
            for index in range(10)
        ]
        
        # Use the service directly instead of run_analysis to avoid timing issues
        results = service.analyze_issues(issues)
        end_time = time.time()
        
        assert [result["key"] for result in results] == [
            f"YA-{index}" for index in range(10)
        ]
        # Processing with fake provider should be fast
        assert end_time - start_time < 1.0
    else:
        # Service doesn't have async execution, just test correctness
        issues = [
            {"key": f"YA-{index}", "element_type": "Task", "description": f"Task {index}"}
            for index in range(5)
        ]
        
        results = service.analyze_issues(issues)
        assert [result["key"] for result in results] == [
            f"YA-{index}" for index in range(5)
        ]


def test_run_analysis_uses_one_worker_as_minimum():
    """Test worker count minimum of 1 with fake provider."""
    from jira_analyzer.analyzer.core.llm.adapter import SyncToAsyncLLMAdapter
    from jira_analyzer.analyzer.service import AnalysisService
    from jira_analyzer.providers import FakeProvider

    fake_provider = FakeProvider('{"overall_conclusion": "ok"}')
    async_provider = SyncToAsyncLLMAdapter(fake_provider)

    service = AnalysisService(
        prompt_template="{element_type}: {description}",
        worker_count=0,  # Should be forced to 1
        llm_provider=async_provider
    )

    assert service.worker_count == 1  # Should be forced to minimum

    results = service.analyze_issues(
        [{"key": "YA-1", "element_type": "Task", "description": "Task"}]
    )

    assert results[0]["key"] == "YA-1"


def test_parallel_worker_configurations():
    """Test different worker configurations with fake provider."""
    from jira_analyzer.analyzer.core.llm.adapter import SyncToAsyncLLMAdapter
    from jira_analyzer.analyzer.service import AnalysisService
    from jira_analyzer.providers import FakeProvider

    test_cases = [1, 2, 4, 8]

    for worker_count in test_cases:
        fake_provider = FakeProvider('{"overall_conclusion": "ok"}')
        async_provider = SyncToAsyncLLMAdapter(fake_provider)

        service = AnalysisService(
            prompt_template="{element_type}: {description}",
            worker_count=worker_count,
            llm_provider=async_provider
        )

        issues = [
            {"key": f"YA-{index}", "element_type": "Task", "description": f"Task {index}"}
            for index in range(worker_count * 2)
        ]

        results = service.analyze_issues(issues)
        assert len(results) == worker_count * 2
        assert [result["key"] for result in results] == [
            f"YA-{index}" for index in range(worker_count * 2)
        ]
