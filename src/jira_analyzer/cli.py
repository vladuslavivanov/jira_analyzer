import argparse
import sys
from pathlib import Path
from typing import List, Optional

from jira_analyzer.analyzer.engine import run_analysis
from jira_analyzer.app.output_handler import save_results
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
        help=f"Path to input JSON file (default: data/input.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Path to output JSON file (default: data/output.json)",
    )
    return parser

def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI application.
    """
    parser = setup_arg_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    logger.info("Starting Jira AI Linter CLI")

    # 1. Load Issues
    try:
        issues = load_issues(str(args.input))
    except Exception as e:
        logger.error(f"Failed to load issues from {args.input}: {e}")
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
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        return 1

    logger.info("Process finished successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())