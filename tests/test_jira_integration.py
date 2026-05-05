from __future__ import annotations

import json
import sys
import threading
import types
from pathlib import Path
from urllib.request import urlopen

import pytest

from jira_analyzer.mock_jira.server import create_server
from jira_analyzer.tasktracker.jira import JiraConnectionConfig, JiraTaskClient
from jira_analyzer.tasktracker.jira import jira_issue_to_analysis_input


def to_namespace(value):
    if isinstance(value, dict):
        return types.SimpleNamespace(
            **{key: to_namespace(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return [to_namespace(item) for item in value]
    return value


class FakeJira:
    def __init__(self, server=None, options=None, **kwargs):
        self.server = server.rstrip("/")
        self.options = options
        self.kwargs = kwargs
        with urlopen(f"{self.server}/rest/api/2/serverInfo", timeout=5):
            pass

    def issue(self, issue_key):
        with urlopen(
            f"{self.server}/rest/api/2/issue/{issue_key}",
            timeout=5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
            issue = to_namespace(payload)
            issue.raw = payload
            return issue


@pytest.fixture
def fake_jira_module(monkeypatch):
    module = types.ModuleType("jira")
    module.JIRA = FakeJira
    monkeypatch.setitem(sys.modules, "jira", module)


@pytest.fixture
def mock_jira_url():
    server = create_server(port=0)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://{host}:{port}"

    server.shutdown()
    server.server_close()


def test_jira_client_fetches_issue_from_mock(mock_jira_url, fake_jira_module):
    client = JiraTaskClient(
        JiraConnectionConfig(server=mock_jira_url, verify_ssl=False)
    )

    issue = client.get_issue("YA-1")

    assert issue.key == "YA-1"
    assert issue.fields.issuetype.name == "Risk"


def test_jira_issue_is_mapped_to_analyzer_input(mock_jira_url, fake_jira_module):
    client = JiraTaskClient(
        JiraConnectionConfig(server=mock_jira_url, verify_ssl=False)
    )

    analysis_input = jira_issue_to_analysis_input(client.get_issue("YA-1"))

    assert analysis_input["element type"] == "Risk"
    assert analysis_input["key"] == "YA-1"
    assert analysis_input["description"].startswith("Риск: появление новых")
    assert "[название_команды]" in analysis_input["description"]


def test_cli_can_analyze_jira_issue_with_mock(
    monkeypatch,
    mock_jira_url,
    fake_jira_module,
):
    from jira_analyzer import cli

    output_file = Path("data/test_jira_integration_output.json")

    def fake_run_analysis(issues):
        assert issues[0]["jira_key"] == "YA-1"
        return [{"input_element_type": issues[0]["element type"], "overall_score": 10}]

    monkeypatch.setattr(cli, "run_analysis", fake_run_analysis)

    try:
        exit_code = cli.main(
            [
                "--jira-server",
                mock_jira_url,
                "--jira-issue",
                "YA-1",
                "--jira-no-verify",
                "--output",
                str(output_file),
            ]
        )

        assert exit_code == 0
        assert json.loads(output_file.read_text(encoding="utf-8")) == [
            {"input_element_type": "Risk", "overall_score": 10}
        ]
    finally:
        if output_file.exists():
            output_file.unlink()
