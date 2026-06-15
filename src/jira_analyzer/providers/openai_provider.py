import time
from typing import Optional

from openai import (
    OpenAI,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
    APIError,
)

from jira_analyzer.analyzer.core.config import ReasoningEffort
from jira_analyzer.providers.base import BaseLLMProvider, LLMMessage, LLMResponse
from jira_analyzer.utils.logger import setup_logger
from jira_analyzer.utils.config import LOG_LLM_PROMPTS


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI-compatible API provider with retry and error handling.

    Transient errors (rate limits, timeouts, connection issues, 5xx) are
    retried with exponential backoff.  Non-retryable errors (auth, bad
    request, permission denied) are reported immediately with clear messages.
    """

    # Exceptions that warrant a retry attempt
    _RETRYABLE_ERRORS = (
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        InternalServerError,
    )

    # Maximum number of retry attempts for transient errors
    _MAX_RETRIES = 3

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        reasoning_effort: ReasoningEffort = ReasoningEffort.NONE,
    ):
        """Initialize with connection details.

        Args:
            api_key: API authentication key (required)
            base_url: API endpoint URL (required)
            model: Model identifier to use (required)
            reasoning_effort: Reasoning effort level.
                    "none" (default) — nothink mode. No thinking params sent.
                    "low", "medium", "high" — enable reasoning at specified effort.
        """
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._logger = setup_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "openai-compatible"

    def call_llm(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Convert messages to OpenAI format and call API with retry.

        Transient errors (rate limits, timeouts, connection drops, 5xx) are
        retried up to _MAX_RETRIES times with exponential backoff.  Hard
        errors (auth, bad request, permission) are raised immediately.

        Returns:
            LLMResponse with content and metadata

        Raises:
            RuntimeError: Wraps all API errors with user-friendly descriptions.
        """
        if LOG_LLM_PROMPTS:
            self._logger.info("=== LLM Request ===")
            self._logger.info(f"Reasoning effort: {self._reasoning_effort}")
            for msg in messages:
                self._logger.info(f"{msg.role}: {msg.content}")

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": str(msg.role), "content": str(msg.content)}
            for msg in messages
        ]

        # Prepare API call parameters
        api_params = {
            "model": self._model,
            "messages": openai_messages,  # type: ignore[assignment]
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if self._reasoning_effort == ReasoningEffort.NONE:
            api_params["extra_body"] = {"think": False}
        else:
            api_params["reasoning_effort"] = self._reasoning_effort

        # Execute with retry and error classification
        try:
            response = self._call_api_with_retry(api_params)
        except self._RETRYABLE_ERRORS as error:
            # All retries exhausted — likely the service is overloaded or unreachable
            raise RuntimeError(
                f"LLM API is temporarily unavailable after {self._MAX_RETRIES} retries. "
                f"The service may be rate-limited or experiencing an outage. "
                f"Please wait and try again later. Details: {error}"
            ) from error
        except AuthenticationError as error:
            raise RuntimeError(
                f"LLM API authentication failed. Check that your API key is correct "
                f"and has not expired. Details: {error}"
            ) from error
        except BadRequestError as error:
            raise RuntimeError(
                f"LLM API request was rejected as invalid. This may indicate a bug in "
                f"the prompt construction or an unsupported model parameter. "
                f"Details: {error}"
            ) from error
        except PermissionDeniedError as error:
            raise RuntimeError(
                f"LLM API access denied. Your API key may not have permission to "
                f"access the requested model or resource. Details: {error}"
            ) from error
        except APIError as error:
            raise RuntimeError(
                f"LLM API returned an unexpected error. Details: {error}"
            ) from error
        except Exception as error:
            # Catch-all for non-OpenAI errors (e.g. network stack issues)
            raise RuntimeError(
                f"Unexpected error during LLM API call. "
                f"Please check your network connection and API endpoint URL. "
                f"Details: {error}"
            ) from error

        # Log response if enabled
        if LOG_LLM_PROMPTS:
            self._logger.info("=== LLM Response ===")
            if response.choices:
                self._logger.info(f"Finish reason: {response.choices[0].finish_reason}")
            if response.usage:
                self._logger.info(
                    f"Tokens used: {response.usage.total_tokens} "
                    f"(prompt: {response.usage.prompt_tokens}, "
                    f"completion: {response.usage.completion_tokens})"
                )
            self._logger.info(f"Content: {response.choices[0].message.content}")

        content = response.choices[0].message.content or ""

        return LLMResponse(
            content=content,
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else None,
        )

    def _call_api_with_retry(self, api_params: dict) -> object:
        """Call the OpenAI chat completions API with retry for transient errors.

        Implements exponential backoff: after each failed attempt, sleep for
        2^attempt seconds (1, 2, 4 seconds) before the next retry.

        Args:
            api_params: Parameters to pass to chat.completions.create()

        Returns:
            Response object from the API

        Raises:
            One of self._RETRYABLE_ERRORS when all retries are exhausted.
        """
        last_exception = None

        for attempt in range(self._MAX_RETRIES):
            try:
                return self._client.chat.completions.create(**api_params)
            except self._RETRYABLE_ERRORS as error:
                last_exception = error
                remaining = self._MAX_RETRIES - attempt - 1

                if remaining > 0:
                    wait_time = 2 ** attempt  # 1, 2, 4
                    self._logger.warning(
                        "LLM API transient error (attempt %d/%d): %s. "
                        "Retrying in %ds (%d retries left)...",
                        attempt + 1,
                        self._MAX_RETRIES,
                        error,
                        wait_time,
                        remaining,
                    )
                    time.sleep(wait_time)
                else:
                    self._logger.error(
                        "LLM API transient error — all %d retries exhausted: %s",
                        self._MAX_RETRIES,
                        error,
                    )

        # All retries failed — re-raise the last retryable exception
        if last_exception is not None:
            raise last_exception
        # Safety guard (should never be reached)
        raise RuntimeError(
            f"LLM API call failed after {self._MAX_RETRIES} retries with no exception captured"
        )
