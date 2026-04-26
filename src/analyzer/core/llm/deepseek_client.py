import json

from openai import OpenAI

from util.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from util.logger import setup_logger

logger = setup_logger(__name__)

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)


def send_prompt(prompt: str) -> dict:
    """
    Отправляет промпт в DeepSeek и возвращает распарсенный JSON-ответ.
    """
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Ты — эксперт по качеству задач в системах трекинга (Jira / YouTrack). "
                    "Твоя задача — критически оценить описание (дескрипшен) задачи, "
                    "выявить его слабые места и присвоить объективную оценку по заданным "
                    "критериям. Ты строг, но конструктивен. Ты не принимаешь расплывчатые "
                    'формулировки, эмоциональные оценки ("боюсь", "кажется") и '
                    "отсутствие измеримых результатов.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={
                "type": "json_object"
            },  # для моделей, поддерживающих JSON mode
        )
        content = response.choices[0].message.content

        # Извлекаем JSON из ответа (на случай лишних символов)
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
