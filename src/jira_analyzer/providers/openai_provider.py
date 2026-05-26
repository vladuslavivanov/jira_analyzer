from __future__ import annotations

from typing import Optional

from openai import OpenAI

from jira_analyzer.providers.base import BaseLLMProvider, LLMMessage, LLMResponse
from jira_analyzer.utils.logger import setup_logger
from jira_analyzer.utils.config import LOG_LLM_PROMPTS


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI-compatible API provider.

    Simple implementation - no complex retry logic or error handling.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str
    ):
        """Initialize with connection details.

        Args:
            api_key: API authentication key (required)
            base_url: API endpoint URL (required)
            model: Model identifier to use (required)
        """
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self._model = model
        self._logger = setup_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "openai-compatible"

    def call_llm(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Convert messages to OpenAI format and call API.

        Returns:
            LLMResponse with content and metadata
        """
        # Log request if enabled
        if LOG_LLM_PROMPTS:
            self._logger.info("=== LLM Request ===")
            for msg in messages:
                self._logger.info(f"{msg.role}: {msg.content}")

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": str(msg.role), "content": str(msg.content)}
            for msg in messages
        ]

        # Call API with explicit type ignore as we're formatting correctly
        response = self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,  # type: ignore[assignment]
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Extract response content
        content = response.choices[0].message.content or ""
        
        # Log response if enabled
        if LOG_LLM_PROMPTS:
            self._logger.info("=== LLM Response ===")
            if response.choices:
                self._logger.info(f"Finish reason: {response.choices[0].finish_reason}")
            if response.usage:
                self._logger.info(f"Tokens used: {response.usage.total_tokens} (prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens})")
            self._logger.info(f"Content: {content}")

        # Return response
        return LLMResponse(
            content=content,
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else None
        )
