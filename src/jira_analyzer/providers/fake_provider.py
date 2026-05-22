"""Fake LLM provider for testing without external API calls.

This provider returns hardcoded responses for testing purposes, allowing
development and testing without making actual LLM API requests.
"""

from typing import Optional, Dict, List

from .base import BaseLLMProvider, LLMMessage, LLMResponse


class FakeLLMProvider(BaseLLMProvider):
    """Fake LLM provider with hardcoded responses for testing.

    This provider is useful for:
    - Unit testing without real API calls
    - Development without external dependencies  
    - Reproducible test scenarios
    - Cost testing (no API charges)

    Student implementation: Simple in-memory response system.
    """

    def __init__(
        self,
        responses: Optional[Dict[str, str]] = None,
        default_response: Optional[str] = None
    ):
        """Initialize with optional hardcoded responses.

        Args:
            responses: Dictionary mapping user message content to fake responses.
                      If provided, provider returns matching responses.
                      If not found, uses default_response.
            default_response: Default response when no match found.
                             Defaults to a generic fake response.

        Example:
            # Provider with specific responses
            responses = {
                analyze: "Analyzing jira issues: found 3 bugs, 2 stories."
            }
            provider = FakeLLMProvider(responses=responses)
            
            # Provider with only default response
            provider = FakeLLMProvider(default_response="Mock response")
        """
        self._responses = responses or {}
        self._default_response = default_response or (
            "This is a fake LLM response for testing purposes. "
            "No actual API call was made."
        )

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "fake"

    def call_llm(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Return hardcoded response without making API call.

        This method:
        1. Extracts the last user message from the conversation
        2. Attempts to find matching response in predefined responses
        3. Returns matching response or default response
        4. Ignores temperature and max_tokens (parameters accepted for compatibility)

        Args:
            messages: List of LLMMessage objects (only last user message used)
            temperature: Randomness parameter (ignored - kept for interface compatibility)
            max_tokens: Token limit (ignored - kept for interface compatibility)

        Returns:
            LLMResponse with hardcoded content and fake model name
        """
        # Find the last user message (typical LLM usage pattern)
        user_content = None
        for message in reversed(messages):
            if message.role == "user":
                user_content = message.content
                break

        # Try to find matching response
        response_content = None
        if user_content and user_content in self._responses:
            response_content = self._responses[user_content]
        else:
            response_content = self._default_response

        # Return fake response (mock tokens based on response length)
        return LLMResponse(
            content=response_content,
            model="fake-model-v1.0.0-test",
            tokens_used=len(response_content.split())
        )
