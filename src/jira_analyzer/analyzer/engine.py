from typing import Any, Dict, List, Optional

from jira_analyzer.analyzer.core.llm.prompt_builder import (
    AnalysisPromptConfig,
    get_default_prompt_config,
)
from jira_analyzer.analyzer.service import AnalysisService
from jira_analyzer.storage import AnalysisResultRepository


def run_analysis(
    issues: List[Dict[str, Any]],
    prompt_template: str | None = None,
    prompt_config: AnalysisPromptConfig | None = None,
    worker_count: int = 1,
    split_by_criterion: bool = False,
    llm_max_workers: int | None = None,
    repo: Optional[AnalysisResultRepository] = None,
) -> List[Dict[str, Any]]:
    """Analyze a list of Jira issues using the configured analysis service."""
    service = AnalysisService(
        prompt_template=prompt_template,
        prompt_config=prompt_config,
        worker_count=worker_count,
        llm_max_workers=llm_max_workers,
        split_by_criterion=split_by_criterion,
        repo=repo,
    )
    return service.analyze_issues(issues)


def get_default_analysis_prompt_config() -> AnalysisPromptConfig:
    return get_default_prompt_config()
