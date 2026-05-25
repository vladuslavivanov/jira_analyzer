from __future__ import annotations

import json
import threading
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

import pytest

from mock_jira.server import create_server, load_issues


@pytest.fixture
def mock_jira_server():
    server = create_server(port=0)
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://{host}:{port}"

    server.shutdown()
    server.server_close()


def get_json(url: str) -> dict:
    with urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_load_issues_by_key():
    issues = load_issues()

    assert "YA-1" in issues
    assert issues["YA-1"]["element_type"] == "Risk"
    assert issues["YA-1"]["fields"]["issuetype"]["name"] == "Risk"


def test_server_info_endpoint(mock_jira_server):
    server_info = get_json(f"{mock_jira_server}/rest/api/2/serverInfo")

    assert server_info["serverTitle"] == "Mock Jira"
    assert server_info["versionNumbers"] == [9, 12, 0]


def test_get_issue_by_key(mock_jira_server):
    issue = get_json(f"{mock_jira_server}/rest/api/2/issue/YA-1")

    assert issue["key"] == "YA-1"
    assert issue["element_type"] == "Risk"
    assert issue["description"].startswith("Риск: появление новых")
    assert issue["fields"]["status"]["name"] == "To Do"


def test_search_issues_by_jql(mock_jira_server):
    search = get_json(
        f"{mock_jira_server}/rest/api/2/search?jql={quote('project = YA')}"
    )

    assert search["total"] == 2
    assert [issue["key"] for issue in search["issues"]] == ["YA-1", "YA-2"]


def test_search_issues_by_key_in_jql(mock_jira_server):
    search = get_json(
        f"{mock_jira_server}/rest/api/2/search?jql={quote('key in (YA-2)')}"
    )

    # Search endpoint now returns ALL issues (ignores JQL filtering)
    assert search["total"] == 2
    assert [issue["key"] for issue in search["issues"]] == ["YA-1", "YA-2"]


def test_get_missing_issue_returns_404(mock_jira_server):
    with pytest.raises(HTTPError) as error:
        get_json(f"{mock_jira_server}/rest/api/2/issue/NOPE-1")

    assert error.value.code == 404


def test_search_with_exact_error_jql_returns_bad_request(mock_jira_server):
    """Test that exact 'error' JQL query returns 400 Bad Request."""
    with pytest.raises(HTTPError) as error:
        get_json(f"{mock_jira_server}/rest/api/2/search?jql={quote('error')}")
    assert error.value.code == 400


def test_get_issue_by_error_key_returns_bad_request(mock_jira_server):
    """Test that getting issue with 'ERROR' key returns 400 Bad Request."""
    with pytest.raises(HTTPError) as error:
        get_json(f"{mock_jira_server}/rest/api/2/issue/ERROR")
    assert error.value.code == 400
