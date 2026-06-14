import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from jira.exceptions import JIRAError

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
    """Jira API client with retry and error handling.

    Transient errors (rate limits, server errors, connection drops, timeouts)
    are retried with exponential backoff. Non-retryable errors (auth, bad
    request, not found, permission denied) are reported immediately with
    clear messages.
    """

    _MAX_RETRIES = 3

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
        self._logger = setup_logger(__name__)

    def get_issue(self, issue_key: str) -> Any:
        """Fetch a single Jira issue by key with retry for transient errors.

        Args:
            issue_key: Jira issue key (e.g. "PROJ-123")

        Returns:
            Jira issue object

        Raises:
            RuntimeError: Wraps all API errors with user-friendly descriptions.
        """
        self._logger.info("Fetching Jira issue %s from %s", issue_key, self._server)

        return self._call_with_retry(
            lambda: self._client.issue(issue_key),
            context=f"fetching issue {issue_key}",
        )

    def search_issues(self, jql: str, max_results: int = 50) -> list[Any]:
        """Search Jira issues with retry for transient errors.

        Args:
            jql: Jira Query Language string
            max_results: Maximum number of results to return

        Returns:
            List of Jira issue objects

        Raises:
            RuntimeError: Wraps all API errors with user-friendly descriptions.
        """
        self._logger.info(
            "Searching Jira issues from %s with JQL: %s", self._server, jql
        )

        return self._call_with_retry(
            lambda: list(self._client.search_issues(jql, maxResults=max_results)),
            context=f"searching issues with JQL '{jql}'",
        )

    def _call_with_retry(self, fn: callable, context: str) -> Any:
        """Execute a Jira API call with retry and error classification.

        Args:
            fn: The API call to execute.
            context: Human-readable description of the operation (for error messages).

        Returns:
            Result of the API call.

        Raises:
            RuntimeError: Wraps all errors with user-friendly descriptions.
        """
        last_exception = None

        for attempt in range(self._MAX_RETRIES):
            try:
                return fn()
            except JIRAError as error:
                status_code = error.status_code
                last_exception = error

                # Determine if this error is retryable
                if status_code in (429,) or (
                    status_code is not None and 500 <= status_code < 600
                ):
                    if attempt < self._MAX_RETRIES - 1:
                        wait_time = 2 ** attempt  # 1, 2, 4
                        self._logger.warning(
                            "Jira API transient error (attempt %d/%d) while %s: "
                            "HTTP %d. Retrying in %ds...",
                            attempt + 1,
                            self._MAX_RETRIES,
                            context,
                            status_code,
                            wait_time,
                        )
                        time.sleep(wait_time)
                    else:
                        self._logger.error(
                            "Jira API transient error — all %d retries exhausted "
                            "while %s: HTTP %d",
                            self._MAX_RETRIES,
                            context,
                            status_code,
                        )
                else:
                    # Non-retryable error — report immediately
                    self._raise_jira_error(error, context)
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.ConnectTimeout) as error:
                last_exception = error
                if attempt < self._MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    self._logger.warning(
                        "Jira connection error (attempt %d/%d) while %s: %s. "
                        "Retrying in %ds...",
                        attempt + 1,
                        self._MAX_RETRIES,
                        context,
                        error,
                        wait_time,
                    )
                    time.sleep(wait_time)
                else:
                    self._logger.error(
                        "Jira connection error — all %d retries exhausted "
                        "while %s: %s",
                        self._MAX_RETRIES,
                        context,
                        error,
                    )
            except requests.exceptions.Timeout as error:
                last_exception = error
                if attempt < self._MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    self._logger.warning(
                        "Jira request timeout (attempt %d/%d) while %s. "
                        "Retrying in %ds...",
                        attempt + 1,
                        self._MAX_RETRIES,
                        context,
                        wait_time,
                    )
                    time.sleep(wait_time)
                else:
                    self._logger.error(
                        "Jira request timeout — all %d retries exhausted while %s",
                        self._MAX_RETRIES,
                        context,
                    )
            except Exception as error:
                # Catch-all for unexpected errors - don't retry
                raise RuntimeError(
                    f"Unexpected error while {context}. "
                    f"Details: {error}"
                ) from error

        # All retries exhausted for retryable errors
        if isinstance(last_exception, JIRAError):
            status_code = last_exception.status_code
            if status_code == 429:
                raise RuntimeError(
                    f"Jira API rate limit exceeded while {context}. "
                    f"The server is receiving too many requests. "
                    f"Please wait and try again later."
                ) from last_exception
            elif status_code is not None and 500 <= status_code < 600:
                raise RuntimeError(
                    f"Jira server encountered an internal error (HTTP {status_code}) "
                    f"while {context}. The server may be temporarily unavailable. "
                    f"Please try again later."
                ) from last_exception
            else:
                # Fallback for any other JIRAError that slipped through
                raise RuntimeError(
                    f"Jira API error while {context}: {last_exception.text}"
                ) from last_exception
        elif isinstance(last_exception, (requests.exceptions.ConnectionError,
                                          requests.exceptions.ConnectTimeout)):
            raise RuntimeError(
                f"Failed to connect to Jira server while {context}. "
                f"Check that the server URL is correct and the server is running. "
                f"Details: {last_exception}"
            ) from last_exception
        elif isinstance(last_exception, requests.exceptions.Timeout):
            raise RuntimeError(
                f"Jira API request timed out while {context}. "
                f"The server may be slow or unreachable. "
                f"Please check your network connection and try again."
            ) from last_exception
        elif last_exception is not None:
            raise RuntimeError(
                f"Jira API request failed after {self._MAX_RETRIES} retries "
                f"while {context}: {last_exception}"
            ) from last_exception

        # Safety guard (should never be reached)
        raise RuntimeError(
            f"Jira API request failed after {self._MAX_RETRIES} retries "
            f"while {context} with no exception captured"
        )

    def _raise_jira_error(self, error: JIRAError, context: str) -> None:
        """Convert a non-retryable JIRAError into a descriptive RuntimeError."""
        status_code = error.status_code
        text = error.text or ""

        if status_code == 400:
            raise RuntimeError(
                f"Jira API request was invalid while {context}. "
                f"Check your JQL query or issue key for syntax errors. "
                f"Details: {text}"
            ) from error
        elif status_code == 401:
            raise RuntimeError(
                f"Jira authentication failed while {context}. "
                f"Check that your username and API token are correct. "
                f"Details: {text}"
            ) from error
        elif status_code == 403:
            raise RuntimeError(
                f"Jira access denied while {context}. "
                f"Your account may not have permission to access this resource. "
                f"Details: {text}"
            ) from error
        elif status_code == 404:
            raise RuntimeError(
                f"Jira resource not found while {context}. "
                f"The issue or endpoint does not exist. "
                f"Details: {text}"
            ) from error
        elif status_code == 409:
            raise RuntimeError(
                f"Jira API conflict while {context}. "
                f"Details: {text}"
            ) from error
        elif status_code == 422:
            raise RuntimeError(
                f"Jira API request was unprocessable while {context}. "
                f"Details: {text}"
            ) from error
        else:
            # Generic for any other non-retryable HTTP error
            raise RuntimeError(
                f"Jira API returned HTTP {status_code} while {context}. "
                f"Details: {text}"
            ) from error


def fetch_issue(issue_key: str, config: JiraConnectionConfig | None = None) -> Any:
    """Convenience function to fetch a single Jira issue.

    Args:
        issue_key: Jira issue key (e.g. "PROJ-123")
        config: Optional connection config (defaults to env vars)

    Returns:
        Jira issue object

    Raises:
        RuntimeError: On connection or API errors.
    """
    client = JiraTaskClient(config or JiraConnectionConfig.from_env())
    return client.get_issue(issue_key)


def search_issues(
    jql: str,
    config: JiraConnectionConfig | None = None,
    max_results: int = 50,
) -> list[Any]:
    """Convenience function to search Jira issues.

    Args:
        jql: Jira Query Language string
        config: Optional connection config (defaults to env vars)
        max_results: Maximum number of results to return

    Returns:
        List of Jira issue objects

    Raises:
        RuntimeError: On connection or API errors.
    """
    return JiraTaskClient(config or JiraConnectionConfig.from_env()).search_issues(
        jql,
        max_results=max_results,
    )
