import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from jira_analyzer.storage.sqlite_repository import SqliteAnalysisResultRepository
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)


def save_results(results: List[Dict[str, Any]], output_path: str) -> None:
    """Save analysis results to JSON file or SQLite database."""
    if output_path.lower().endswith(".db"):
        self_path = Path(output_path)
        repository = SqliteAnalysisResultRepository(self_path)
        run_id = repository.save_results(results)
        logger.info(
            f"Saved {len(results)} results to SQLite database {output_path} (run_id={run_id})"
        )
        return

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(results)} results to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        raise


def build_markdown_report(results: List[Dict[str, Any]]) -> str:
    max_criteria_count = max(
        (len(_extract_criterion_scores(result)) for result in results),
        default=0,
    )
    summary_headers = ["#", "Issue", "Type"]
    summary_headers.extend(f"К{index}" for index in range(1, max_criteria_count + 1))
    if any("overall_score" in result for result in results):
        summary_headers.append("Score")
    if any("verdict" in result for result in results):
        summary_headers.append("Verdict")

    lines = [
        "# Jira Task Analysis Report",
        "",
        f"Analyzed issues: {len(results)}",
        "",
        "## Summary",
        "",
        _markdown_table_row(summary_headers),
        _markdown_table_row(["---"] * len(summary_headers)),
    ]

    for index, result in enumerate(results, start=1):
        issue_key = result.get("jira_key") or result.get("key") or f"Issue {index}"
        issue_type = result.get("input_element_type", "")
        row = [index, issue_key, issue_type]
        criterion_scores = _extract_criterion_scores(result)
        row.extend(
            criterion_scores[score_index] if score_index < len(criterion_scores) else ""
            for score_index in range(max_criteria_count)
        )
        if "overall_score" in result:
            row.append(result["overall_score"])
        elif "Score" in summary_headers:
            row.append("")
        if "verdict" in result:
            row.append(result["verdict"])
        elif "Verdict" in summary_headers:
            row.append("")
        lines.append(_markdown_table_row(row))

    lines.extend(["", "## Details", ""])

    zombie_tasks = [result for result in results if _is_zombie_task(result)]
    if zombie_tasks:
        lines.extend(["", "## Zombie Tasks", ""])
        lines.append(f"Found {len(zombie_tasks)} tasks not updated for 30+ days:")
        for result in zombie_tasks:
            issue_key = result.get("jira_key") or result.get("key") or "Unknown"
            lines.append(f"- {issue_key}")
        lines.append("")

    lines.extend(["", "## Issue Details", ""])

    for index, result in enumerate(results, start=1):
        issue_key = result.get("jira_key") or result.get("key") or f"Issue {index}"
        issue_type = result.get("input_element_type", "N/A")
        lines.extend(
            [
                f"### {index}. {issue_key}",
                "",
                f"- Type: {issue_type}",
            ]
        )
        status = result.get("status", "")
        if status:
            lines.append(f"- Status: {status}")
        updated_at = result.get("updated_at", "")
        if updated_at:
            lines.append(f"- Updated: {updated_at}")
            if _is_zombie_task(result):
                lines.append("- **Zombie Task**: Not updated for 30+ days")
        if "overall_score" in result:
            lines.append(f"- Score: {result['overall_score']}")
        if "verdict" in result:
            lines.append(f"- Verdict: {result['verdict']}")
        lines.append("")

        scores = _extract_criterion_scores(result)
        if scores:
            lines.extend(["#### Criteria Scores", ""])
            for score_index, value in enumerate(scores, start=1):
                lines.append(f"- К{score_index}: {value}")
            lines.append("")

        criteria = result.get("criteria")
        if isinstance(criteria, dict) and criteria:
            lines.extend(["#### Criteria Details", ""])
            for name, criterion_result in criteria.items():
                if not isinstance(criterion_result, dict):
                    continue
                title = criterion_result.get(
                    "title",
                    name.replace("_", " ").title(),
                )
                score = criterion_result.get("score", "N/A")
                scoring_system = criterion_result.get("scoring_system", "N/A")
                lines.append(f"- {title}: {score} ({scoring_system})")
                if criterion_result.get("review"):
                    lines.append(f"  {criterion_result['review']}")
            lines.append("")

        if "error" in result:
            lines.extend(["#### Error", "", str(result["error"]), ""])
        else:
            if result.get("overall_conclusion"):
                lines.extend(
                    [
                        "#### Overall Conclusion",
                        "",
                        str(result["overall_conclusion"]),
                        "",
                    ]
                )
            if result.get("diagnosis"):
                lines.extend(["#### Diagnosis", "", str(result["diagnosis"]), ""])
            if result.get("recommendations"):
                lines.extend(
                    ["#### Recommendations", "", str(result["recommendations"]), ""]
                )

        description = result.get("input_description")
        if description:
            lines.extend(
                [
                    "#### Original Description",
                    "",
                    "```",
                    str(description),
                    "```",
                    "",
                ]
            )

    return "\n".join(lines).strip() + "\n"


def save_markdown_report(results: List[Dict[str, Any]], output_path: str) -> None:
    try:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(build_markdown_report(results))
        logger.info(f"Saved Markdown report to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save Markdown report: {e}")
        raise


def _extract_criterion_scores(result: Dict[str, Any]) -> List[Any]:
    criteria = result.get("criteria")
    if isinstance(criteria, dict) and criteria:
        scores = []
        for criterion_result in criteria.values():
            if isinstance(criterion_result, dict) and "score" in criterion_result:
                scores.append(criterion_result["score"])
        if scores:
            return scores

    scores = result.get("criteria_scores")
    if isinstance(scores, dict) and scores:
        return list(scores.values())

    return []


def _markdown_table_row(values: List[Any]) -> str:
    return "| " + " | ".join(_escape_table_cell(value) for value in values) + " |"


def _escape_table_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _is_zombie_task(result: Dict[str, Any], days_threshold: int = 30) -> bool:
    updated_at_str = result.get("updated_at")
    if not updated_at_str:
        return False
    try:
        updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (now - updated_at) > timedelta(days=days_threshold)
    except (ValueError, TypeError):
        return False
