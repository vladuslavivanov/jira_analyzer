from typing import Optional

from jira_analyzer.providers.base import BaseLLMProvider, LLMMessage, LLMResponse
from jira_analyzer.utils.logger import setup_logger
from jira_analyzer.utils.config import LOG_LLM_PROMPTS


class FakeProvider(BaseLLMProvider):
    """Fake provider that returns predefined responses.

    Simple implementation for testing without calling real APIs.
    """
    
    def __init__(self, default_response: str = "Fake LLM response"):
        """Initialize with default response.

        Args:
            default_response: Text to return for all calls
        """
        self._default_response = default_response
        self._logger = setup_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "fake"

    def call_llm(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,  # Ignored in fake
        max_tokens: Optional[int] = None  # Ignored in fake
    ) -> LLMResponse:
        """Return fake response.

        Simple implementation returning predefined response.
        """
        # Log request if enabled
        if LOG_LLM_PROMPTS:
            self._logger.info("=== LLM Request ===")
            for i, msg in enumerate(messages):
                self._logger.info(f"{msg.role}: {msg.content}")

        # Return response
        response = LLMResponse(
            content=self._default_response,
            model="fake-model",
            tokens_used=100
        )

        # Log response if enabled
        if LOG_LLM_PROMPTS:
            self._logger.info("=== LLM Response ===")
            self._logger.info(f"Content: {response.content}")
            self._logger.info(f"Tokens used: {response.tokens_used}")

        return response
