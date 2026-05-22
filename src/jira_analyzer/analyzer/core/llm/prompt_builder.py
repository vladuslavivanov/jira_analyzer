import re
from dataclasses import dataclass, field
from typing import Literal, TextIO


ScoringSystem = Literal["binary", "percent", "five"]


@dataclass
class CriterionConfig:
    title: str
    description: str
    scoring_system: ScoringSystem = "percent"
    include_review: bool = False
    key: str | None = None


@dataclass
class AnalysisPromptConfig:
    system_prompt: str
    general_prompt: str
    criteria: list[CriterionConfig] = field(default_factory=list)
    include_overall_conclusion: bool = True


DEFAULT_SYSTEM_PROMPT = (
    "You are a strict but constructive Jira issue quality analyst. "
    "Return only valid JSON that matches the requested schema."
)

DEFAULT_GENERAL_PROMPT = (
    "Analyze the issue description. Evaluate whether it is clear, complete, "
    "measurable, and suitable for the specified issue type."
)

DEFAULT_CRITERIA = [
    CriterionConfig(
        title="Completeness and specificity",
        description=(
            "Check whether the issue contains concrete names, links, versions, "
            "API signatures, expected behavior, and enough context to act on it."
        ),
        scoring_system="percent",
        include_review=True,
    ),
    CriterionConfig(
        title="Measurability and acceptance criteria",
        description=(
            "Check whether the issue has measurable success conditions. For a "
            "Task, look for DoD or a verifiable result. For a Risk, look for "
            "probability, impact, and a mitigation plan."
        ),
        scoring_system="percent",
        include_review=True,
    ),
]


def build_prompt_from_template(
    element_type: str,
    description: str,
    template: str,
) -> str:
    """
    Forms a prompt for the LLM based on the element_type and description.

    We use .replace() instead of .format() to avoid conflicts with literal curly
    braces used in JSON examples inside the template.
    """
    prompt = template.replace("{element_type}", str(element_type))
    prompt = prompt.replace("{description}", str(description))

    return prompt


def build_structured_prompt(
    element_type: str,
    description: str,
    config: AnalysisPromptConfig,
) -> str:
    criteria = [
        criterion
        for criterion in config.criteria
        if criterion.title.strip() and criterion.description.strip()
    ]
    criterion_keys = _criterion_key_map(criteria)
    criteria_block = "\n".join(
        _format_criterion(index, criterion, criterion_keys[index - 1])
        for index, criterion in enumerate(criteria, start=1)
    )
    schema = _build_json_schema_text(
        criteria,
        config.include_overall_conclusion,
        criterion_keys,
    )
    overall_instruction = (
        "Also include the overall_conclusion field."
        if config.include_overall_conclusion
        else "Do not include an overall_conclusion field."
    )

    return f"""Тип проблемы:
{element_type}

Описание проблемы:
{description}

Общий промпт для анализа:
{config.general_prompt}

Критерии:
{criteria_block if criteria_block else "Отдельные критерии не были предоставлены."}

Требования к выводу:
- Возвращай только корректный JSON. Не включай markdown или пояснительный текст вне JSON.
- Строго следуй JSON-схеме ниже и сохраняй точные идентификаторы критериев.
- Помести результат каждого критерия в объект верхнего уровня "criteria".
- Результат каждого критерия должен включать: title, description, scoring_system и score.
- Добавляй поле review для критерия только в том случае, если оно явно требуется этим критерием.
- Для каждого критерия включай recommendations в виде массива из 1–3 конкретных предложений, основанных на оценке по этому критерию.
- Помести компактную карту оценок в "criteria_scores" для последующего парсинга.
- Значения criteria_scores должны соответствовать значениям criteria.*.score.
- Вычисляй total_score как среднее значение всех criteria_scores.
- Объединяй все уникальные рекомендации по критериям в список верхнего уровня recommendations.
- Предоставь список рекомендаций по улучшению описания проблемы на основе анализа.
- Не добавляй критерии, отсутствующие в схеме.
- Для бинарных критериев значение score должно быть 0 или 1.
- Для процентных критериев значение score должно быть целым числом от 0 до 100.
- Для пятибалльных критериев значение score должно быть целым числом от 0 до 5.
- {overall_instruction}

JSON-схема, которой необходимо следовать:
{schema}
"""


def get_default_prompt_config() -> AnalysisPromptConfig:
    return AnalysisPromptConfig(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        general_prompt=DEFAULT_GENERAL_PROMPT,
        criteria=[CriterionConfig(**criterion.__dict__) for criterion in DEFAULT_CRITERIA],
        include_overall_conclusion=True,
    )


def build_prompt(element_type: str, description: str, prompt_file: TextIO) -> str:
    """
    Forms a prompt for the LLM based on the element_type and description.

    Note: We use .replace() instead of .format() to avoid conflicts with
    the literal curly braces used in the JSON structure within the template.
    """
    return build_prompt_from_template(element_type, description, prompt_file.read())


def criterion_key(criterion: CriterionConfig) -> str:
    if criterion.key:
        return criterion.key
    key = re.sub(r"[^a-zA-Z0-9]+", "_", criterion.title.strip().lower())
    key = key.strip("_")
    return key or "criterion"


def _criterion_key_map(criteria: list[CriterionConfig]) -> list[str]:
    keys: list[str] = []
    used: set[str] = set()
    for index, criterion in enumerate(criteria, start=1):
        base_key = criterion_key(criterion)
        if base_key == "criterion":
            base_key = f"criterion_{index}"

        key = base_key
        suffix = 2
        while key in used:
            key = f"{base_key}_{suffix}"
            suffix += 1

        used.add(key)
        keys.append(key)

    return keys


def _format_criterion(index: int, criterion: CriterionConfig, key: str) -> str:
    scale = _scoring_instruction(criterion.scoring_system)
    review_instruction = (
        "Include a review field with a concise review from this criterion perspective."
        if criterion.include_review
        else "Do not include a review field for this criterion."
    )
    return (
        f"{index}. id: {key}\n"
        f"   title: {criterion.title}\n"
        f"   description: {criterion.description}\n"
        f"   scoring_system: {criterion.scoring_system}\n"
        f"   score: {scale}\n"
        f"   review: {review_instruction}"
    )


def _build_json_schema_text(
    criteria: list[CriterionConfig],
    include_overall_conclusion: bool,
    criterion_keys: list[str] | None = None,
) -> str:
    criteria_schema = {}
    score_schema = {}
    if criterion_keys is None:
        criterion_keys = _criterion_key_map(criteria)
    for criterion, key in zip(criteria, criterion_keys, strict=True):
        criterion_result = {
            "title": criterion.title,
            "description": criterion.description,
            "scoring_system": criterion.scoring_system,
            "score": 0,
        }
        if criterion.include_review:
            criterion_result["review"] = "Criterion-specific review."
        criterion_result["recommendations"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "1-3 specific recommendations for this criterion based on the score"
        }
        criteria_schema[key] = criterion_result
        score_schema[key] = _score_schema_label(criterion.scoring_system)

    schema = {
        "criteria": criteria_schema,
        "criteria_scores": score_schema,
        "total_score": {
            "type": "number",
            "description": "Overall score as the average of all criteria scores"
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Aggregated list of unique recommendations from all criteria"
        },
    }
    if include_overall_conclusion:
        schema["overall_conclusion"] = "Overall conclusion for the issue."

    import json

    return json.dumps(schema, ensure_ascii=False, indent=2)


def _scoring_instruction(scoring_system: ScoringSystem) -> str:
    if scoring_system == "binary":
        return "0 or 1, where 0 means the criterion is not met and 1 means it is met"
    if scoring_system == "five":
        return "0 to 5, where 0 means not met and 5 means fully met"
    return "0 to 100, where the value is the percent of criterion fulfillment"


def _score_schema_label(scoring_system: ScoringSystem) -> str:
    if scoring_system == "binary":
        return "0/1"
    if scoring_system == "five":
        return "0-5"
    return "0-100"
