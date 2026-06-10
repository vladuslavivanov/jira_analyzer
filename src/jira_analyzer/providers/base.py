from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMMessage:
    """Simple message container for LLM requests."""
    role: str  # "user" or "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    model: str
    tokens_used: Optional[int] = None


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers.

    Student implementation: Interface definition, abstract methods.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier (e.g., 'openai', 'fake')."""
        pass

    @abstractmethod
    def call_llm(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Make LLM API call.

        Args:
            messages: List of user/assistant messages
            temperature: Randomness (0.0-2.0)
            max_tokens: Output limit (None = provider default)

        Returns:
            LLMResponse with content and metadata
        """
        pass
