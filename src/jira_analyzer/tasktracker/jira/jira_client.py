from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass(frozen=True)
class JiraConnectionConfig:
    server: str
    username: str | None = None
    token: str | None = None
    verify_ssl: bool = True

    @classmethod
    def from_env(cls) -> "JiraConnectionConfig":
        server = os.getenv("JIRA_SERVER_URL")
        if not server:
            raise ValueError("JIRA_SERVER_URL is required to fetch issues from Jira")

        return cls(
            server=server,
            username=os.getenv("JIRA_USERNAME") or None,
            token=os.getenv("JIRA_API_TOKEN") or None,
            verify_ssl=os.getenv("JIRA_VERIFY_SSL", "true").lower() not in {
                "0",
                "false",
                "no",
            },
        )


class JiraTaskClient:
    def __init__(self, config: JiraConnectionConfig):
        try:
            from jira import JIRA
        except ImportError as error:
            raise RuntimeError(
                "Python package 'jira' is required for Jira integration. "
                "Install project dependencies with 'uv sync'."
            ) from error

        options = {"verify": config.verify_ssl}
        kwargs: dict[str, Any] = {}
        if config.username and config.token:
            kwargs["basic_auth"] = (config.username, config.token)
        elif config.token:
            kwargs["token_auth"] = config.token

        self._client = JIRA(server=config.server, options=options, **kwargs)
        self._server = config.server

    def get_issue(self, issue_key: str) -> Any:
        logger.info("Fetching Jira issue %s from %s", issue_key, self._server)
        return self._client.issue(issue_key)


def fetch_issue(issue_key: str, config: JiraConnectionConfig | None = None) -> Any:
    return JiraTaskClient(config or JiraConnectionConfig.from_env()).get_issue(issue_key)
