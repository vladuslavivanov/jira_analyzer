"""Analysis configuration dataclasses for type-safe config handling."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

ScoringSystem = Literal["binary", "percent", "five"]


@dataclass
class CriterionDefinition:
    """A single analysis criterion with scoring configuration."""

    title: str = ""
    description: str = ""
    scoring_system: ScoringSystem = "percent"
    include_review: bool = False
    key: str = ""


@dataclass
class AnalysisConfig:
    """Unified analysis configuration with serialization.

    This is the canonical format for all three config contexts:
      - Resources (default config loaded from JSON)
      - UI editor export / import
      - Analysis run config export from the results viewer

    Run-specific metadata fields (run_name, created_at, etc.) are
    preserved in exports but silently ignored on import.
    """

    version: int = 1
    system_prompt: str = ""
    general_prompt: str = ""
    include_overall_conclusion: bool = True
    default_scoring_system: ScoringSystem = "percent"
    criteria: list[CriterionDefinition] = field(default_factory=list)

    # Run metadata (optional, populated by results-viewer export)
    run_name: str | None = None
    created_at: str | None = None
    split_by_criterion: bool = False
    reasoning_enabled: bool = False
    reasoning_effort: str = "high"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict (omits None values)."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    def to_json(self, **kwargs: Any) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, **kwargs)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisConfig:
        """Deserialize from a dict (tolerant of missing/extra keys)."""
        if not isinstance(data, dict):
            raise ValueError("Root value must be a JSON object.")

        criteria_data = data.get("criteria", [])
        if not isinstance(criteria_data, list):
            raise ValueError("Field 'criteria' must be a list.")

        criteria = []
        for index, item in enumerate(criteria_data, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Criterion {index} must be an object.")
            key = item.get("key", "")
            criteria.append(
                CriterionDefinition(
                    title=str(item.get("title", "")),
                    description=str(item.get("description", "")),
                    scoring_system=_normalize_scoring(item.get("scoring_system", "percent")),
                    include_review=bool(item.get("include_review", False)),
                    key=str(key) if key else "",
                )
            )

        default_scoring = _normalize_scoring(data.get("default_scoring_system", "percent"))

        # Accept both reasoning_enabled and reasoning_mode
        reasoning_enabled = data.get("reasoning_enabled", None)
        if reasoning_enabled is None:
            reasoning_enabled = data.get("reasoning_mode", False)

        return cls(
            version=int(data.get("version", 1)),
            system_prompt=str(data.get("system_prompt", "")),
            general_prompt=str(data.get("general_prompt", "")),
            include_overall_conclusion=bool(data.get("include_overall_conclusion", True)),
            default_scoring_system=default_scoring,
            criteria=criteria,
            run_name=data.get("run_name"),
            created_at=data.get("created_at"),
            split_by_criterion=bool(data.get("split_by_criterion", False)),
            reasoning_enabled=bool(reasoning_enabled),
            reasoning_effort=str(data.get("reasoning_effort", "high")),
        )


_SCORING_MAP: dict[str, ScoringSystem] = {
    "binary": "binary",
    "percent": "percent",
    "five": "five",
    "0/1": "binary",
    "0-100%": "percent",
    "0-5": "five",
}


def _normalize_scoring(value: Any) -> ScoringSystem:
    """Normalize a scoring system value to the canonical form."""
    if isinstance(value, str) and value in _SCORING_MAP:
        return _SCORING_MAP[value]
    raise ValueError(f"Unsupported scoring system: {value}")
