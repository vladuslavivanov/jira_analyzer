import json
from typing import Any, Dict, List

from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_issues(file_path: str) -> List[Dict[str, Any]]:
    """
    Загружает JSON-файл с массивом задач Jira.
    Каждый объект должен содержать поля "element_type" и "description".
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Input JSON must be an array of objects")
        for item in data:
            if "element_type" not in item or "description" not in item:
                raise ValueError(
                    "Each object must have 'element_type' and 'description' fields"
                )
        logger.info(f"Loaded {len(data)} issues from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load issues: {e}")
        raise
