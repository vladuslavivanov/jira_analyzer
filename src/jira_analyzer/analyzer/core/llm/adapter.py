import asyncio
import json
from typing import Any

from jira_analyzer.analyzer.core.llm.provider import LLMProvider
from jira_analyzer.providers import BaseLLMProvider, LLMMessage, LLMResponse


class SyncToAsyncLLMAdapter(LLMProvider):
    """Adapter that wraps synchronous BaseLLMProvider to work with async LLMClient.
    
    This adapter allows the new synchronous provider architecture to work with
    the existing async AnalysisService infrastructure.
    """

    def __init__(self, sync_provider: BaseLLMProvider) -> None:
        """Initialize adapter with a synchronous provider.
        
        Args:
            sync_provider: Instance of BaseLLMProvider (synchronous)
        """
        self._sync_provider = sync_provider

    @property
    def provider_name(self) -> str:
        """Get the provider name from the wrapped synchronous provider."""
        return self._sync_provider.provider_name

    async def send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Send a prompt using the synchronous provider (async wrapper).
        
        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt
            
        Returns:
            Dictionary containing the response content or error
        """
        try:
            # Run synchronous implementation in a thread pool to not block the event loop
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self._sync_send_prompt(prompt, system_prompt)
            )
        
        except Exception as error:
            # Return error in format AnalysisService expects
            return {
                "error": str(error),
                "provider": self._sync_provider.provider_name
            }

    def _sync_send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """Synchronous implementation of send_prompt.
        
        This method does actual work and is run in a thread pool by
        async send_prompt method above.
        
        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt
            
        Returns:
            Dictionary containing the response content or error
        """
        try:
            # Build message list for new API
            messages: list[LLMMessage] = []
            
            if system_prompt:
                messages.append(LLMMessage(role="system", content=system_prompt))
            
            messages.append(LLMMessage(role="user", content=prompt))
            
            # Call synchronous provider
            response: LLMResponse = self._sync_provider.call_llm(
                messages=messages,
                temperature=0.2,  # Low temperature for deterministic responses
                max_tokens=None
            )
            
            # Return result in format expected by AnalysisService
            # Try to parse as JSON first (for structured responses)
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                # If not JSON, return plain text response
                return {
                    "text": response.content,
                    "model": response.model,
                    "tokens_used": response.tokens_used
                }
                
        except Exception as error:
            # Return error in format AnalysisService expects
            return {
                "error": str(error),
                "provider": self._sync_provider.provider_name
            }
