import json
import re
from datetime import datetime, timedelta, timezone
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any, Dict, List

from jira_analyzer.analyzer.core.llm.client import LLMClient
from jira_analyzer.analyzer.core.llm.prompt_builder import (
    AnalysisPromptConfig,
    build_prompt_from_template,
    build_structured_prompt,
    get_default_prompt_config,
)
from jira_analyzer.analyzer.core.llm.provider import LLMProvider
from jira_analyzer.app.output_handler import build_markdown_report
from jira_analyzer.tasktracker.jira import JiraConnectionConfig
from jira_analyzer.tasktracker.repository import (
    JiraTasksRepository,
    JsonFileTasksRepository,
    TasksRepository,
)
from jira_analyzer.storage import AnalysisResultRepository
import asyncio
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnalysisService:
    """Orchestrates Jira issue analysis requests, task acquisition, and reporting."""

    def __init__(
        self,
        prompt_template: str | None = None,
        prompt_config: AnalysisPromptConfig | None = None,
        worker_count: int = 1,
        llm_max_workers: int | None = None,
        llm_provider: LLMProvider | None = None,
        split_by_criterion: bool = False,
        task_repository: TasksRepository | None = None,
        repo: AnalysisResultRepository | None = None,
    ):
        self.prompt_template = prompt_template
        self.prompt_config = prompt_config
        self.worker_count = max(1, int(worker_count))
        self.split_by_criterion = split_by_criterion
        self.task_repository = task_repository
        self.repo = repo

        if self.prompt_config is None and self.prompt_template is None:
            self.prompt_config = get_default_prompt_config()

        provider = llm_provider or self._resolve_default_provider()
        self.llm_client = LLMClient(
            provider=provider,
            max_workers=llm_max_workers or self.worker_count,
        )

    def _resolve_task_repository(
        self,
        jira_config: JiraConnectionConfig | None = None,
    ) -> TasksRepository:
        if self.task_repository is not None:
            return self.task_repository

        if jira_config is not None:
            return JiraTasksRepository(jira_config)

        return JsonFileTasksRepository()

    def analyze_task(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        return self._analyze_issue(idx=1, total=1, issue=issue)

    def analyze_jql(
        self,
        jql: str,
        jira_config: JiraConnectionConfig | None = None,
        max_results: int = 50,
        exclude_closed: bool = True,
    ) -> List[Dict[str, Any]]:
        try:
            repository = self._resolve_task_repository(jira_config=jira_config)
            issues = repository.search_tasks(jql=jql, max_results=max_results)
            if exclude_closed:
                issues = [issue for issue in issues if not self._is_closed_status(issue)]
            return self.analyze_issues(issues)
        except ValueError as e:
            return [{"error": str(e)}]
        except Exception as e:
            return [{"error": f"Unexpected error during JQL analysis: {str(e)}"}]

    def _is_closed_status(self, issue: Dict[str, Any]) -> bool:
        status = issue.get("status", "").lower()
        closed_statuses = {"closed", "done", "resolved", "cancelled"}
        return status in closed_statuses

    def is_zombie_task(self, issue: Dict[str, Any], days_threshold: int = 30) -> bool:
        updated_at_str = issue.get("updated_at")
        if not updated_at_str:
            return False
        try:
            updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return (now - updated_at) > timedelta(days=days_threshold)
        except (ValueError, TypeError):
            return False

    def analyze_dataset(self, path: str) -> List[Dict[str, Any]]:
        try:
            repository = self._resolve_task_repository()
            issues = repository.load_dataset(path)
            return self.analyze_issues(issues)
        except ValueError as e:
            return [{"error": str(e)}]
        except Exception as e:
            return [{"error": f"Unexpected error during dataset analysis: {str(e)}"}]

    def generate_report(self, results: List[Dict[str, Any]], format: str = "json") -> str:
        if format == "markdown":
            return build_markdown_report(results)
        return json.dumps(results, ensure_ascii=False, indent=2)

    def _resolve_default_provider(self) -> LLMProvider:
        import importlib

        deepseek_module = importlib.import_module(
            "jira_analyzer.analyzer.core.llm.deepseek_client"
        )

        provider_class = getattr(deepseek_module, "DeepSeekProvider", None)
        if provider_class is not None:
            return provider_class()

        send_prompt = getattr(deepseek_module, "send_prompt", None)
        if callable(send_prompt):
            class _LegacySendPromptProvider(LLMProvider):
                def send_prompt(
                    self,
                    prompt: str,
                    system_prompt: str | None = None,
                ) -> dict[str, Any]:
                    return send_prompt(prompt, system_prompt)

            return _LegacySendPromptProvider()

        raise ImportError(
            "Could not resolve a default LLM provider from deepseek_client. "
            "Make sure the module exposes DeepSeekProvider or send_prompt()."
        )

    async def _async_analyze_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        total = len(issues)
        if self.repo:
            for idx, issue in enumerate(issues, start=1):
                task_id = issue.get("key") or issue.get("jira_key") or f"local_{idx}"
                await asyncio.to_thread(self.repo.save_pending, task_id, issue)

        sem = asyncio.Semaphore(self.worker_count)

        async def process_issue(idx: int, issue: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
            async with sem:
                task_id = issue.get("key") or issue.get("jira_key") or f"local_{idx}"
                if self.repo:
                    await asyncio.to_thread(self.repo.update_processing, task_id)

                try:
                    analysis = await self._async_analyze_issue(idx=idx, total=total, issue=issue)
                    if 'error' in analysis:
                        if self.repo:
                            await asyncio.to_thread(self.repo.save_failed, task_id, analysis['error'])
                    else:
                        if self.repo:
                            await asyncio.to_thread(self.repo.save_result, task_id, analysis)
                    return (idx, analysis)
                except Exception as error:
                    logger.error(f"Analysis failed for issue {idx}/{total}: {error}")
                    failed_result = {
                        "error": str(error),
                        "key": task_id,
                        "jira_key": task_id,
                        "input_element_type": issue.get("element_type", ""),
                        "input_description": issue.get("description", ""),
                        "status": issue.get("status", ""),
                        "updated_at": issue.get("updated_at", ""),
                    }
                    if self.repo:
                        await asyncio.to_thread(self.repo.save_failed, task_id, str(error))
                    return (idx, failed_result)

        tasks = [
            asyncio.create_task(process_issue(idx, issue))
            for idx, issue in enumerate(issues, start=1)
        ]
        result_items = await asyncio.gather(*tasks)

        return [result for _, result in sorted(result_items)]

    def analyze_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return asyncio.run(self._async_analyze_issues(issues))

    async def _async_analyze_issue(
        self,
        *,
        idx: int,
        total: int,
        issue: Dict[str, Any],
    ) -> Dict[str, Any]:
        element_type = issue.get("element_type") or issue.get("type") or issue.get("issuetype", {}).get("name") or "Unknown"
        description = issue.get("description", "")

        if not description:
            return {
                "error": "No description provided",
                "key": issue.get("key"),
                "jira_key": issue.get("jira_key"),
                "input_element_type": element_type,
                "input_description": description,
            }

        logger.info(f"Processing issue {idx}/{total}: {element_type}")
        try:
            if self.prompt_config is not None:
                if self.split_by_criterion and len(self.prompt_config.criteria) > 1:
                    prompt_result = await self._async_analyze_issue_criteria_split(
                        element_type=element_type,
                        description=description,
                    )
                else:
                    prompt = build_structured_prompt(
                        element_type,
                        description,
                        self.prompt_config,
                    )
                    prompt_result = await self.llm_client.send_prompt(
                        prompt,
                        system_prompt=self.prompt_config.system_prompt,
                    )
            else:
                prompt = build_prompt_from_template(
                    element_type,
                    description,
                    self.prompt_template or "",
                )
                prompt_result = await self.llm_client.send_prompt(prompt)
        except Exception as error:
            logger.error(f"Failed to build prompt for issue {idx}: {error}")
            return {
                "error": f"Prompt building error: {str(error)}",
                "key": issue.get("key"),
                "jira_key": issue.get("jira_key"),
                "input_element_type": element_type,
                "input_description": description,
            }

        try:
            if issue.get("key"):
                prompt_result["key"] = issue["key"]
            if issue.get("jira_key"):
                prompt_result["jira_key"] = issue["jira_key"]
            prompt_result["input_element_type"] = element_type
            prompt_result["input_description"] = description
            prompt_result["status"] = issue.get("status", "")
            prompt_result["updated_at"] = issue.get("updated_at", "")
            return prompt_result
        except Exception as error:
            logger.error(f"Failed to attach metadata to the result for issue {idx}: {error}")
            return {
                "error": f"Result metadata error: {str(error)}",
                "key": issue.get("key"),
                "jira_key": issue.get("jira_key"),
                "input_element_type": element_type,
                "input_description": description,
                "status": issue.get("status", ""),
                "updated_at": issue.get("updated_at", ""),
            }

    def _analyze_issue(
        self,
        *,
        idx: int,
        total: int,
        issue: Dict[str, Any],
    ) -> Dict[str, Any]:
        return asyncio.run(self._async_analyze_issue(idx=idx, total=total, issue=issue))

    async def _async_analyze_issue_criteria_split(
        self,
        element_type: str,
        description: str,
    ) -> Dict[str, Any]:
        criteria_requests: list[tuple[str, str | None]] = []
        for criterion in self.prompt_config.criteria:
            single_prompt_config = AnalysisPromptConfig(
                system_prompt=self.prompt_config.system_prompt,
                general_prompt=self.prompt_config.general_prompt,
                criteria=[criterion],
                include_overall_conclusion=False,
            )
            prompt = build_structured_prompt(
                element_type,
                description,
                single_prompt_config,
            )
            criteria_requests.append((prompt, self.prompt_config.system_prompt))

        responses = await self.llm_client.send_prompts(criteria_requests)
        return self._merge_split_results(responses)

    def _analyze_issue_criteria_split(
        self,
        element_type: str,
        description: str,
    ) -> Dict[str, Any]:
        return asyncio.run(self._async_analyze_issue_criteria_split(element_type, description))

    def _merge_split_results(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {
            "criteria": {},
            "criteria_scores": {},
            "recommendations": [],  # Aggregate unique per-criterion recs
        }
        errors: list[str] = []
        successful_criteria_count = 0
        seen_criteria_keys: set[str] = set()
        seen_score_keys: set[str] = set()
        all_recs: set[str] = set()  # To deduplicate recommendations

        def _unique_key(base_key: str, existing_keys: set[str]) -> str:
            if base_key not in existing_keys:
                existing_keys.add(base_key)
                return base_key

            match = re.match(r"^(.*?)(?:_(\d+))?$", base_key)
            if match:
                prefix = match.group(1) or base_key
            else:
                prefix = base_key

            suffix = 2
            candidate = f"{prefix}_{suffix}"
            while candidate in existing_keys:
                suffix += 1
                candidate = f"{prefix}_{suffix}"

            existing_keys.add(candidate)
            return candidate

        for response in responses:
            if not isinstance(response, dict):
                errors.append("Non-dict response received from LLM")
                continue

            criteria = response.get("criteria")
            response_key_map: dict[str, str] = {}
            if isinstance(criteria, dict):
                for key, value in criteria.items():
                    unique_key = _unique_key(key, seen_criteria_keys)
                    response_key_map[key] = unique_key
                    merged["criteria"][unique_key] = value
                    successful_criteria_count += 1

                    # Collect per-criterion recommendations
                    criterion_recs = value.get("recommendations", [])
                    if isinstance(criterion_recs, list):
                        for rec in criterion_recs:
                            if isinstance(rec, str) and rec.strip():
                                all_recs.add(rec.strip())

            scores = response.get("criteria_scores")
            if isinstance(scores, dict):
                for key, value in scores.items():
                    unique_key = response_key_map.get(key, _unique_key(key, seen_score_keys))
                    if unique_key not in seen_score_keys:
                        seen_score_keys.add(unique_key)
                    merged["criteria_scores"][unique_key] = value

            # Also check top-level recs from response
            global_recs = response.get("recommendations", [])
            if isinstance(global_recs, list):
                for rec in global_recs:
                    if isinstance(rec, str) and rec.strip():
                        all_recs.add(rec.strip())

            if response.get("error"):
                errors.append(str(response["error"]))

        # Sort and set to list for top-level recommendations
        merged["recommendations"] = sorted(list(all_recs))

        if self.prompt_config and self.prompt_config.include_overall_conclusion:
            merged["overall_conclusion"] = (
                f"This analysis was produced by separate per-criterion requests. "
                f"Successfully analyzed {successful_criteria_count} criteria."
            )

        if errors:
            merged["error"] = "; ".join(errors)

        return merged
