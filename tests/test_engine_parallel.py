from __future__ import annotations

import sys
import threading
import time
import asyncio
import types

from jira_analyzer.analyzer.engine import run_analysis


def test_run_analysis_processes_issues_with_multiple_workers(monkeypatch):
    processed_threads = set()
    lock = threading.Lock()

    async def fake_send_prompt(prompt, system_prompt=None):
            await asyncio.sleep(1.0)
            return {"prompt": prompt, "system_prompt": system_prompt}

    fake_module = types.ModuleType("jira_analyzer.analyzer.core.llm.deepseek_client")
    fake_module.send_prompt = fake_send_prompt
    monkeypatch.setitem(
        sys.modules,
        "jira_analyzer.analyzer.core.llm.deepseek_client",
        fake_module,
    )

    issues = [
        {"key": f"YA-{index}", "element_type": "Task", "description": f"Task {index}"}
        for index in range(10)
    ]

    start_time = time.time()
    results = run_analysis(
        issues,
        prompt_template="{element_type}: {description}",
        worker_count=2,
    )
    end_time = time.time()

    assert [result["key"] for result in results] == [
        f"YA-{index}" for index in range(10)
    ]
    assert end_time - start_time < 6.0  # 10 issues, 2 workers, each 1s => ~5s


def test_run_analysis_uses_one_worker_as_minimum(monkeypatch):
    async def fake_send_prompt(prompt, system_prompt=None):
            return {"prompt": prompt}

    fake_module = types.ModuleType("jira_analyzer.analyzer.core.llm.deepseek_client")
    fake_module.send_prompt = fake_send_prompt
    monkeypatch.setitem(
        sys.modules,
        "jira_analyzer.analyzer.core.llm.deepseek_client",
        fake_module,
    )

    results = run_analysis(
        [{"key": "YA-1", "element_type": "Task", "description": "Task"}],
        prompt_template="{element_type}: {description}",
        worker_count=0,
    )

    assert results[0]["key"] == "YA-1"
