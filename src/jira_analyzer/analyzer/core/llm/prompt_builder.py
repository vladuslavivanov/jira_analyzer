import re
from dataclasses import dataclass, field
from typing import Literal, TextIO


ScoringSystem = Literal["binary", "percent"]


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
    Forms a prompt for the LLM based on the element type and description.

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
    criteria_block = "\n".join(
        _format_criterion(index, criterion)
        for index, criterion in enumerate(criteria, start=1)
    )
    schema = _build_json_schema_text(criteria, config.include_overall_conclusion)
    overall_instruction = (
        "Also include the overall_conclusion field."
        if config.include_overall_conclusion
        else "Do not include an overall_conclusion field."
    )

    return f"""Issue type:
{element_type}

Issue description:
{description}

General analysis prompt:
{config.general_prompt}

Criteria:
{criteria_block if criteria_block else "No separate criteria were provided."}

Output requirements:
- Return only valid JSON. Do not include markdown or explanatory text outside JSON.
- Put every criterion result into the top-level "criteria" object.
- Put a compact score map into "criteria_scores" for downstream parsing.
- For binary criteria, score must be 0 or 1.
- For percent criteria, score must be an integer from 0 to 100.
- {overall_instruction}

JSON schema to follow:
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
    Forms a prompt for the LLM based on the element type and description.

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


def _format_criterion(index: int, criterion: CriterionConfig) -> str:
    scale = (
        "0 or 1, where 0 means the criterion is not met and 1 means it is met"
        if criterion.scoring_system == "binary"
        else "0 to 100, where the value is the percent of criterion fulfillment"
    )
    review_instruction = (
        "Include a review field with a concise review from this criterion perspective."
        if criterion.include_review
        else "Do not include a review field for this criterion."
    )
    return (
        f"{index}. id: {criterion_key(criterion)}\n"
        f"   title: {criterion.title}\n"
        f"   description: {criterion.description}\n"
        f"   scoring_system: {criterion.scoring_system}\n"
        f"   score: {scale}\n"
        f"   review: {review_instruction}"
    )


def _build_json_schema_text(
    criteria: list[CriterionConfig],
    include_overall_conclusion: bool,
) -> str:
    criteria_schema = {}
    score_schema = {}
    for criterion in criteria:
        key = criterion_key(criterion)
        criterion_result = {
            "title": criterion.title,
            "scoring_system": criterion.scoring_system,
            "score": 0 if criterion.scoring_system == "binary" else 0,
        }
        if criterion.include_review:
            criterion_result["review"] = "Criterion-specific review."
        criteria_schema[key] = criterion_result
        score_schema[key] = (
            "0/1" if criterion.scoring_system == "binary" else "0-100"
        )

    schema = {
        "criteria": criteria_schema,
        "criteria_scores": score_schema,
    }
    if include_overall_conclusion:
        schema["overall_conclusion"] = "Overall conclusion for the issue."

    import json

    return json.dumps(schema, ensure_ascii=False, indent=2)
