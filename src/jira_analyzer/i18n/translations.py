"""Hardcoded translations for Jira Analyzer.

This module provides simple dictionary-based translation support
for English and Russian languages. No external file loading or
complex translation infrastructure - just basic string lookup.
"""

from typing import Dict

# Hardcoded translations - no loading from files
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Main UI
        "app_title": "Jira AI Analyzer",
        "start_analysis": "Start Analysis",
        "results": "Results",

        # Input fields
        "jql_query": "JQL Query",
        "enter_jql": "Enter JIRA Query Language query...",
        "analysis_type": "Analysis Type",
        "select_analysis": "Select analysis type...",

        # Results
        "task_id": "Task ID",
        "task_title": "Task Title",
        "quality_score": "Quality Score",
        "rationale": "Rationale",
        "no_results": "No results found",

        # Settings
        "settings": "Settings",
        "language": "Language",
        "issue_source": "Issue Source",
        "connection": "Connection",
        "jira_query_mode": "Jira Query Mode",
        "upload_jira_json": "Upload Jira JSON",
        "use_sample": "Use Sample Data",
        "worker_count": "Worker Count",
        "run_analysis": "Run Analysis",

        # Errors
        "error_title": "Error",
        "jira_connection_error": "Failed to connect to Jira",
        "config_error": "Configuration error",
    },
    "ru": {
        # Main UI
        "app_title": "AI Анализатор Jira",
        "start_analysis": "Начать анализ",
        "results": "Результаты",

        # Input fields
        "jql_query": "JQL Запрос",
        "enter_jql": "Введите запрос JIRA Query Language...",
        "analysis_type": "Тип анализа",
        "select_analysis": "Выберите тип анализа...",

        # Results
        "task_id": "ID Задачи",
        "task_title": "Название задачи",
        "quality_score": "Оценка качества",
        "rationale": "Обоснование",
        "no_results": "Результаты не найдены",

        # Settings
        "settings": "Настройки",
        "language": "Язык",
        "issue_source": "Источник задач",
        "connection": "Подключение",
        "jira_query_mode": "Режим JQL запроса",
        "upload_jira_json": "Загрузить Jira JSON",
        "use_sample": "Использовать примеры",
        "worker_count": "Количество потоков",
        "run_analysis": "Запустить анализ",

        # Errors
        "error_title": "Ошибка",
        "jira_connection_error": "Не удалось подключиться к Jira",
        "config_error": "Ошибка конфигурации",
    },
}


def get_text(key: str, language: str = "en") -> str:
    """Get translated text string by key.

    Args:
        key: Translation key (e.g., "app_title")
        language: Language code ("en" or "ru")

    Returns:
        Translated string, or "[missing:key]" if not found

    Example:
        >>> get_text("app_title", "en")
        'Jira AI Analyzer'
        >>> get_text("app_title", "ru")
        'AI Анализатор Jira'
    """
    # Fallback to English if language not supported
    if language not in TRANSLATIONS:
        language = "en"

    # Return "[missing:key]" if key not found
    if key not in TRANSLATIONS[language]:
        return f"[missing:{key}]"

    return TRANSLATIONS[language][key]


def set_language(language: str) -> None:
    """Validate and set active language.

    Args:
        language: Language code ("en" or "ru")

    Raises:
        ValueError: If language is not supported

    Example:
        >>> set_language("ru")  # Works
        >>> set_language("fr")  # Raises ValueError
    """
    if language not in TRANSLATIONS:
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Supported languages: {', '.join(TRANSLATIONS.keys())}"
        )
