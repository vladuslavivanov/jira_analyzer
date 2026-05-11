import json

from openai import OpenAI

from jira_analyzer.utils.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

DEFAULT_SYSTEM_PROMPT = (
    "You are a strict but constructive Jira issue quality analyst. "
    "Return only valid JSON."
)


def send_prompt(prompt: str, system_prompt: str | None = None) -> dict:
    """Send a prompt to DeepSeek and return the parsed JSON response."""
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
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
    except Exception as e:
        logger.error(f"Failed to get response from DeepSeek: {e}")
        raise
