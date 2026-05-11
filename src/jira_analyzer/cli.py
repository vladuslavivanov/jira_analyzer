import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from jira_analyzer.analyzer.engine import run_analysis
from jira_analyzer.app.output_handler import save_markdown_report, save_results
from jira_analyzer.tasktracker.jira import (
    JiraConnectionConfig,
    fetch_issue,
    jira_issue_to_analysis_input,
    search_issues,
)
from jira_analyzer.tasktracker.jira.jira_parser import load_issues
from jira_analyzer.utils.logger import setup_logger

# Constants for defaults
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent # ipkn-jira-ai-linter/jira_analyzer
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_INPUT_FILE = DEFAULT_DATA_DIR / "input.json"
DEFAULT_OUTPUT_FILE = DEFAULT_DATA_DIR / "output.json"

logger = setup_logger(__name__)

def setup_arg_parser() -> argparse.ArgumentParser:
    """
    Configures the command-line argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Jira AI Linter: Analyze Jira issues for quality using AI."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT_FILE,
        help="Path to input JSON file (default: data/input.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help="Path to output JSON file (default: data/output.json)",
    )
    parser.add_argument(
        "--jira-issue",
        "-j",
        help="Jira issue key to fetch and analyze, for example YA-1",
    )
    parser.add_argument(
        "--jql",
        help="JQL query to fetch and analyze multiple Jira issues.",
    )
    parser.add_argument(
        "--jira-server",
        help="Jira server URL. Can also be provided via JIRA_SERVER_URL.",
    )
    parser.add_argument(
        "--jira-username",
        help="Jira username. Can also be provided via JIRA_USERNAME.",
    )
    parser.add_argument(
        "--jira-token",
        help="Jira API token/password. Can also be provided via JIRA_API_TOKEN.",
    )
    parser.add_argument(
        "--jira-no-verify",
        action="store_true",
        help="Disable SSL certificate verification for Jira requests.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path for a Markdown analysis report.",
    )
    return parser


def load_issues_from_args(args: argparse.Namespace) -> list[dict]:
    if not args.jira_issue and not args.jql:
        return load_issues(str(args.input))

    config = JiraConnectionConfig(
        server=args.jira_server or os.getenv("JIRA_SERVER_URL", ""),
        username=args.jira_username or os.getenv("JIRA_USERNAME") or None,
        token=args.jira_token or os.getenv("JIRA_API_TOKEN") or None,
        verify_ssl=(
            False
            if args.jira_no_verify
            else os.getenv("JIRA_VERIFY_SSL", "true").lower()
            not in {"0", "false", "no"}
        ),
    )
    if not config.server:
        raise ValueError(
            "Jira server URL is required. Use --jira-server or JIRA_SERVER_URL."
        )

    if args.jql:
        return [
            jira_issue_to_analysis_input(issue)
            for issue in search_issues(args.jql, config)
        ]

    jira_issue = fetch_issue(args.jira_issue, config)
    return [jira_issue_to_analysis_input(jira_issue)]

def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI application.
    """
    parser = setup_arg_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    logger.info("Starting Jira AI Linter CLI")

    # 1. Load Issues
    try:
        issues = load_issues_from_args(args)
    except Exception as e:
        logger.error(f"Failed to load issues: {e}")
        return 1

    # 2. Run Analysis
    try:
        results = run_analysis(issues)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return 1

    # 3. Save Results
    try:
        save_results(results, str(args.output))
        logger.info(f"Results successfully saved to {args.output}")
        if args.markdown_output:
            save_markdown_report(results, str(args.markdown_output))
            logger.info(f"Markdown report successfully saved to {args.markdown_output}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        return 1

    logger.info("Process finished successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
