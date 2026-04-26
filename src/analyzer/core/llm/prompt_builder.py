from pathlib import Path


def build_prompt(element_type: str, description: str, prompt_file: Path) -> str:
    """
    Формирует промпт для DeepSeek на основе типа элемента и описания.
    Нейросеть должна вернуть строго JSON с заданной структурой.
    """

    # TODO: use Jinja
    prompt = prompt_file.read_text().format(
        element_type=element_type,
        description=description,
    )
    return prompt
