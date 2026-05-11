from __future__ import annotations

import argparse
import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8081
DEFAULT_DATA_FILE = (
    Path(__file__).resolve().parents[3] / "data" / "mock_jira_issues.json"
)


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


def filter_issues_by_jql(
    issues: dict[str, dict[str, Any]],
    jql: str,
) -> list[dict[str, Any]]:
    normalized_jql = " ".join(jql.strip().split())
    if not normalized_jql:
        return list(issues.values())

    clauses = re.split(r"\s+and\s+", normalized_jql, flags=re.IGNORECASE)
    matched = list(issues.values())
    for clause in clauses:
        matched = [issue for issue in matched if _matches_jql_clause(issue, clause)]
    return matched


def _matches_jql_clause(issue: dict[str, Any], clause: str) -> bool:
    clause = clause.strip()
    fields = issue.get("fields", {})

    in_match = re.fullmatch(
        r"(key|issuekey)\s+in\s+\(([^)]+)\)",
        clause,
        flags=re.IGNORECASE,
    )
    if in_match:
        keys = {
            item.strip().strip("'\"").upper()
            for item in in_match.group(2).split(",")
            if item.strip()
        }
        return issue.get("key", "").upper() in keys

    equals_pattern = (
        r"(key|issuekey|project|type|issuetype|status)\s*=\s*"
        r"('([^']+)'|\"([^\"]+)\"|[^\s]+)"
    )
    equals_match = re.fullmatch(equals_pattern, clause, flags=re.IGNORECASE)
    if equals_match:
        field_name = equals_match.group(1).lower()
        raw_value = (
            equals_match.group(3)
            or equals_match.group(4)
            or equals_match.group(2)
        )
        expected = raw_value.strip("'\"").lower()
        if field_name in {"key", "issuekey"}:
            actual = str(issue.get("key", "")).lower()
        elif field_name == "project":
            actual = str(fields.get("project", {}).get("key", "")).lower()
        elif field_name in {"type", "issuetype"}:
            actual = str(fields.get("issuetype", {}).get("name", "")).lower()
        else:
            actual = str(fields.get("status", {}).get("name", "")).lower()
        return actual == expected

    contains_match = re.fullmatch(
        r"(summary|description|text)\s*~\s*('([^']+)'|\"([^\"]+)\"|.+)",
        clause,
        flags=re.IGNORECASE,
    )
    if contains_match:
        field_name = contains_match.group(1).lower()
        raw_value = (
            contains_match.group(3)
            or contains_match.group(4)
            or contains_match.group(2)
        )
        needle = raw_value.strip("'\"").lower()
        if field_name == "summary":
            haystack = str(fields.get("summary", ""))
        elif field_name == "description":
            haystack = str(fields.get("description", ""))
        else:
            haystack = " ".join(
                [
                    str(fields.get("summary", "")),
                    str(fields.get("description", "")),
                    str(issue.get("description", "")),
                ]
            )
        return needle in haystack.lower()

    # Unsupported clauses are ignored by returning all issues for that clause.
    # This keeps the local mock permissive for development.
    return True


def make_handler(issues: dict[str, dict[str, Any]]) -> type[BaseHTTPRequestHandler]:
    class MockJiraHandler(BaseHTTPRequestHandler):
        server_version = "MockJira/0.1"

        def do_GET(self) -> None:
            parsed_url = urlparse(self.path)
            path_parts = [
                unquote(part) for part in parsed_url.path.strip("/").split("/")
            ]
            query_params = parse_qs(parsed_url.query)

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

            if self._is_search_path(path_parts):
                jql = query_params.get("jql", [""])[0]
                start_at = int(query_params.get("startAt", ["0"])[0])
                max_results = int(query_params.get("maxResults", ["50"])[0])
                self._send_search_results(jql, start_at, max_results)
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

        def do_POST(self) -> None:
            parsed_url = urlparse(self.path)
            path_parts = [
                unquote(part) for part in parsed_url.path.strip("/").split("/")
            ]

            if not self._is_search_path(path_parts):
                self._send_json(
                    {
                        "errorMessages": [
                            f"Unsupported mock Jira endpoint: {parsed_url.path}"
                        ],
                        "errors": {},
                    },
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            body = json.loads(raw_body) if raw_body else {}
            self._send_search_results(
                str(body.get("jql", "")),
                int(body.get("startAt", 0)),
                int(body.get("maxResults", 50)),
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
        def _is_search_path(path_parts: list[str]) -> bool:
            return (
                len(path_parts) == 4
                and path_parts[:2] == ["rest", "api"]
                and path_parts[2] in {"2", "3", "latest"}
                and path_parts[3] == "search"
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

        def _send_search_results(
            self,
            jql: str,
            start_at: int,
            max_results: int,
        ) -> None:
            matched = filter_issues_by_jql(issues, jql)
            paged = matched[start_at : start_at + max_results]
            self._send_json(
                {
                    "expand": "schema,names",
                    "startAt": start_at,
                    "maxResults": max_results,
                    "total": len(matched),
                    "issues": paged,
                }
            )

        def _send_json(
            self,
            body: dict[str, Any],
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
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


if __name__ == "__main__":
    main()
