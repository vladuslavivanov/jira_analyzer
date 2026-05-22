"""Adapter to bridge between new provider architecture and legacy async interface.

This adapter allows the new synchronous providers (BaseLLMProvider)
to work with the legacy async LLMProvider interface expected by
AnalysisService and LLMClient.
"""

import asyncio
from typing import Any

from jira_analyzer.analyzer.core.llm.provider import LLMProvider
from jira_analyzer.providers.base import BaseLLMProvider, LLMMessage as ProviderMessage


class ProviderAdapter(LLMProvider):
    """Adapter to wrap synchronous providers in async interface.
    
    This allows the new provider architecture (synchronous) to work
    with the legacy AnalysisService and LLMClient (async) without
    requiring changes to the core application logic.
    """

    def __init__(self, base_provider: BaseLLMProvider):
        """Initialize adapter with a synchronous provider.
        
        Args:
            base_provider: Instance of BaseLLMProvider (synchronous)
        """
        self._provider = base_provider

    async def send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Send prompt using synchronous provider (wrapped as async).
        
        Args:
            prompt: User prompt message
            system_prompt: Optional system prompt (prepended as message)
            
        Returns:
            Dictionary with analysis results (compatible with AnalysisService)
        """
        import json
        
        # Convert to provider message format
        messages = []
        # Note: We use "system" role for system prompts (standard OpenAI format)
        # Some providers (like fake) may ignore system messages, while others use them
        if system_prompt:
            messages.append(ProviderMessage(role="system", content=system_prompt))
        messages.append(ProviderMessage(role="user", content=prompt))
        
        # Call synchronous provider in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._provider.call_llm, messages)
        
        # Try to parse response as JSON (most providers return JSON analysis results)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            # If not JSON, return as plain text in a dict format
            return {"analysis": response.content, "model": response.model}

    async def async_send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Async wrapper for synchronous provider.
        
        Args:
            prompt: User prompt message  
            system_prompt: Optional system prompt
            
        Returns:
            Dictionary with response content and metadata
        """
        # Run synchronous send_prompt in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.send_prompt, prompt, system_prompt)
        return result