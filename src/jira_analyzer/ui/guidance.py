"""Streamlit user guidance component.

This module provides simple guidance system with tooltips and
help text for Streamlit widgets.
"""

from typing import Dict
import streamlit as st
from jira_analyzer.i18n import get_text


# Hardcoded guidance strings (EN/RU only) - no complex infrastructure
GUIDANCE_TEXTS: Dict[str, Dict[str, str]] = {
    "en": {
        "jql_help": "Use JQL to filter tasks. Example: `status = Open AND priority = High'",
        "task_analysis_help": "Analyze individual task quality using AI.",
        "batch_analysis_help": "Analyze multiple tasks at once.",
        "quality_threshold_help": "Minimum quality score (1-10).",
        "model_selection_help": "Choose AI model: gpt-4 for quality, gpt-3.5 for speed.",
    },
    "ru": {
        "jql_help": "Используйте JQL для фильтрации задач. Пример: `status = Open AND priority = High'",
        "task_analysis_help": "Анализ качества отдельной задачи с помощью ИИ.",
        "batch_analysis_help": "Анализ нескольких задач одновременно.",
        "quality_threshold_help": "Минимальная оценка качества (1-10).",
        "model_selection_help": "Выберите модель ИИ: gpt-4 для качества, gpt-3.5 для скорости.",
    },
}


def get_guidance(key: str, language: str = "en") -> str:
    """Get guidance text string by key.

    Args:
        key: Guidance text key
        language: Language code ("en" or "ru")

    Returns:
        Guidance text string, or "[missing:key]" if not found

    Note:
        Simple dictionary lookup with fallback behavior.
    """
    # Fallback to English if language not supported
    if language not in GUIDANCE_TEXTS:
        language = "en"

    # Return "[missing:key]" if key not found
    if key not in GUIDANCE_TEXTS[language]:
        return f"[missing:{key}]"

    return GUIDANCE_TEXTS[language][key]


def guided_text_input(
    label_key: str,
    help_key: str,
    language: str = "en",
    **kwargs
) -> str:
    """Create text input with help tooltip.

    Args:
        label_key: Translation key for label
        help_key: Guidance key for help text
        language: Language code
        **kwargs: Additional arguments for st.text_input

    Returns:
        User input value
    """
    return st.text_input(
        label=get_text(label_key, language),
        help=get_guidance(help_key, language),
        **kwargs
    )


def guided_selectbox(
    label_key: str,
    help_key: str,
    options: list,
    language: str = "en",
    **kwargs
) -> str:
    """Create selectbox with help tooltip.

    Args:
        label_key: Translation key for label
        help_key: Guidance key for help text
        options: List of options
        language: Language code
        **kwargs: Additional arguments for st.selectbox

    Returns:
        Selected value
    """
    return st.selectbox(
        label=get_text(label_key, language),
        options=options,
        help=get_guidance(help_key, language),
        **kwargs
    )


def guided_slider(
    label_key: str,
    help_key: str,
    language: str = "en",
    **kwargs
) -> int:
    """Create slider with help tooltip.

    Args:
        label_key: Translation key for label
        help_key: Guidance key for help text
        language: Language code
        **kwargs: Additional arguments for st.slider

    Returns:
        Selected integer value
    """
    return st.slider(
        label=get_text(label_key, language),
        help=get_guidance(help_key, language),
        **kwargs
    )


def guided_button(
    label_key: str,
    help_key: str,
    language: str = "en",
    **kwargs
) -> bool:
    """Create button with help text below.

    Note: Streamlit buttons don't support help parameter directly.
    We add help text below the button instead.

    Args:
        label_key: Translation key for label
        help_key: Guidance key for help text
        language: Language code
        **kwargs: Additional arguments for st.button

    Returns:
        True if button was clicked, False otherwise
    """
    button_label = get_text(label_key, language)
    result = st.button(button_label, **kwargs)
    help_text = get_guidance(help_key, language)
    st.info(f"💡 {help_text}")
    return result
