from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8081
DEFAULT_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "mock_jira_issues.json"


def load_issues(path: Path = DEFAULT_DATA_FILE) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        issues = json.load(file)

    if not isinstance(issues, list):
        raise ValueError("Mock Jira data file must contain a JSON array")

    result: dict[str, dict[str, Any]] = {}
    for issue in issues:
        if not isinstance(issue, dict) or not isinstance(issue.get("key"), str):
            raise ValueError("Each mock Jira issue must be an object with a string key")
        result[issue["key"].upper()] = normalize_issue(issue)
    return result


def normalize_issue(issue: dict[str, Any]) -> dict[str, Any]:
    if "fields" in issue:
        return issue

    issue_key = issue["key"]
    element_type = issue.get("element type", "Task")
    description = issue.get("description", "")
    project_key = issue_key.split("-", maxsplit=1)[0]

    return {
        "expand": "renderedFields,names,schema,operations,editmeta,changelog",
        "id": issue.get("id", issue_key.replace("-", "")),
        "self": f"http://127.0.0.1:8081/rest/api/2/issue/{issue_key}",
        "key": issue_key,
        "element type": element_type,
        "description": description,
        "fields": {
            "summary": description,
            "description": description,
            "issuetype": {
                "self": "http://127.0.0.1:8081/rest/api/2/issuetype/10001",
                "id": "10001",
                "description": element_type,
                "name": element_type,
                "subtask": False,
            },
            "project": {
                "self": f"http://127.0.0.1:8081/rest/api/2/project/{project_key}",
                "id": "10000",
                "key": project_key,
                "name": project_key,
                "projectTypeKey": "software",
            },
            "status": {
                "self": "http://127.0.0.1:8081/rest/api/2/status/10000",
                "description": "Mock issue status",
                "name": "To Do",
                "id": "10000",
                "statusCategory": {
                    "id": 2,
                    "key": "new",
                    "colorName": "blue-gray",
                    "name": "To Do",
                },
            },
            "priority": {
                "self": "http://127.0.0.1:8081/rest/api/2/priority/3",
                "id": "3",
                "name": "Medium",
            },
            "labels": ["mock"],
        },
    }


def make_handler(issues: dict[str, dict[str, Any]]) -> type[BaseHTTPRequestHandler]:
    class MockJiraHandler(BaseHTTPRequestHandler):
        server_version = "MockJira/0.1"

        def do_GET(self) -> None:
            parsed_url = urlparse(self.path)
            path_parts = [unquote(part) for part in parsed_url.path.strip("/").split("/")]

            if self._is_server_info_path(path_parts):
                self._send_json(
                    {
                        "baseUrl": f"http://{self.headers.get('Host', 'localhost')}",
                        "version": "9.12.0",
                        "versionNumbers": [9, 12, 0],
                        "deploymentType": "Server",
                        "buildNumber": 912000,
                        "serverTitle": "Mock Jira",
                    }
                )
                return

            issue_key = self._extract_issue_key(path_parts)
            if issue_key is not None:
                issue = issues.get(issue_key.upper())
                if issue is None:
                    self._send_json(
                        {
                            "errorMessages": [
                                "Issue does not exist or you do not have permission "
                                f"to see it: {issue_key}"
                            ],
                            "errors": {},
                        },
                        status=HTTPStatus.NOT_FOUND,
                    )
                    return
                self._send_json(issue)
                return

            if self._is_myself_path(path_parts):
                self._send_json(
                    {
                        "self": (
                            f"http://{self.headers.get('Host', 'localhost')}"
                            "/rest/api/2/user?username=mock-user"
                        ),
                        "name": "mock-user",
                        "key": "mock-user",
                        "displayName": "Mock Jira User",
                        "active": True,
                    }
                )
                return

            self._send_json(
                {
                    "errorMessages": [
                        f"Unsupported mock Jira endpoint: {parsed_url.path}"
                    ],
                    "errors": {},
                },
                status=HTTPStatus.NOT_FOUND,
            )

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        @staticmethod
        def _is_server_info_path(path_parts: list[str]) -> bool:
            return (
                len(path_parts) == 4
                and path_parts[:2] == ["rest", "api"]
                and path_parts[2] in {"2", "3", "latest"}
                and path_parts[3] == "serverInfo"
            )

        @staticmethod
        def _is_myself_path(path_parts: list[str]) -> bool:
            return (
                len(path_parts) == 4
                and path_parts[:2] == ["rest", "api"]
                and path_parts[2] in {"2", "3", "latest"}
                and path_parts[3] == "myself"
            )

        @staticmethod
        def _extract_issue_key(path_parts: list[str]) -> str | None:
            if (
                len(path_parts) >= 5
                and path_parts[:2] == ["rest", "api"]
                and path_parts[2] in {"2", "3", "latest"}
                and path_parts[3] == "issue"
            ):
                return path_parts[4]
            return None

        def _send_json(self, body: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return MockJiraHandler


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    data_file: Path = DEFAULT_DATA_FILE,
) -> ThreadingHTTPServer:
    issues = load_issues(data_file)
    return ThreadingHTTPServer((host, port), make_handler(issues))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local mock Jira REST API server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-file", type=Path, default=DEFAULT_DATA_FILE)
    args = parser.parse_args()

    server = create_server(args.host, args.port, args.data_file)
    print(f"Mock Jira is running on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mock Jira")
    finally:
        server.server_close()
