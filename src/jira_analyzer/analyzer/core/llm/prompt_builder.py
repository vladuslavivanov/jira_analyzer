import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TextIO

ScoringSystem = Literal["binary", "percent", "five"]

# Template loading paths
_PACKAGE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent
_TEMPLATES_DIR = _PACKAGE_DIR / "resources" / "prompts"
_DEFAULT_CONFIG_PATH = _TEMPLATES_DIR / "default" / "criteria-config.json"
_INSTRUCTIONS_PATH = _TEMPLATES_DIR / "default" / "instructions.json"


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


# Template loading functions
def _load_template(relative_path: str) -> str:
    """Load a template file from the resources directory."""
    template_path = _TEMPLATES_DIR / relative_path
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    return template_path.read_text(encoding="utf-8").strip()


def _load_criteria_config() -> list[CriterionConfig]:
    """Load default criteria configuration from JSON file."""
    if not _DEFAULT_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Criteria configuration file not found: {_DEFAULT_CONFIG_PATH}")
    
    try:
        with open(_DEFAULT_CONFIG_PATH, encoding="utf-8") as f:
            criteria_data = json.load(f)
        return [CriterionConfig(**criterion) for criterion in criteria_data]
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise ValueError(f"Invalid criteria configuration file: {e}") from e


def _load_instructions() -> dict[str, dict[str, str]]:
    """Load instruction strings from JSON file."""
    if not _INSTRUCTIONS_PATH.exists():
        raise FileNotFoundError(f"Instructions configuration file not found: {_INSTRUCTIONS_PATH}")
    
    try:
        with open(_INSTRUCTIONS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise ValueError(f"Invalid instructions configuration file: {e}") from e


# Load templates from files
DEFAULT_SYSTEM_PROMPT = _load_template("system-prompt.md")
DEFAULT_GENERAL_PROMPT = _load_template("general-prompt.md")
STRUCTURED_ANALYSIS_TEMPLATE = _load_template("structured-analysis-prompt.md")
CRITERION_FORMAT_TEMPLATE = _load_template("templates/criterion-format.md")

# Load default criteria from JSON configuration
DEFAULT_CRITERIA = _load_criteria_config()

# Load all instruction strings from JSON
_INSTRUCTIONS = _load_instructions()

# Get specific instruction sets from loaded data
_SCORING_INSTRUCTIONS = _INSTRUCTIONS["scoring_instructions"]
_SCORE_SCHEMA_LABELS = _INSTRUCTIONS["score_schema_labels"]
_OVERALL_INSTRUCTIONS = _INSTRUCTIONS["overall_instructions"]
_REVIEW_INSTRUCTIONS = _INSTRUCTIONS["review_instructions"]
_SCHEMA_DESCRIPTIONS = _INSTRUCTIONS["schema_descriptions"]


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
        _OVERALL_INSTRUCTIONS["include"]
        if config.include_overall_conclusion
        else _OVERALL_INSTRUCTIONS["exclude"]
    )

    # Use loaded template with placeholder replacement
    prompt = STRUCTURED_ANALYSIS_TEMPLATE.replace("{element_type}", str(element_type))
    prompt = prompt.replace("{description}", str(description))
    prompt = prompt.replace("{general_prompt}", str(config.general_prompt))
    prompt = prompt.replace("{criteria_block}", str(criteria_block))
    prompt = prompt.replace("{overall_instruction}", str(overall_instruction))
    prompt = prompt.replace("{json_schema}", str(schema))

    return prompt


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
    scoring_instruction_text = _scoring_instruction(criterion.scoring_system)
    review_instruction = (
        _REVIEW_INSTRUCTIONS["include"]
        if criterion.include_review
        else _REVIEW_INSTRUCTIONS["exclude"]
    )
    
    # Use loaded template with placeholder replacement
    formatted = CRITERION_FORMAT_TEMPLATE.replace("{criterion_index}", str(index))
    formatted = formatted.replace("{criterion_key}", str(key))
    formatted = formatted.replace("{criterion_title}", str(criterion.title))
    formatted = formatted.replace("{criterion_description}", str(criterion.description))
    formatted = formatted.replace("{criterion_scoring_system}", str(criterion.scoring_system))
    formatted = formatted.replace("{scoring_instruction}", str(scoring_instruction_text))
    formatted = formatted.replace("{review_instruction}", str(review_instruction))

    return formatted


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
            criterion_result["review"] = _SCHEMA_DESCRIPTIONS["criterion_review"]
        criterion_result["recommendations"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": _SCHEMA_DESCRIPTIONS["criteria_recommendations"]
        }
        criteria_schema[key] = criterion_result
        score_schema[key] = _score_schema_label(criterion.scoring_system)

    schema = {
        "criteria": criteria_schema,
        "criteria_scores": score_schema,
        "total_score": {
            "type": "number",
            "description": _SCHEMA_DESCRIPTIONS["total_score"]
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": _SCHEMA_DESCRIPTIONS["aggregated_recommendations"]
        },
    }
    if include_overall_conclusion:
        schema["overall_conclusion"] = _SCHEMA_DESCRIPTIONS["overall_conclusion"]

    return json.dumps(schema, ensure_ascii=False, indent=2)


def _scoring_instruction(scoring_system: ScoringSystem) -> str:
    """Get scoring instruction from lookup dictionary."""
    return _SCORING_INSTRUCTIONS[scoring_system]


def _score_schema_label(scoring_system: ScoringSystem) -> str:
    """Get score schema label from lookup dictionary."""
    return _SCORE_SCHEMA_LABELS[scoring_system]
