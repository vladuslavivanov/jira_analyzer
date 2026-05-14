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
    all_criteria_keys: List[str] = []
    criteria_info: Dict[str, Dict[str, str]] = {}

    for result in results:
        criteria = result.get("criteria")
        if isinstance(criteria, dict):
            for key, criterion in criteria.items():
                if key not in all_criteria_keys:
                    all_criteria_keys.append(key)
                if key not in criteria_info and isinstance(criterion, dict):
                    criteria_info[key] = {
                        "title": str(
                            criterion.get("title", key.replace("_", " ").title())
                        ).strip(),
                        "description": str(criterion.get("description", "")).strip(),
                        "scoring_system": str(
                            criterion.get("scoring_system", ""
                        )).strip(),
                    }

        criteria_scores = result.get("criteria_scores")
        if isinstance(criteria_scores, dict):
            for key in criteria_scores.keys():
                if key not in all_criteria_keys:
                    all_criteria_keys.append(key)
                if key not in criteria_info:
                    criteria_info[key] = {
                        "title": key.replace("_", " ").title(),
                        "description": "",
                        "scoring_system": "",
                    }

    summary_headers = ["#", "Issue", "Type"]
    summary_headers.extend(
        criteria_info.get(key, {}).get("title", key.replace("_", " ").title())
        for key in all_criteria_keys
    )
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

    total_scores: List[float] = [0.0] * len(all_criteria_keys)
    score_counts: List[int] = [0] * len(all_criteria_keys)
    total_overall_score = 0.0
    overall_score_count = 0

    for index, result in enumerate(results, start=1):
        issue_key = result.get("jira_key") or result.get("key") or f"Issue {index}"
        issue_type = result.get("input_element_type", "")
        row = [index, issue_key, issue_type]

        for score_index, criterion_key in enumerate(all_criteria_keys):
            score = _extract_criterion_score_by_key(result, criterion_key)
            row.append(score if score is not None else "")
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                total_scores[score_index] += score
                score_counts[score_index] += 1

        if "overall_score" in result:
            overall_score = result["overall_score"]
            row.append(overall_score)
            if isinstance(overall_score, (int, float)) and not isinstance(
                overall_score, bool
            ):
                total_overall_score += overall_score
                overall_score_count += 1
        elif "Score" in summary_headers:
            row.append("")

        if "verdict" in result:
            row.append(result["verdict"])
        elif "Verdict" in summary_headers:
            row.append("")

        lines.append(_markdown_table_row(row))

    if results and all_criteria_keys:
        average_row = ["", "**Average**", ""]
        for score_index, count in enumerate(score_counts):
            if count:
                average = total_scores[score_index] / count
                average_row.append(
                    str(int(average)) if average.is_integer() else f"{average:.2f}"
                )
            else:
                average_row.append("")

        if "Score" in summary_headers:
            average_row.append(
                str(int(total_overall_score / overall_score_count))
                if overall_score_count and (total_overall_score / overall_score_count).is_integer()
                else f"{total_overall_score / overall_score_count:.2f}"
                if overall_score_count
                else ""
            )
        if "Verdict" in summary_headers:
            average_row.append("")

    # Criteria Statistics Table
    if all_criteria_keys:
        lines.extend(["", "## Criteria Statistics", "",])
        lines.append(_markdown_table_row(["Criterion", "Average Score", "Scoring System"]))
        lines.append(_markdown_table_row(["---", "---", "---"]))
        for key, count in zip(all_criteria_keys, score_counts):
            if count > 0:
                avg = total_scores[all_criteria_keys.index(key)] / count
                scoring = criteria_info.get(key, {}).get("scoring_system", "")
                title = criteria_info.get(key, {}).get("title", key.replace("_", " ").title())
                lines.append(_markdown_table_row([title, f"{avg:.2f}", scoring]))
        lines.append("")

    if criteria_info:
        lines.extend(["", "## Evaluation Criteria", ""])
        lines.append(_markdown_table_row(["Criterion", "Scoring", "Description"]))
        lines.append(_markdown_table_row(["---", "---", "---"]))
        for key in all_criteria_keys:
            info = criteria_info.get(key, {})
            lines.append(
                _markdown_table_row(
                    [
                        info.get("title", key.replace("_", " ").title()),
                        info.get("scoring_system", ""),
                        info.get("description", ""),
                    ]
                )
            )
        lines.append("")

    zombie_tasks = [result for result in results if _is_zombie_task(result)]
    if zombie_tasks:
        lines.extend(["", "## Zombie Tasks", "",])
        lines.append(f"Found {len(zombie_tasks)} tasks not updated for 30+ days:")
        for result in zombie_tasks:
            issue_key = result.get("jira_key") or result.get("key") or "Unknown"
            lines.append(f"- {issue_key}")
        lines.append("")

    lines.extend(["", "## Issue Details", "",])

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
        if "total_score" in result or 'analysis' in result and 'total_score' in result.get('analysis', {}):
            score = result.get('total_score') or result.get('analysis', {}).get('total_score', '')
            lines.append(f"- Score: {score}")
        if "verdict" in result:
            lines.append(f"- Verdict: {result['verdict']}")
        lines.append("")

        criteria = result.get("criteria") or (result.get('analysis', {}) or {}).get("criteria", {})
        if isinstance(criteria, dict) and criteria:
            lines.extend(["#### Criteria Details", "",])
            lines.append(
                _markdown_table_row(
                    ["Criterion", "Score", "Review", "Recommendations"]
                )
            )
            lines.append(_markdown_table_row(["---", "---", "---", "---"]))
            for key in all_criteria_keys:
                criterion_result = criteria.get(key, {})
                if not isinstance(criterion_result, dict):
                    continue
                title = criterion_result.get(
                    "title",
                    key.replace("_", " ").title(),
                )
                score = criterion_result.get("score", "N/A")
                review = criterion_result.get("review", "")
                recs = criterion_result.get("recommendations", [])
                if isinstance(recs, list):
                    recommendation = " ".join([f"{r.strip()}" for r in recs if r.strip()])
                else:
                    recommendation = str(recs) if recs else ""
                lines.append(
                    _markdown_table_row([title, score, review, recommendation])
                )
            lines.append("\n")

        if "error" in result:
            lines.extend(["#### Error", "", str(result["error"]), "",])
        else:
            conclusion = result.get("overall_conclusion") or result.get('analysis', {}).get("overall_conclusion", '')
            if conclusion:
                lines.extend(
                    [
                        "#### Overall Conclusion",
                        "",
                        str(conclusion),
                        "",
                    ]
                )
            diagnosis = result.get("diagnosis") or result.get('analysis', {}).get("diagnosis", '')
            if diagnosis:
                lines.extend(["#### Diagnosis", "", str(diagnosis), "",])

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


def _extract_criterion_score_by_key(
    result: Dict[str, Any], criterion_key: str
) -> Any | None:
    criteria = result.get("criteria")
    if isinstance(criteria, dict):
        criterion_result = criteria.get(criterion_key)
        if isinstance(criterion_result, dict) and "score" in criterion_result:
            return criterion_result["score"]

    criteria_scores = result.get("criteria_scores")
    if isinstance(criteria_scores, dict) and criterion_key in criteria_scores:
        return criteria_scores[criterion_key]

    return None


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
