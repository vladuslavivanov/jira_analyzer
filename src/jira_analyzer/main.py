import argparse
import sys
from jira_parser import load_issues
from prompt_builder import build_prompt
from deepseek_client import send_prompt
from output_handler import save_results
from utils import setup_logger

logger = setup_logger(__name__)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze Jira issues using DeepSeek API"
    )
    parser.add_argument(
        "--input", "-i",
        default="data/input.json",
        help="Path to input JSON file (default: data/input.json)"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/output.json",
        help="Path to output JSON file (default: data/output.json)"
    )
    args = parser.parse_args()

    # Загрузка задач
    try:
        issues = load_issues(args.input)
    except Exception as e:
        logger.error(f"Exiting due to input error: {e}")
        sys.exit(1)

    results = []
    for idx, issue in enumerate(issues, start=1):
        element_type = issue["element type"]
        description = issue["description"]
        logger.info(f"Processing issue {idx}/{len(issues)}: {element_type}")

        prompt = build_prompt(element_type, description)
        try:
            analysis = send_prompt(prompt)
            # Добавляем исходные данные для прозрачности
            analysis["input_element_type"] = element_type
            analysis["input_description"] = description
            results.append(analysis)
        except Exception as e:
            logger.error(f"Failed to process issue {idx}: {e}")
            # Заглушка с ошибкой
            results.append({
                "error": str(e),
                "input_element_type": element_type,
                "input_description": description
            })

    # Сохранение результатов
    try:
        save_results(results, args.output)
    except Exception as e:
        logger.error(f"Exiting due to output error: {e}")
        sys.exit(1)

    logger.info("Processing completed successfully")

if __name__ == "__main__":
    main()