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
        "caption": "Analyze Jira issues from JSON, a single Jira key, or a JQL query.",
        "analysis_tab": "Analysis",
        "results_tab": "Results",
        "start_analysis": "Start Analysis",
        "results": "Results",

        # Database section
        "database_settings": "Database Settings",
        "database_path": "Database Path",
        "database_path_help": "Path to SQLite database for analysis results",

        # Data source section
        "data_source": "Data Source",
        "select_data_source": "Select data source",
        "select_data_source_help": "Choose JSON file upload or Jira connection",

        # Prompt configuration section
        "prompt_configuration": "Prompt Configuration",
        "system_prompt_help": "Define AI system behavior and role",
        "general_prompt_help": "General instructions for issue analysis",
        "criteria_help": "Define quality criteria for issue evaluation",
        "prompt_config_io": "Prompt Config Import/Export",
        "export_prompt_config": "Export Configuration",
        "download_json": "Download JSON",
        "prompt_config_file": "Upload Configuration File",
        "prompt_config_imported": "Configuration imported successfully",
        "invalid_prompt_config": "Invalid configuration: {error}",
        "analysis_prompt": "Analysis Prompts",
        "prompt_caption": "Configure system and general prompts for AI analysis",
        "system_prompt": "System Prompt",
        "general_prompt": "General Prompt",
        "include_overall": "Include Overall Conclusion",
        "criteria": "Quality Criteria",
        "criterion": "Criterion {number}",
        "criterion_name": "Criterion Name",
        "criterion_description": "Description",
        "scoring_system": "Scoring System",
        "include_criterion_review": "Include Detailed Review",

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
        "split_by_criterion": "Split by Criterion",
        "split_by_criterion_help": "Analyze each quality criterion separately",
        "analyzing": "Analyzing {count} issues with {workers} workers...",
        "analysis_complete": "Analysis completed successfully",
        "analysis_error": "Analysis failed: {error}",
        "no_issues": "No issues found to analyze",
        "markdown_report": "Analysis Report",
        "jira_issue_key": "Jira Issue Key",

        # Errors
        "error_title": "Error",
        "jira_connection_error": "Failed to connect to Jira",
        "config_error": "Configuration error",
    },
    "ru": {
        # Main UI
        "app_title": "AI Анализатор Jira",
        "caption": "Анализируйте Jira-задачи из JSON, по ключу задачи или через JQL.",
        "analysis_tab": "Анализ",
        "results_tab": "Результаты",
        "start_analysis": "Начать анализ",
        "results": "Результаты",

        # Database section
        "database_settings": "Настройки базы данных",
        "database_path": "Путь к базе данных",
        "database_path_help": "Путь к базе данных SQLite для результатов анализа",

        # Data source section  
        "data_source": "Источник данных",
        "select_data_source": "Выберите источник данных",
        "select_data_source_help": "Выберите загрузку JSON или подключение к Jira",

        # Prompt configuration section  
        "prompt_configuration": "Конфигурация промпта",
        "system_prompt_help": "Определите поведение и роль ИИ",
        "general_prompt_help": "Общие инструкции для анализа задач",
        "criteria_help": "Определите критерии качества для оценки задач",
        "prompt_config_io": "Импорт/Экспорт конфигурации",
        "export_prompt_config": "Экспорт конфигурации",
        "download_json": "Скачать JSON",
        "prompt_config_file": "Загрузить файл конфигурации",
        "prompt_config_imported": "Конфигурация импортирована успешно",
        "invalid_prompt_config": "Неверная конфигурация: {error}",
        "analysis_prompt": "Промпты анализа",
        "prompt_caption": "Настройте системные и общие промпты для ИИ анализа",
        "system_prompt": "Системный промпт",
        "general_prompt": "Общий промпт",
        "include_overall": "Включить общий вывод",
        "criteria": "Критерии качества",
        "criterion": "Критерий {number}",
        "criterion_name": "Название критерия",
        "criterion_description": "Описание",
        "scoring_system": "Система оценки",
        "include_criterion_review": "Включить подробный обзор",

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
        "split_by_criterion": "Разбить по критерию",
        "split_by_criterion_help": "Анализировать каждый критерий качества отдельно",
        "analyzing": "Анализ {count} задач с {workers} потоками...",
        "analysis_complete": "Анализ завершен успешно",
        "analysis_error": "Анализ не удался: {error}",
        "no_issues": "Не найдено задач для анализа",
        "markdown_report": "Отчет об анализе",
        "jira_issue_key": "Ключ задачи Jira",

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
