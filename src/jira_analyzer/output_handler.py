import json
from typing import List, Dict, Any
from utils import setup_logger

logger = setup_logger(__name__)

def save_results(results: List[Dict[str, Any]], output_path: str) -> None:
    """Сохраняет список результатов в JSON-файл."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(results)} results to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        raise