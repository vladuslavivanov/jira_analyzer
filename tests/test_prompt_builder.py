from __future__ import annotations

import json
import re

from jira_analyzer.analyzer.core.llm.prompt_builder import (
    AnalysisPromptConfig,
    CriterionConfig,
    build_structured_prompt,
)
from jira_analyzer.app.streamlit import (
    SCORING_LABEL_BY_VALUE,
    _apply_prompt_config_to_state,
    _build_results_table,
    _delete_all_criteria,
    _delete_selected_criteria,
    _extract_criterion_scores,
    _filter_criteria,
    _normalize_prompt_config,
    _set_all_criteria_scoring,
    _sync_criterion_selection_from_widgets,
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


def test_sync_criterion_selection_from_widget_state(monkeypatch):
    from jira_analyzer.app import streamlit

    criteria = [
        {"title": "First", "selected": False, "_ui_id": "first"},
        {"title": "Second", "selected": False, "_ui_id": "second"},
    ]

    monkeypatch.setitem(streamlit.st.session_state, "criterion_selected_first", True)
    monkeypatch.setitem(streamlit.st.session_state, "criterion_selected_second", False)

    _sync_criterion_selection_from_widgets(criteria)

    assert [criterion["selected"] for criterion in criteria] == [True, False]


def test_sync_criterion_selection_ignores_stale_index_widget_state(monkeypatch):
    from jira_analyzer.app import streamlit

    criteria = [
        {"title": "First", "selected": False, "_ui_id": "stable_first"},
        {"title": "Second", "selected": False, "_ui_id": "stable_second"},
    ]

    monkeypatch.setitem(streamlit.st.session_state, "criterion_selected_0", True)
    monkeypatch.setitem(streamlit.st.session_state, "criterion_selected_stable_second", True)

    _sync_criterion_selection_from_widgets(criteria)
    _delete_selected_criteria(criteria)

    assert [criterion["title"] for criterion in criteria] == ["First"]


def test_prompt_config_import_replaces_existing_criteria(monkeypatch):
    from jira_analyzer.app import streamlit

    monkeypatch.setitem(
        streamlit.st.session_state,
        "analysis_criteria",
        [
            {"title": "Old first", "description": "Old", "_ui_id": "old_first"},
            {"title": "Old second", "description": "Old", "_ui_id": "old_second"},
        ],
    )
    config = _normalize_prompt_config(
        {
            "system_prompt": "system",
            "general_prompt": "general",
            "include_overall_conclusion": True,
            "default_scoring_system": "percent",
            "criteria": [
                {
                    "title": "Imported only",
                    "description": "Imported description",
                    "scoring_system": "binary",
                    "include_review": True,
                }
            ],
        }
    )

    _apply_prompt_config_to_state(config)

    assert [criterion["title"] for criterion in streamlit.st.session_state.analysis_criteria] == [
        "Imported only"
    ]
    assert streamlit.st.session_state.analysis_criteria[0]["_ui_id"] != "old_first"


def test_extract_criterion_scores_prefers_detailed_scores():
    result = {
        "criteria": {
            "criterion_1": {"score": 0, "title": "First"},
            "criterion_2": {"score": 80, "title": "Second"},
        },
        "criteria_scores": {
            "criterion_1": "0/1",
            "criterion_2": "0-100",
        },
    }

    assert _extract_criterion_scores(result) == [0, 80]


def test_build_results_table_adds_criterion_columns():
    table = _build_results_table(
        [
            {
                "jira_key": "YA-1",
                "input_element_type": "Risk",
                "criteria": {
                    "criterion_1": {"score": 1},
                    "criterion_2": {"score": 30},
                },
                "overall_conclusion": "Needs work.",
            }
        ]
    )

    assert list(table.columns) == [
        "jira_key",
        "input_element_type",
        "overall_conclusion",
        "К1",
        "К2",
    ]
    assert table.iloc[0].to_dict() == {
        "jira_key": "YA-1",
        "input_element_type": "Risk",
        "overall_conclusion": "Needs work.",
        "К1": 1,
        "К2": 30,
    }


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


def test_structured_prompt_uses_unique_keys_for_cyrillic_criteria():
    config = AnalysisPromptConfig(
        system_prompt="system",
        general_prompt="general",
        criteria=[
            CriterionConfig(
                title="Полнота",
                description="Первый критерий.",
                scoring_system="binary",
            ),
            CriterionConfig(
                title="Измеримость",
                description="Второй критерий.",
                scoring_system="percent",
            ),
            CriterionConfig(
                title="Соответствие типу",
                description="Третий критерий.",
                scoring_system="five",
            ),
        ],
        include_overall_conclusion=False,
    )

    prompt = build_structured_prompt("Risk", "Description", config)
    schema_match = re.search(r"JSON schema to follow:\n(\{.*\})\s*$", prompt, re.S)

    assert schema_match is not None
    schema = json.loads(schema_match.group(1))
    assert list(schema["criteria"]) == [
        "criterion_1",
        "criterion_2",
        "criterion_3",
    ]
    assert schema["criteria"]["criterion_1"]["title"] == "Полнота"
    assert schema["criteria"]["criterion_2"]["title"] == "Измеримость"
    assert schema["criteria"]["criterion_3"]["title"] == "Соответствие типу"
    assert schema["criteria_scores"] == {
        "criterion_1": "0/1",
        "criterion_2": "0-100",
        "criterion_3": "0-5",
    }


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
