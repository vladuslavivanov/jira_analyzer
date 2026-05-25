from __future__ import annotations

from typing import Optional

from openai import OpenAI

from jira_analyzer.providers.base import BaseLLMProvider, LLMMessage, LLMResponse


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

        # Return response
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else None
        )
