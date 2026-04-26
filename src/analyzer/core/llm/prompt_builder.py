from pathlib import Path
from typing import TextIO


def build_prompt(element_type: str, description: str, prompt_file: TextIO) -> str:
    """
    Формирует промпт для DeepSeek на основе типа элемента и описания.
    Нейросеть должна вернуть строго JSON с заданной структурой.
    """

    # TODO: use Jinja
    prompt = prompt_file.read().format(
        element_type=element_type,
        description=description,
    )
    return prompt
