from importlib import resources as importlib_resources
from typing import Any, Dict, List

import jira_analyzer.analyzer.core.llm.prompts as llm_prompts
from jira_analyzer.analyzer.core.llm.prompt_builder import (
    AnalysisPromptConfig,
    build_prompt_from_template,
    build_structured_prompt,
    get_default_prompt_config,
)
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_default_prompt_template() -> str:
    with (
        importlib_resources.files(llm_prompts)
        .joinpath("system_prompt.template")
        .open(encoding="utf-8") as prompt_file
    ):
        return prompt_file.read()


def run_analysis(
    issues: List[Dict[str, Any]],
    prompt_template: str | None = None,
    prompt_config: AnalysisPromptConfig | None = None,
) -> List[Dict[str, Any]]:
    """
    Analyzes a list of Jira issues using the LLM.
    
    Args:
        issues: List of dictionaries containing 'element type' and 'description'
        
    Returns:
        List of analysis results
    """
    results = []
    total = len(issues)
    if prompt_config is None and prompt_template is None:
        prompt_template = get_default_prompt_template()
    
    for idx, issue in enumerate(issues, start=1):
        element_type = issue.get("element type")
        description = issue.get("description")
        
        logger.info(f"Processing issue {idx}/{total}: {element_type}")

        try:
            if prompt_config is not None:
                prompt = build_structured_prompt(
                    element_type,
                    description,
                    prompt_config,
                )
            else:
                prompt = build_prompt_from_template(
                    element_type,
                    description,
                    prompt_template or "",
                )
        except Exception as e:
            logger.error(f"Failed to build prompt for issue {idx}: {e}")
            results.append({
                "error": f"Prompt building error: {str(e)}",
                "key": issue.get("key"),
                "jira_key": issue.get("jira_key"),
                "input_element_type": element_type,
                "input_description": description,
            })
            continue

        try:
            from jira_analyzer.analyzer.core.llm.deepseek_client import send_prompt

            analysis = send_prompt(
                prompt,
                system_prompt=(
                    prompt_config.system_prompt if prompt_config is not None else None
                ),
            )
            # Add metadata for context
            if issue.get("key"):
                analysis["key"] = issue["key"]
            if issue.get("jira_key"):
                analysis["jira_key"] = issue["jira_key"]
            analysis["input_element_type"] = element_type
            analysis["input_description"] = description
            results.append(analysis)
        except Exception as e:
            logger.error(f"Failed to process issue {idx} with LLM: {e}")
            results.append({
                "error": str(e),
                "key": issue.get("key"),
                "jira_key": issue.get("jira_key"),
                "input_element_type": element_type,
                "input_description": description,
            })

    return results


def get_default_analysis_prompt_config() -> AnalysisPromptConfig:
    return get_default_prompt_config()
