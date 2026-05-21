"""OpenAI-compatible provider implementation.

This provider implements the BaseLLMProvider interface using the
OpenAI Python client. It's compatible with any OpenAI-compatible API
(like internal/self-hosted LLM services).
"""

import openai
from typing import Optional

from .base import BaseLLMProvider, LLMMessage, LLMResponse


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI-compatible API provider (protocol, not service).

    Student implementation: Simple synchronous wrapper around OpenAI client.

    SECURITY NOTE: No default URLs or models - all must be provided via config.
    Suitable for internal/self-hosted LLM services.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str
    ):
        """Initialize with connection details.

        Args:
            api_key: API authentication key (required - NO DEFAULTS)
            base_url: API endpoint URL (required - NO DEFAULTS)
            model: Model identifier to use (required - NO DEFAULTS)

        SECURITY: All parameters are REQUIRED - no defaults that connect externally.
        This prevents accidental connections to external OpenAI services.
        """
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self._model = model

    @property
    def provider_name(self) -> str:
        """Return provider identifier.

        Note: We return 'openai-compatible' not 'openai' because this
        implements the OpenAI API protocol, not the specific service.
        """
        return "openai-compatible"

    def call_llm(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Make LLM API call.

        Converts LLMMessage objects to OpenAI format and synchronous call.

        Args:
            messages: List of LLMMessage objects
            temperature: Randomness (0.0-2.0)
            max_tokens: Output limit (None = provider default)

        Returns:
            LLMResponse with content and metadata
        """
        # Convert LLMMessage to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Build API parameters
        api_params = {
            "model": self._model,
            "messages": openai_messages,
            "temperature": temperature,
        }
        
        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens

        # Make synchronous call (no async)
        response = self._client.chat.completions.create(**api_params)

        # Extract response content
        content = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else None

        return LLMResponse(
            content=content,
            model=self._model,
            tokens_used=tokens_used
        )
