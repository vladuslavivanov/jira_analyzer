from __future__ import annotations

from typing import Dict

from jira_analyzer.providers.base import BaseLLMProvider, LLMMessage, LLMResponse
from jira_analyzer.providers.fake_provider import FakeProvider
from jira_analyzer.providers.openai_provider import OpenAICompatibleProvider


class ProviderFactory:
    """Simple factory for creating providers from config.

    Simple if-else logic, no dynamic loading.
    """

    @staticmethod
    def create_provider(config: Dict) -> BaseLLMProvider:
        """Create provider instance from config dictionary.

        Config structure:
        {
            "provider_type": "openai-compatible" or "fake",
            "api_key": "your-api-key",           # for openai-compatible only
            "base_url": "http://localhost:8000/v1",  # for openai-compatible only
            "model": "your-model-name",          # for openai-compatible only
            "default_response": "response text"  # for fake only
        }
        """
        provider_type = config.get("provider_type")

        if provider_type == "openai-compatible":
            # Validate required fields
            required_fields = ["api_key", "base_url", "model"]
            missing = [f for f in required_fields if f not in config]
            if missing:
                raise ValueError(f"Missing required fields for openai-compatible: {missing}")

            return OpenAICompatibleProvider(
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"]
            )

        elif provider_type == "fake":
            default_response = config.get("default_response", "Fake response")
            return FakeProvider(default_response=default_response)

        else:
            raise ValueError(f"Unknown provider type: {provider_type}")


__all__ = [
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    "OpenAICompatibleProvider",
    "FakeProvider",
    "ProviderFactory",
]
