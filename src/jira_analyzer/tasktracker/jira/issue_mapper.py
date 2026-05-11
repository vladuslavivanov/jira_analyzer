from __future__ import annotations

from typing import Any


def jira_issue_to_analysis_input(issue: Any) -> dict[str, str]:
    raw_issue = getattr(issue, "raw", None)
    if isinstance(raw_issue, dict):
        element_type = raw_issue.get("element type")
        description = raw_issue.get("description")
        if element_type and description:
            return {
                "key": str(raw_issue.get("key", issue.key)),
                "jira_key": str(raw_issue.get("key", issue.key)),
                "element type": str(element_type),
                "description": str(description),
            }

    fields = issue.fields
    issue_type = getattr(getattr(fields, "issuetype", None), "name", "Task")
    summary = getattr(fields, "summary", "") or ""
    description = getattr(fields, "description", "") or ""

    text_parts = []
    if summary:
        text_parts.append(f"Summary: {summary}")
    if description:
        text_parts.append(f"Description: {description}")

    return {
        "key": issue.key,
        "element type": issue_type,
        "description": "\n\n".join(text_parts) or f"Jira issue {issue.key}",
        "jira_key": issue.key,
    }
