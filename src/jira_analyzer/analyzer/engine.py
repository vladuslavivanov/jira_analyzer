import importlib_resources
from typing import List, Dict, Any

import jira_analyzer.analyzer.core.llm.prompts as llm_prompts
from jira_analyzer.analyzer.core.llm.deepseek_client import send_prompt
from jira_analyzer.analyzer.core.llm.prompt_builder import build_prompt
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)

def run_analysis(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyzes a list of Jira issues using the LLM.
    
    Args:
        issues: List of dictionaries containing 'element type' and 'description'
        
    Returns:
        List of analysis results
    """
    results = []
    total = len(issues)
    
    for idx, issue in enumerate(issues, start=1):
        element_type = issue.get("element type")
        description = issue.get("description")
        
        logger.info(f"Processing issue {idx}/{total}: {element_type}")

        # Loading the system prompt from the package resources
        try:
            with (
                importlib_resources.files(llm_prompts)
                .joinpath("system_prompt.template")
                .open() as prompt_file
            ):
                prompt = build_prompt(element_type, description, prompt_file)
        except Exception as e:
            logger.error(f"Failed to build prompt for issue {idx}: {e}")
            results.append({
                "error": f"Prompt building error: {str(e)}",
                "input_element_type": element_type,
                "input_description": description,
            })
            continue

        try:
            analysis = send_prompt(prompt)
            # Add metadata for context
            analysis["input_element_type"] = element_type
            analysis["input_description"] = description
            results.append(analysis)
        except Exception as e:
            logger.error(f"Failed to process issue {idx} with LLM: {e}")
            results.append({
                "error": str(e),
                "input_element_type": element_type,
                "input_description": description,
            })

    return results