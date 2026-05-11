import json
from typing import Any, Dict, List

from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)


def save_results(results: List[Dict[str, Any]], output_path: str) -> None:
    """Сохраняет список результатов в JSON-файл."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(results)} results to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        raise


def build_markdown_report(results: List[Dict[str, Any]]) -> str:
    lines = [
        "# Jira Task Analysis Report",
        "",
        f"Analyzed issues: {len(results)}",
        "",
        "## Summary",
        "",
        "| # | Issue | Type | Score | Verdict |",
        "|---|---|---|---|---|",
    ]

    for index, result in enumerate(results, start=1):
        issue_key = result.get("jira_key") or result.get("key") or f"Issue {index}"
        issue_type = result.get("input_element_type", "N/A")
        score = result.get("overall_score", "N/A")
        verdict = result.get("verdict", "N/A")
        lines.append(
            "| "
            f"{index} | {_escape_table_cell(issue_key)} | "
            f"{_escape_table_cell(issue_type)} | {_escape_table_cell(score)} | "
            f"{_escape_table_cell(verdict)} |"
        )

    lines.extend(["", "## Details", ""])

    for index, result in enumerate(results, start=1):
        issue_key = result.get("jira_key") or result.get("key") or f"Issue {index}"
        issue_type = result.get("input_element_type", "N/A")
        lines.extend(
            [
                f"### {index}. {issue_key}",
                "",
                f"- Type: {issue_type}",
                f"- Score: {result.get('overall_score', 'N/A')}",
                f"- Verdict: {result.get('verdict', 'N/A')}",
                "",
            ]
        )

        scores = result.get("criteria_scores")
        if isinstance(scores, dict) and scores:
            lines.extend(["#### Criteria Scores", ""])
            for name, value in scores.items():
                lines.append(f"- {name.replace('_', ' ').title()}: {value}")
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
            lines.extend(
                [
                    "#### Diagnosis",
                    "",
                    str(result.get("diagnosis", "No diagnosis available")),
                    "",
                    "#### Recommendations",
                    "",
                    str(result.get("recommendations", "No recommendations available")),
                    "",
                ]
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


def _escape_table_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
