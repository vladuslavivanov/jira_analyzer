import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from jira_analyzer.storage.sqlite_repository import SqliteAnalysisResultRepository
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)

# Default English translations for contexts without a language selector
_DEFAULT_TRANSLATIONS = None


def _get_default_translate() -> Callable[[str], str]:
    """Create a default translate function using English resource file."""
    global _DEFAULT_TRANSLATIONS
    if _DEFAULT_TRANSLATIONS is None:
        path = Path(__file__).resolve().parent.parent.parent.parent / "resources" / "translations" / "en.json"
        try:
            with open(path, encoding="utf-8") as f:
                _DEFAULT_TRANSLATIONS = json.load(f)
        except Exception:
            _DEFAULT_TRANSLATIONS = {}

    def _translate(key: str, **kwargs: Any) -> str:
        text = _DEFAULT_TRANSLATIONS.get(key, key)
        return text.format(**kwargs) if kwargs else text

    return _translate


@dataclass
class CriteriaInfo:
    """Structured information about evaluation criteria."""
    keys: List[str] = field(default_factory=list)
    metadata: Dict[str, Dict[str, str]] = field(default_factory=dict)
    titles: List[str] = field(default_factory=list)


@dataclass
class Statistics:
    """Calculated statistics for report generation."""
    total_scores: List[float] = field(default_factory=list)
    score_counts: List[int] = field(default_factory=list)


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


def build_markdown_report(
    results: List[Dict[str, Any]],
    t: Callable | None = None,
) -> str:
    """
    Generate a comprehensive Markdown report from analysis results.

    Args:
        results: List of analysis result dictionaries.
        t: Optional translation function. Falls back to English if not provided.

    Returns:
        Complete Markdown report as a string.
    """
    if t is None:
        t = _get_default_translate()

    if not results:
        return f"# {t('report_title')}\n\n{t('no_issues_analyzed')}\n"

    criteria_info = _collect_criteria_info(results)
    statistics = _calculate_statistics(results, criteria_info)

    summary_table = _build_summary_table(results, criteria_info, statistics, t)
    criteria_stats = _build_criteria_statistics_section(criteria_info, statistics, t)
    zombie_section = _build_zombie_tasks_section(results, t)
    issues_section = _build_issue_details_section(results, criteria_info, t)

    lines = [
        f"# {t('report_title')}",
        "",
        t("analyzed_issues_count", count=len(results)),
        "",
        f"## {t('summary_section')}",
        "",
        summary_table,
        "",
        criteria_stats,
        zombie_section,
        f"## {t('issue_details_section')}",
        "",
        issues_section,
    ]

    return "\n".join(lines).strip() + "\n"


def _collect_criteria_info(results: List[Dict[str, Any]]) -> CriteriaInfo:
    """Collect and structure criteria information from all analysis results."""
    criteria_keys: List[str] = []
    criteria_metadata: Dict[str, Dict[str, str]] = {}

    for result in results:
        criteria = result.get("criteria")
        if isinstance(criteria, dict):
            for key, criterion in criteria.items():
                if key not in criteria_keys:
                    criteria_keys.append(key)
                if key not in criteria_metadata and isinstance(criterion, dict):
                    criteria_metadata[key] = {
                        "title": str(
                            criterion.get("title", key.replace("_", " ").title())
                        ).strip(),
                        "description": str(criterion.get("description", "")).strip(),
                        "scoring_system": str(
                            criterion.get("scoring_system", "")
                        ).strip(),
                    }

        criteria_scores = result.get("criteria_scores")
        if isinstance(criteria_scores, dict):
            for key in criteria_scores.keys():
                if key not in criteria_keys:
                    criteria_keys.append(key)
                if key not in criteria_metadata:
                    criteria_metadata[key] = {
                        "title": key.replace("_", " ").title(),
                        "description": "",
                        "scoring_system": "",
                    }

    titles = [
        criteria_metadata.get(key, {}).get("title", key.replace("_", " ").title())
        for key in criteria_keys
    ]

    return CriteriaInfo(keys=criteria_keys, metadata=criteria_metadata, titles=titles)


def _calculate_statistics(
    results: List[Dict[str, Any]], criteria_info: CriteriaInfo
) -> Statistics:
    """Calculate score statistics across all analyzed issues."""
    total_scores: List[float] = [0.0] * len(criteria_info.keys)
    score_counts: List[int] = [0] * len(criteria_info.keys)

    for result in results:
        for score_index, criterion_key in enumerate(criteria_info.keys):
            score = _extract_criterion_score_by_key(result, criterion_key)
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                total_scores[score_index] += score
                score_counts[score_index] += 1

    return Statistics(
        total_scores=total_scores,
        score_counts=score_counts,
    )


def _build_summary_table(
    results: List[Dict[str, Any]],
    criteria_info: CriteriaInfo,
    statistics: Statistics,
    t: Callable,
) -> str:
    """Build the summary table with all issues and their scores."""
    summary_headers = [
        t("table_header_num"),
        t("table_header_issue"),
        t("table_header_type"),
    ]
    summary_headers.extend(criteria_info.titles)

    has_verdict = any("verdict" in result for result in results)

    if has_verdict:
        summary_headers.append(t("verdict"))

    lines = [
        _markdown_table_row(summary_headers),
        _markdown_table_row(["---"] * len(summary_headers)),
    ]

    for index, result in enumerate(results, start=1):
        issue_key = result.get("jira_key") or result.get("key") or f"Issue {index}"
        issue_type = result.get("input_element_type", "")
        row = [index, issue_key, issue_type]

        for criterion_key in criteria_info.keys:
            score = _extract_criterion_score_by_key(result, criterion_key)
            row.append(score if score is not None else "")

        if has_verdict:
            row.append(result.get("verdict", ""))

        lines.append(_markdown_table_row(row))

    lines.append(_build_average_row(criteria_info, statistics, has_verdict, t))

    return "\n".join(lines)


def _build_average_row(
    criteria_info: CriteriaInfo,
    statistics: Statistics,
    has_verdict: bool,
    t: Callable,
) -> str:
    """Build the averages row for the summary table."""
    average_row = ["", f"**{t('average_label')}**", ""]

    for score_index, count in enumerate(statistics.score_counts):
        if count:
            average = statistics.total_scores[score_index] / count
            average_row.append(
                str(int(average)) if average.is_integer() else f"{average:.2f}"
            )
        else:
            average_row.append("")

    if has_verdict:
        average_row.append("")

    return _markdown_table_row(average_row)


def _build_criteria_statistics_section(
    criteria_info: CriteriaInfo,
    statistics: Statistics,
    t: Callable,
) -> str:
    """Build the evaluation criteria statistics table."""
    if not criteria_info.keys:
        return ""

    lines = [
        f"## {t('evaluation_criteria_section')}",
        "",
        _markdown_table_row([
            t("table_header_name"),
            t("table_header_scoring"),
            t("table_header_average"),
            t("table_header_description"),
        ]),
        _markdown_table_row(["---", "---", "---", "---"]),
    ]

    for key in criteria_info.keys:
        index = criteria_info.keys.index(key)
        count = statistics.score_counts[index]

        if count > 0:
            avg = statistics.total_scores[index] / count
            avg_str = f"{avg:.2f}"
        else:
            avg_str = ""

        info = criteria_info.metadata.get(key, {})
        name = info.get("title", key.replace("_", " ").title())
        scoring = info.get("scoring_system", "")
        description = info.get("description", "")

        lines.append(_markdown_table_row([name, scoring, avg_str, description]))

    return "\n".join(lines) + "\n"


def _build_zombie_tasks_section(
    results: List[Dict[str, Any]],
    t: Callable,
) -> str:
    """Build the zombie tasks section for issues not updated recently."""
    zombie_tasks = [result for result in results if _is_zombie_task(result)]

    if not zombie_tasks:
        return ""

    lines = [
        f"## {t('zombie_tasks_section')}",
        "",
        t("zombie_tasks_found", count=len(zombie_tasks)),
    ]

    for result in zombie_tasks:
        issue_key = result.get("jira_key") or result.get("key") or t("na_value")
        lines.append(f"- {issue_key}")

    return "\n".join(lines) + "\n"


def _build_issue_details_section(
    results: List[Dict[str, Any]],
    criteria_info: CriteriaInfo,
    t: Callable,
) -> str:
    """Build detailed information for each analyzed issue."""
    lines = []

    for index, result in enumerate(results, start=1):
        issue_key = result.get("jira_key") or result.get("key") or f"Issue {index}"
        issue_type = result.get("input_element_type", t("na_value"))

        lines.extend([
            f"### {index}. {issue_key}",
            "",
            f"- {t('table_header_type')}: {issue_type}",
        ])

        status = result.get("status", "")
        if status:
            lines.append(f"- {t('status')}: {status}")

        updated_at = result.get("updated_at", "")
        if updated_at:
            lines.append(f"- {t('updated_label')}: {updated_at}")
            if _is_zombie_task(result):
                lines.append(f"- **{t('zombie_task_label')}**: {t('zombie_task_not_updated')}")

        if "verdict" in result:
            lines.append(f"- {t('verdict')}: {result['verdict']}")

        lines.append("")
        lines.extend(_build_issue_criteria_details(result, criteria_info, t))
        lines.extend(_build_issue_conclusion_section(result, t))
        lines.extend(_build_issue_description_section(result, t))

    return "\n".join(lines)


def _build_issue_criteria_details(
    result: Dict[str, Any],
    criteria_info: CriteriaInfo,
    t: Callable,
) -> List[str]:
    """Build criteria details for a single issue."""
    criteria = result.get("criteria") or result.get('analysis', {}).get("criteria", {})

    if not isinstance(criteria, dict) or not criteria:
        return []

    lines = [
        f"#### {t('criteria_details_section')}",
        "",
        _markdown_table_row([
            t("table_header_criterion"),
            t("score"),
            t("review"),
            t("recommendations"),
        ]),
        _markdown_table_row(["---", "---", "---", "---"]),
    ]

    for criterion_key in criteria_info.keys:
        criterion_result = criteria.get(criterion_key, {})

        if not isinstance(criterion_result, dict):
            continue

        title = criterion_result.get(
            "title",
            criterion_key.replace("_", " ").title(),
        )
        score = criterion_result.get("score", t("na_value"))
        review = criterion_result.get("review", "")
        recs = criterion_result.get("recommendations", [])

        if isinstance(recs, list):
            recommendation = "  ".join(
                [f"{i+1}. {r.strip()}" for i, r in enumerate(recs) if r.strip()]
            )
        else:
            recommendation = str(recs) if recs else ""

        lines.append(_markdown_table_row([title, score, review, recommendation]))

    return lines + [""]


def _build_issue_conclusion_section(
    result: Dict[str, Any],
    t: Callable,
) -> List[str]:
    """Build conclusion and diagnosis sections for a single issue."""
    lines = []

    if "error" in result:
        lines.extend([
            f"#### {t('error_section')}",
            "",
            str(result["error"]),
            "",
        ])
    else:
        conclusion = (
            result.get("overall_conclusion") or
            result.get('analysis', {}).get("overall_conclusion", '')
        )
        if conclusion:
            lines.extend([
                f"#### {t('overall_conclusion')}",
                "",
                str(conclusion),
                "",
            ])

        diagnosis = (
            result.get("diagnosis") or
            result.get('analysis', {}).get("diagnosis", '')
        )
        if diagnosis:
            lines.extend([
                f"#### {t('diagnosis')}",
                "",
                str(diagnosis),
                "",
            ])

    return lines


def _build_issue_description_section(
    result: Dict[str, Any],
    t: Callable,
) -> List[str]:
    """Build original description section for a single issue."""
    description = result.get("input_description")

    if not description:
        return []

    return [
        f"#### {t('original_description')}",
        "",
        "```",
        str(description),
        "```",
        "",
    ]


def _extract_criterion_score_by_key(
    result: Dict[str, Any], criterion_key: str
) -> Any | None:
    """Extract score for a specific criterion from a result."""
    criteria = result.get("criteria")
    if isinstance(criteria, dict):
        criterion_result = criteria.get(criterion_key)
        if isinstance(criterion_result, dict) and "score" in criterion_result:
            return criterion_result["score"]

    criteria_scores = result.get("criteria_scores")
    if isinstance(criteria_scores, dict) and criterion_key in criteria_scores:
        return criteria_scores[criterion_key]

    return None


def save_markdown_report(
    results: List[Dict[str, Any]],
    output_path: str,
    t: Callable | None = None,
) -> None:
    """Save the generated Markdown report to a file.

    Args:
        results: List of analysis result dictionaries.
        output_path: File path where the report should be saved.
        t: Optional translation function. Falls back to English if not provided.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(build_markdown_report(results, t=t))
        logger.info(f"Saved Markdown report to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save Markdown report: {e}")
        raise


def _extract_criterion_scores(result: Dict[str, Any]) -> List[Any]:
    """Extract all criterion scores from a result dictionary."""
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
    """Format a list of values as a Markdown table row."""
    return "| " + " | ".join(_escape_table_cell(value) for value in values) + " |"


def _escape_table_cell(value: Any) -> str:
    """Escape special characters for Markdown table cell compatibility."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _is_zombie_task(result: Dict[str, Any], days_threshold: int = 30) -> bool:
    """Determine if a task has not been updated for a specified period."""
    updated_at_str = result.get("updated_at")
    if not updated_at_str:
        return False

    try:
        updated_at = datetime.fromisoformat(
            updated_at_str.replace('Z', '+03:00') if 'Z' in updated_at_str else updated_at_str
        )
        now = datetime.now(timezone(timedelta(hours=3)))
        return (now - updated_at) > timedelta(days=days_threshold)
    except (ValueError, TypeError):
        return False
