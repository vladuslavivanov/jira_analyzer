"""Basic tests for provider architecture system."""

import pytest

from jira_analyzer.providers import (
    ProviderFactory,
    OpenAICompatibleProvider,
    FakeLLMProvider,
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


def test_fake_provider_creation():
    """Test FakeLLMProvider can be created via factory - happy path."""
    config = {
        "provider_type": "fake",
        "default_response": "Custom fake response"
    }
    provider = ProviderFactory.create_provider(config)
    
    # Verify provider was created correctly
    assert isinstance(provider, FakeLLMProvider)
    assert provider.provider_name == "fake"


def test_fake_provider_factory_none_config():
    """Test FakeLLMProvider creation via factory with no config fields."""
    config = {
        "provider_type": "fake"
    }
    provider = ProviderFactory.create_provider(config)
    
    # Verify provider created with defaults
    assert isinstance(provider, FakeLLMProvider)
    assert provider.provider_name == "fake"


def test_fake_provider_with_responses():
    """Test FakeLLMProvider with custom response mappings.
    
    This tests that the fake provider can return different responses
    for different input messages, useful for testing various scenarios.
    """
    custom_responses = {
        "analyze": "Analysis complete: found 3 issues",
        "summarize": "Summary: This task involves user authentication"
    }
    
    provider = FakeLLMProvider(responses=custom_responses)
    
    # Test matching responses
    response1 = provider.call_llm([LLMMessage("user", "analyze")])
    assert response1.content == "Analysis complete: found 3 issues"
    assert response1.model == "fake-model-v1.0.0-test"
    
    response2 = provider.call_llm([LLMMessage("user", "summarize")])
    assert response2.content == "Summary: This task involves user authentication"
    
    # Test non-matching request falls back to default
    response3 = provider.call_llm([LLMMessage("user", "unknown")])
    assert "fake llm response" in response3.content.lower()


def test_fake_provider_default_response():
    """Test FakeLLMProvider with custom default response.
    
    This tests that a custom default response can be set and will
    be used for non-matching input messages.
    """
    custom_default = "This is my custom default response for testing"
    provider = FakeLLMProvider(default_response=custom_default)
    
    # Any request returns the custom default
    response = provider.call_llm([LLMMessage("user", "any input")])
    assert response.content == custom_default
    assert response.model == "fake-model-v1.0.0-test"
    assert response.tokens_used is not None


def test_fake_provider_default_behavior():
    """Test FakeLLMProvider with completely default configuration.
    
    This tests the behavior when no custom responses or default
    are provided - should use built-in default.
    """
    provider = FakeLLMProvider()  # No custom configuration
    
    response = provider.call_llm([LLMMessage("user", "test input")])
    
    # Should contain the built-in default message
    assert "fake llm response" in response.content.lower()
    assert "testing purposes" in response.content.lower()
    assert response.model == "fake-model-v1.0.0-test"


def test_fake_provider_message_priority():
    """Test that FakeLLMProvider finds the last user message.
    
    In typical LLM usage, only the last user message is relevant
    for generating the response. This tests that behavior.
    """
    responses = {
        "first": "First response",
        "second": "Second response", 
        "third": "Third response"
    }
    
    provider = FakeLLMProvider(responses=responses)
    
    # Multi-turn conversation - should use last user message
    messages = [
        LLMMessage("user", "first"),
        LLMMessage("assistant", "Assistant response"),
        LLMMessage("user", "second"),  # This should be used
    ]
    
    response = provider.call_llm(messages)
    assert response.content == "Second response"


def test_fake_provider_interface_compatibility():
    """Test that FakeLLMProvider follows the BaseLLMProvider interface.
    
    This ensures the fake provider is polymorphic with real providers.
    """
    provider = FakeLLMProvider()
    
    # Test that provider_name property exists and returns string
    assert isinstance(provider.provider_name, str)
    assert len(provider.provider_name) > 0
    
    # Test that call_llm accepts all required parameters
    response = provider.call_llm(
        messages=[LLMMessage("user", "test")],
        temperature=0.5,
        max_tokens=100
    )
    
    # Test that it returns LLMResponse with correct structure
    assert isinstance(response, LLMResponse)
    assert isinstance(response.content, str)
    assert isinstance(response.model, str)
    # tokens_used can be None or int
    assert response.tokens_used is None or isinstance(response.tokens_used, int)


def test_fake_provider_multiple_messages():
    """Test FakeLLMProvider handles conversational messages."""
    provider = FakeLLMProvider(default_response="Response")
    
    # Multiple messages in conversation
    messages = [
        LLMMessage("user", "Hello"),
        LLMMessage("assistant", "Hi there!"),
        LLMMessage("user", "How are you?"),
    ]
    
    response = provider.call_llm(messages)
    assert response.content == "Response"  # Uses last user message


def test_fake_provider_empty_conversation():
    """Test FakeLLMProvider handles empty or assistant-only conversations.
    
    Edge case: what happens if there's no user message?
    """
    provider = FakeLLMProvider(default_response="Default response")
    
    # No user message, only assistant messages
    messages = [
        LLMMessage("assistant", "Helper text"),
    ]
    
    response = provider.call_llm(messages)
    # Should still return default response
    assert response.content == "Default response"
