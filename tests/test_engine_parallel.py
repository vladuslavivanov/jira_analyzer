from __future__ import annotations

import asyncio
import time

from jira_analyzer.analyzer.engine import run_analysis
from jira_analyzer.analyzer.core.llm.provider import LLMProvider


class FakeAsyncProvider(LLMProvider):
    """Fake async provider for testing."""
    
    def __init__(self, delay: float = 0):
        self.delay = delay
    
    async def send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict:
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return {"prompt": prompt, "system_prompt": system_prompt}


def test_run_analysis_processes_issues_with_multiple_workers():
    fake_provider = FakeAsyncProvider(delay=1.0)
    issues = [
        {"key": f"YA-{index}", "element_type": "Task", "description": f"Task {index}"}
        for index in range(10)
    ]

    start_time = time.time()
    results = run_analysis(
        issues,
        prompt_template="{element_type}: {description}",
        worker_count=2,
        llm_provider=fake_provider,
    )
    end_time = time.time()

    assert [result["key"] for result in results] == [
        f"YA-{index}" for index in range(10)
    ]
    assert end_time - start_time < 6.0  # 10 issues, 2 workers, each 1s => ~5s


def test_run_analysis_uses_one_worker_as_minimum():
    fake_provider = FakeAsyncProvider(delay=0)
    results = run_analysis(
        [{"key": "YA-1", "element_type": "Task", "description": "Task"}],
        prompt_template="{element_type}: {description}",
        worker_count=0,
        llm_provider=fake_provider,
    )

    assert results[0]["key"] == "YA-1"
