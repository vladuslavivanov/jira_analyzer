"""Basic tests for provider architecture system."""

import pytest

from jira_analyzer.providers import (
    ProviderFactory,
    OpenAICompatibleProvider,
    LLMMessage,
    LLMResponse,
)


def test_provider_creation():
    """Test that provider can be created from config - happy path only."""
    config = {
        "provider_type": "openai-compatible",
        "api_key": "test-key",
        "base_url": "http://localhost:8000/v1",
        "model": "test-model"
    }
    provider = ProviderFactory.create_provider(config)
    
    # Verify provider was created correctly
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.provider_name == "openai-compatible"


def test_provider_properties():
    """Test provider properties and dataclasses - happy path only."""
    # Test LLMMessage dataclass
    message = LLMMessage(role="user", content="Test message")
    assert message.role == "user"
    assert message.content == "Test message"
    
    # Test LLMResponse dataclass  
    response = LLMResponse(content="Test response", model="test-model", tokens_used=42)
    assert response.content == "Test response"
    assert response.model == "test-model"
    assert response.tokens_used == 42
    
    # Test optional parameter
    response_no_tokens = LLMResponse(content="Test response", model="test-model")
    assert response_no_tokens.tokens_used is None
