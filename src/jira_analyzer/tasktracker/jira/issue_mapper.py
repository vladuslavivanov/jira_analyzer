from typing import Any


def _extract_assignee(assignee_field: Any) -> str:
    """Extract a displayable assignee name from a Jira assignee field."""
    if assignee_field is None:
        return ""
    display_name = getattr(assignee_field, "displayName", None)
    if display_name:
        return str(display_name)
    name = getattr(assignee_field, "name", None)
    if name:
        return str(name)
    return str(assignee_field) if assignee_field else ""


def _extract_raw_assignee(raw_issue: dict) -> str:
    """Extract assignee from a raw Jira issue dict."""
    assignee = raw_issue.get("assignee")
    if assignee is None:
        return ""
    if isinstance(assignee, dict):
        return assignee.get("displayName") or assignee.get("name") or ""
    return str(assignee) if assignee else ""


def jira_issue_to_analysis_input(issue: Any) -> dict[str, str]:
    raw_issue = getattr(issue, "raw", None)
    if isinstance(raw_issue, dict):
        element_type = raw_issue.get("element_type")
        description = raw_issue.get("description")
        if element_type and description:
            result = {
                "key": str(raw_issue.get("key", issue.key)),
                "jira_key": str(raw_issue.get("key", issue.key)),
                "element_type": str(element_type),
                "description": str(description),
                "title": str(raw_issue.get("summary") or raw_issue.get("title") or ""),
                "assignee": _extract_raw_assignee(raw_issue),
                "created_at": str(raw_issue.get("created") or raw_issue.get("created_at") or ""),
            }
            status = raw_issue.get("status")
            if status:
                if isinstance(status, dict):
                    result["status"] = str(status.get("name", ""))
                else:
                    result["status"] = str(status)
            return result

    fields = issue.fields
    issue_type = getattr(getattr(fields, "issuetype", None), "name", "Task")
    summary = getattr(fields, "summary", "") or ""
    description = getattr(fields, "description", "") or ""
    status = getattr(getattr(fields, "status", None), "name", "Unknown")
    updated_at = getattr(fields, "updated", "")

    text_parts = []
    if summary:
        text_parts.append(f"Summary: {summary}")
    if description:
        text_parts.append(f"Description: {description}")

    return {
        "key": issue.key,
        "element_type": issue_type,
        "description": "\n\n".join(text_parts) or f"Jira issue {issue.key}",
        "jira_key": issue.key,
        "status": status,
        "updated_at": updated_at,
        "title": summary,
        "assignee": _extract_assignee(getattr(fields, "assignee", None)),
        "created_at": str(getattr(fields, "created", "") or ""),
    }
