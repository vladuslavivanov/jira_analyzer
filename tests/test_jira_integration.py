import json
import sys
import threading
import types
from urllib.parse import quote
from urllib.request import urlopen

import pytest

from mock_jira.server import create_server
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

    def search_issues(self, jql, maxResults=50):
        with urlopen(
            f"{self.server}/rest/api/2/search?jql={quote(jql)}&maxResults={maxResults}",
            timeout=5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
            result = []
            for raw_issue in payload["issues"]:
                issue = to_namespace(raw_issue)
                issue.raw = raw_issue
                result.append(issue)
            return result


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

    assert analysis_input["element_type"] == "Risk"
    assert analysis_input["key"] == "YA-1"
    assert analysis_input["description"].startswith("Риск: появление новых")
    assert "[название_команды]" in analysis_input["description"]


def test_jira_client_searches_issues_with_jql(mock_jira_url, fake_jira_module):
    client = JiraTaskClient(
        JiraConnectionConfig(server=mock_jira_url, verify_ssl=False)
    )

    issues = client.search_issues("project = YA")

    assert [issue.key for issue in issues] == ["YA-1", "YA-2"]


