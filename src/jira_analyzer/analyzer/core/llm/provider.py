from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Base interface for an LLM provider implementation."""

    @abstractmethod
    def send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        raise NotImplementedError()

    async def async_send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Optional asynchronous prompt support."""
        raise NotImplementedError("Async support is not implemented for this provider.")
