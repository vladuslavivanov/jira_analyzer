"""Tests for the new provider-agnostic LLM architecture."""

import pytest

from jira_analyzer.providers import (
    BaseLLMProvider,
    FakeProvider,
    LLMMessage,
    LLMResponse,
    OpenAICompatibleProvider,
    ProviderFactory,
)


def test_llm_message_dataclass():
    """Test LLMMessage dataclass creation and attributes."""
    message = LLMMessage(role="user", content="Test content")
    assert message.role == "user"
    assert message.content == "Test content"


def test_llm_response_dataclass():
    """Test LLMResponse dataclass creation and attributes."""
    response = LLMResponse(content="Response text", model="test-model", tokens_used=100)
    assert response.content == "Response text"
    assert response.model == "test-model"
    assert response.tokens_used == 100
    assert response.tokens_used is not None


def test_llm_response_dataclass_without_tokens():
    """Test LLMResponse without tokens_used field."""
    response = LLMResponse(content="Response text", model="test-model")
    assert response.content == "Response text"
    assert response.model == "test-model"
    assert response.tokens_used is None


def test_fake_provider_basic():
    """Test FakeProvider returns default response."""
    provider = FakeProvider()
    assert provider.provider_name == "fake"
    
    messages = [LLMMessage(role="user", content="Test")]
    response = provider.call_llm(messages)
    
    assert response.content == "Fake LLM response"
    assert response.model == "fake-model"
    assert response.tokens_used == 100


def test_fake_provider_custom_response():
    """Test FakeProvider with custom default response."""
    provider = FakeProvider(default_response="Custom response")
    assert provider.provider_name == "fake"
    
    messages = [LLMMessage(role="user", content="Test")]
    response = provider.call_llm(messages)
    
    assert response.content == "Custom response"


def test_fake_provider_ignores_parameters():
    """Test FakeProvider ignores temperature and max_tokens."""
    provider = FakeProvider()
    messages = [LLMMessage(role="user", content="Test")]
    
    # Various parameters should be ignored
    response1 = provider.call_llm(messages, temperature=0.1, max_tokens=50)
    response2 = provider.call_llm(messages, temperature=2.0, max_tokens=1000)
    
    assert response1.content == response2.content


def test_openai_provider_creation():
    """Test OpenAICompatibleProvider can be created."""
    provider = OpenAICompatibleProvider(
        api_key="test-key",
        base_url="http://test.com/v1",
        model="test-model"
    )
    assert provider.provider_name == "openai-compatible"
    assert provider._model == "test-model"


def test_openai_provider_requires_parameters():
    """Test OpenAICompatibleProvider requires all parameters."""
    with pytest.raises(TypeError):
        OpenAICompatibleProvider(
            api_key="test-key",
            base_url="http://test.com/v1",
            # Missing model
        )
    
    with pytest.raises(TypeError):
        OpenAICompatibleProvider(
            api_key="test-key",
            model="test-model",
            # Missing base_url
        )


def test_openai_provider_invalid_api_call():
    """Test OpenAICompatibleProvider wraps API errors in RuntimeError."""
    provider = OpenAICompatibleProvider(
        api_key="invalid-key",
        base_url="http://invalid-url.example.com/v1",
        model="test-model"
    )
    
    messages = [LLMMessage(role="user", content="Test")]
    
    with pytest.raises(RuntimeError):
        provider.call_llm(messages)


def test_provider_factory_creates_fake_provider():
    """Test ProviderFactory creates FakeProvider from config."""
    config = {
        "provider_type": "fake",
        "default_response": "Test response"
    }
    
    provider = ProviderFactory.create_provider(config)
    assert isinstance(provider, FakeProvider)
    assert provider.provider_name == "fake"


def test_provider_factory_creates_openai_provider():
    """Test ProviderFactory creates OpenAICompatibleProvider from config."""
    config = {
        "provider_type": "openai-compatible",
        "api_key": "test-key",
        "base_url": "http://test.com/v1",
        "model": "test-model"
    }
    
    provider = ProviderFactory.create_provider(config)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.provider_name == "openai-compatible"


def test_provider_factory_fake_default_response():
    """Test ProviderFactory uses default response for FakeProvider."""
    config = {"provider_type": "fake"}
    provider = ProviderFactory.create_provider(config)
    
    # Factory returns concrete provider instance
    assert isinstance(provider, FakeProvider)
    # Access the attribute through the concrete type
    assert provider._default_response == "Fake response"


def test_provider_factory_missing_openai_fields():
    """Test ProviderFactory raises ValueError for missing OpenAI fields."""
    config = {
        "provider_type": "openai-compatible",
        "api_key": "test-key"
        # Missing base_url and model
    }
    
    with pytest.raises(ValueError, match="Missing required fields"):
        ProviderFactory.create_provider(config)


def test_provider_factory_unknown_provider_type():
    """Test ProviderFactory raises ValueError for unknown provider types."""
    config = {"provider_type": "unknown"}
    
    with pytest.raises(ValueError, match="Unknown provider type"):
        ProviderFactory.create_provider(config)


def test_base_provider_is_abstract():
    """Test BaseLLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseLLMProvider()
