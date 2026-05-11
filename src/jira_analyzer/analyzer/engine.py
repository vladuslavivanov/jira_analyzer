from importlib import resources as importlib_resources
from queue import Empty, Queue
from threading import Lock, Thread
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
    worker_count: int = 1,
) -> List[Dict[str, Any]]:
    """
    Analyzes a list of Jira issues using the LLM.
    
    Args:
        issues: List of dictionaries containing 'element type' and 'description'
        prompt_template: Optional legacy prompt template.
        prompt_config: Optional structured prompt configuration.
        worker_count: Number of parallel worker threads. Values below 1 become 1.
        
    Returns:
        List of analysis results
    """
    total = len(issues)
    if prompt_config is None and prompt_template is None:
        prompt_template = get_default_prompt_template()

    workers = max(1, int(worker_count))
    task_queue: Queue[tuple[int, Dict[str, Any]]] = Queue()
    result_items: list[tuple[int, Dict[str, Any]]] = []
    result_lock = Lock()

    for idx, issue in enumerate(issues, start=1):
        task_queue.put((idx, issue))

    def worker() -> None:
        while True:
            try:
                idx, issue = task_queue.get_nowait()
            except Empty:
                return

            try:
                result = _analyze_issue(
                    idx=idx,
                    total=total,
                    issue=issue,
                    prompt_template=prompt_template,
                    prompt_config=prompt_config,
                )
                with result_lock:
                    result_items.append((idx, result))
            finally:
                task_queue.task_done()

    threads = [
        Thread(target=worker, name=f"jira-analysis-worker-{index}", daemon=True)
        for index in range(1, min(workers, total or 1) + 1)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return [result for _, result in sorted(result_items, key=lambda item: item[0])]


def _analyze_issue(
    *,
    idx: int,
    total: int,
    issue: Dict[str, Any],
    prompt_template: str | None,
    prompt_config: AnalysisPromptConfig | None,
) -> Dict[str, Any]:
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
        return {
            "error": f"Prompt building error: {str(e)}",
            "key": issue.get("key"),
            "jira_key": issue.get("jira_key"),
            "input_element_type": element_type,
            "input_description": description,
        }

    try:
        from jira_analyzer.analyzer.core.llm.deepseek_client import send_prompt

        analysis = send_prompt(
            prompt,
            system_prompt=(
                prompt_config.system_prompt if prompt_config is not None else None
            ),
        )
        if issue.get("key"):
            analysis["key"] = issue["key"]
        if issue.get("jira_key"):
            analysis["jira_key"] = issue["jira_key"]
        analysis["input_element_type"] = element_type
        analysis["input_description"] = description
        return analysis
    except Exception as e:
        logger.error(f"Failed to process issue {idx} with LLM: {e}")
        return {
            "error": str(e),
            "key": issue.get("key"),
            "jira_key": issue.get("jira_key"),
            "input_element_type": element_type,
            "input_description": description,
        }


def get_default_analysis_prompt_config() -> AnalysisPromptConfig:
    return get_default_prompt_config()
