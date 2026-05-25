"""Tests for the provider adapter that bridges sync and async interfaces."""

from __future__ import annotations

import pytest

from jira_analyzer.analyzer.core.llm.adapter import SyncToAsyncLLMAdapter
from jira_analyzer.providers import BaseLLMProvider, FakeProvider, LLMMessage, LLMResponse


def test_adapter_wraps_fake_provider():
    """Test SyncToAsyncLLMAdapter wraps FakeProvider correctly."""
    fake_provider = FakeProvider("Test response")
    adapter = SyncToAsyncLLMAdapter(fake_provider)
    
    assert adapter.provider_name == "fake"
    assert adapter._sync_provider is fake_provider


def test_adapter_send_prompt_with_user_only():
    """Test adapter send_prompt with only user message."""
    fake_provider = FakeProvider('{"result": "test output"}')
    adapter = SyncToAsyncLLMAdapter(fake_provider)
    
    response = adapter.send_prompt("Test prompt", None)
    
    assert response["result"] == "test output"


def test_adapter_send_prompt_with_system_message():
    """Test adapter send_prompt with both system and user messages."""
    fake_provider = FakeProvider('{"result": "test output"}')
    adapter = SyncToAsyncLLMAdapter(fake_provider)
    
    response = adapter.send_prompt("Test prompt", "System prompt")
    
    assert response["result"] == "test output"


def test_adapter_send_prompt_json_response():
    """Test adapter correctly parses JSON responses."""
    expected_response = {
        "overall_conclusion": "ok",
        "criteria": {"completeness": {"score": 100}}
    }
    fake_provider = FakeProvider('{"overall_conclusion": "ok", "criteria": {"completeness": {"score": 100}}}')
    adapter = SyncToAsyncLLMAdapter(fake_provider)
    
    response = adapter.send_prompt("Test prompt", None)
    
    assert response == expected_response


def test_adapter_send_prompt_non_json_response():
    """Test adapter handles non-JSON responses gracefully."""
    fake_provider = FakeProvider("Plain text response")
    adapter = SyncToAsyncLLMAdapter(fake_provider)
    
    response = adapter.send_prompt("Test prompt", None)
    
    assert response["text"] == "Plain text response"
    assert response["model"] == "fake-model"
    assert response["tokens_used"] == 100
    assert "error" not in response


def test_adapter_send_prompt_handles_exceptions():
    """Test adapter catches and returns provider exceptions as error dict."""
    class BrokenProvider(BaseLLMProvider):
        @property
        def provider_name(self) -> str:
            return "broken"
        
        def call_llm(self, messages, temperature=0.7, max_tokens=None) -> LLMResponse:
            raise Exception("Provider failed!")
    
    adapter = SyncToAsyncLLMAdapter(BrokenProvider())
    response = adapter.send_prompt("Test prompt", None)
    
    assert "error" in response
    assert "Provider failed!" in response["error"]
    assert response["provider"] == "broken"


@pytest.mark.asyncio
async def test_adapter_async_send_prompt():
    """Test adapter async_send_prompt works correctly."""
    fake_provider = FakeProvider('{"result": "async test"}')
    adapter = SyncToAsyncLLMAdapter(fake_provider)
    
    response = await adapter.async_send_prompt("Test prompt", None)
    
    assert response["result"] == "async test"


@pytest.mark.asyncio
async def test_adapter_async_matches_sync_behavior():
    """Test async behavior matches sync behavior."""
    fake_provider = FakeProvider('{"result": "test"}')
    adapter = SyncToAsyncLLMAdapter(fake_provider)
    
    sync_response = adapter.send_prompt("Test", None)
    async_response = await adapter.async_send_prompt("Test", None)
    
    assert sync_response == async_response
