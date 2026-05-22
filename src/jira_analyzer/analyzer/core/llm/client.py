from __future__ import annotations

import asyncio

from typing import Any

from jira_analyzer.analyzer.core.llm.provider import LLMProvider
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)

class LLMClient:
    """Manages queued LLM requests with configurable concurrency."""

    def __init__(
        self,
        provider: LLMProvider,
        max_workers: int = 1,
        max_queue_size: int | None = None,
    ):
        self.provider = provider
        self.max_workers = max(1, int(max_workers))
        self._semaphore = asyncio.Semaphore(self.max_workers)
        self._max_queue_size = max_queue_size or 0

    async def send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Send a single prompt through the configured provider."""
        logger.info(f"{prompt=}, {system_prompt=}")
        async with self._semaphore:
            return await self.provider.send_prompt(prompt, system_prompt)

    async def send_prompts(self, requests: list[tuple[str, str | None]]) -> list[dict[str, Any]]:
        """Send multiple prompts asynchronously."""
        if not requests:
            return []

        tasks = [
            self.send_prompt(prompt, system_prompt)
            for prompt, system_prompt in requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            {"error": str(r)} if isinstance(r, Exception) else r
            for r in results
        ]
