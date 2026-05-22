"""Provider architecture for LLM services.

This module exports the provider abstraction and factory for creating
provider instances from configuration. All providers implement the
BaseLLMProvider interface for polymorphic usage.
"""

from typing import Dict, Any

from .base import BaseLLMProvider, LLMMessage, LLMResponse
from .openai_provider import OpenAICompatibleProvider
from .fake_provider import FakeLLMProvider

__all__ = [
    "BaseLLMProvider",
    "LLMMessage", 
    "LLMResponse",
    "OpenAICompatibleProvider",
    "FakeLLMProvider",
    "ProviderFactory",
]


class ProviderFactory:
    """Simple factory for creating providers from configuration.

    MVP version: Uses simple if-else logic (no dynamic loading).
    Complexity: ~30 lines including docstrings
    """

    @staticmethod
    def create_provider(config: Dict[str, Any]) -> BaseLLMProvider:
        """Create provider instance from config dictionary.

        Args:
            config: Configuration dictionary with provider settings
            
        Config structure (ALL FIELDS REQUIRED):
            {
                "provider_type": "openai-compatible",
                "api_key": "your-internal-api-key",
                "base_url": "http://localhost:8000/v1",
                "model": "your-model-name"
            }

        Returns:
            BaseLLMProvider instance appropriate for the provider_type

        Raises:
            ValueError: If provider_type unknown or required fields are missing

        SECURITY: All provider fields are REQUIRED - no fallback to external services.
        This prevents accidental connections to external OpenAI endpoints.
        """
        provider_type = config.get("provider_type")

        if provider_type == "openai-compatible":
            # Validate required fields (security: no external defaults)
            required_fields = ["api_key", "base_url", "model"]
            missing = [f for f in required_fields if f not in config]
            if missing:
                raise ValueError(
                    f"Missing required provider fields: {missing}. "
                    "All provider config fields must be explicitly set "
                    "(no external service defaults allowed)."
                )

            return OpenAICompatibleProvider(
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"]
            )
        elif provider_type == "fake":
            # Fake provider doesn't require API keys or URLs
            # Useful for testing without external dependencies
            return FakeLLMProvider(
                responses=config.get("responses"),
                default_response=config.get("default_response")
            )
        else:
            raise ValueError(
                f"Unknown provider: {provider_type}. "
                f"Supported providers: openai-compatible, fake"
            )
