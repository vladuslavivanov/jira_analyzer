from __future__ import annotations

import json
import re

from jira_analyzer.analyzer.core.llm.prompt_builder import (
    AnalysisPromptConfig,
    CriterionConfig,
    build_structured_prompt,
)
from jira_analyzer.ui import (
    SCORING_LABEL_BY_VALUE,
    _delete_all_criteria,
    _delete_selected_criteria,
    _filter_criteria,
    _normalize_prompt_config,
    _set_all_criteria_scoring,
)


def test_set_all_criteria_scoring_updates_every_criterion():
    criteria = [
        {"title": "A", "description": "First", "scoring_system": "binary"},
        {"title": "B", "description": "Second", "scoring_system": "percent"},
    ]

    _set_all_criteria_scoring(criteria, "five")

    assert [criterion["scoring_system"] for criterion in criteria] == [
        "five",
        "five",
    ]
    assert SCORING_LABEL_BY_VALUE["five"] == "0-5"


def test_filter_criteria_matches_title_and_description():
    criteria = [
        {"title": "Completeness", "description": "Has all required details"},
        {"title": "Security", "description": "Mentions access control"},
        {"title": "Performance", "description": "Latency requirements"},
    ]

    assert [
        criterion["title"] for _, criterion in _filter_criteria(criteria, "access")
    ] == ["Security"]
    assert [
        criterion["title"] for _, criterion in _filter_criteria(criteria, "PERF")
    ] == ["Performance"]
    assert [
        criterion["title"] for _, criterion in _filter_criteria(criteria, "")
    ] == [
        "Completeness",
        "Security",
        "Performance",
    ]


def test_delete_selected_and_all_criteria():
    criteria = [
        {"title": "First", "selected": True},
        {"title": "Second", "selected": False},
        {"title": "Third", "selected": True},
    ]

    assert _delete_selected_criteria(criteria) == 2
    assert criteria == [{"title": "Second", "selected": False}]

    assert _delete_all_criteria(criteria) == 1
    assert criteria == []


def test_structured_prompt_contains_parseable_schema_for_mixed_criteria():
    config = AnalysisPromptConfig(
        system_prompt="system",
        general_prompt="general",
        criteria=[
            CriterionConfig(
                title="Binary criterion",
                description="Check yes or no.",
                scoring_system="binary",
                include_review=False,
            ),
            CriterionConfig(
                title="Percent criterion",
                description="Check completion percent.",
                scoring_system="percent",
                include_review=True,
            ),
            CriterionConfig(
                title="Five criterion",
                description="Check five point score.",
                scoring_system="five",
                include_review=True,
            ),
        ],
        include_overall_conclusion=True,
    )

    prompt = build_structured_prompt("Task", "Description", config)
    schema_match = re.search(r"JSON schema to follow:\n(\{.*\})\s*$", prompt, re.S)

    assert schema_match is not None
    schema = json.loads(schema_match.group(1))
    assert set(schema["criteria"]) == {
        "binary_criterion",
        "percent_criterion",
        "five_criterion",
    }
    assert schema["criteria"]["binary_criterion"] == {
        "title": "Binary criterion",
        "description": "Check yes or no.",
        "scoring_system": "binary",
        "score": 0,
    }
    assert schema["criteria"]["percent_criterion"]["review"]
    assert schema["criteria"]["five_criterion"]["scoring_system"] == "five"
    assert schema["criteria_scores"] == {
        "binary_criterion": "0/1",
        "percent_criterion": "0-100",
        "five_criterion": "0-5",
    }
    assert schema["overall_conclusion"]


def test_normalize_prompt_config_preserves_imported_criteria_order():
    config = _normalize_prompt_config(
        {
            "system_prompt": "system",
            "general_prompt": "general",
            "include_overall_conclusion": False,
            "default_scoring_system": "0-5",
            "criteria": [
                {
                    "title": "Second",
                    "description": "Second description",
                    "scoring_system": "0-100%",
                    "include_review": True,
                },
                {
                    "title": "First",
                    "description": "First description",
                    "scoring_system": "0/1",
                    "include_review": False,
                },
            ],
        }
    )

    assert config["system_prompt"] == "system"
    assert config["general_prompt"] == "general"
    assert config["include_overall_conclusion"] is False
    assert config["default_scoring_system"] == "five"
    assert [criterion["title"] for criterion in config["criteria"]] == [
        "Second",
        "First",
    ]
    assert [criterion["scoring_system"] for criterion in config["criteria"]] == [
        "percent",
        "binary",
    ]
