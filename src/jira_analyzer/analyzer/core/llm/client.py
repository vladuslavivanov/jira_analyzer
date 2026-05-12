from __future__ import annotations

import asyncio
from queue import Empty, Queue
from threading import Lock, Semaphore, Thread
from typing import Any

from jira_analyzer.analyzer.core.llm.provider import LLMProvider


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
        self._semaphore = Semaphore(self.max_workers)
        self._max_queue_size = max_queue_size or 0

    def send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Send a single prompt through the configured provider."""
        with self._semaphore:
            return self.provider.send_prompt(prompt, system_prompt)

    def send_prompts(self, requests: list[tuple[str, str | None]]) -> list[dict[str, Any]]:
        """Send multiple prompts using an internal queue and worker threads."""
        if not requests:
            return []

        request_queue: Queue[tuple[int, tuple[str, str | None]]] = Queue(self._max_queue_size)
        result_items: list[tuple[int, dict[str, Any]]] = []
        result_lock = Lock()

        for index, request in enumerate(requests):
            request_queue.put((index, request))

        def worker() -> None:
            while True:
                try:
                    index, (prompt, system_prompt) = request_queue.get_nowait()
                except Empty:
                    return

                try:
                    response = self.send_prompt(prompt, system_prompt)
                except Exception as error:
                    response = {"error": str(error)}
                finally:
                    with result_lock:
                        result_items.append((index, response))
                    request_queue.task_done()

        threads = [
            Thread(
                target=worker,
                name=f"llm-client-worker-{index}",
                daemon=True,
            )
            for index in range(1, min(self.max_workers, len(requests)) + 1)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        return [result for _, result in sorted(result_items, key=lambda item: item[0])]

    async def async_send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Asynchronously send a single prompt."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.send_prompt, prompt, system_prompt)

    async def async_send_prompts(
        self,
        requests: list[tuple[str, str | None]],
    ) -> list[dict[str, Any]]:
        """Asynchronously send multiple prompts in parallel."""
        tasks = [
            asyncio.create_task(self.async_send_prompt(prompt, system_prompt))
            for prompt, system_prompt in requests
        ]
        return await asyncio.gather(*tasks)
