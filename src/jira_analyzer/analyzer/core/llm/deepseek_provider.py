import json

from openai import AsyncOpenAI

from jira_analyzer.analyzer.core.llm.provider import LLMProvider
from jira_analyzer.utils.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from jira_analyzer.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a strict but constructive Jira issue quality analyst. "
    "Return only valid JSON."
)


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider implementation for OpenAI-compatible API usage."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.model = model or DEEPSEEK_MODEL
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def send_prompt(self, prompt: str, system_prompt: str | None = None) -> dict:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt or DEFAULT_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or ""

            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                json_str = content[start:end]
                result = json.loads(json_str)
            else:
                result = json.loads(content)

            logger.info("Successfully received and parsed response from DeepSeek")
            return result
        except Exception as error:
            logger.error(f"Failed to get response from DeepSeek: {error}")
            raise


_default_provider = DeepSeekProvider()


def send_prompt(prompt: str, system_prompt: str | None = None) -> dict:
    return _default_provider.send_prompt(prompt, system_prompt)


def get_default_provider() -> DeepSeekProvider:
    return _default_provider
