"""Base provider interface for LLM providers.

This abstract base class defines the contract that all LLM providers
must implement. It uses simple data structures and synchronous calls.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMMessage:
    """Simple message container for LLM requests.
    
    Supports basic message role and content structure.
    """
    role: str  # "user" or "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from LLM provider.
    
    Contains the actual response content and metadata.
    """
    content: str
    model: str
    tokens_used: Optional[int] = None


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers.

    This interface defines the contract that all LLM providers
    must implement. Students learn interface definition and abstract methods.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier (e.g., 'openai-compatible', 'fake')."""  
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
