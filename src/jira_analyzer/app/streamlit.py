import json
from pathlib import Path

import pandas as pd
import streamlit as st

from jira_analyzer.analyzer.core.llm.prompt_builder import (
    AnalysisPromptConfig,
    CriterionConfig,
)
from jira_analyzer.analyzer.service import AnalysisService
from jira_analyzer.analyzer.engine import get_default_analysis_prompt_config
from jira_analyzer.app.output_handler import build_markdown_report
from jira_analyzer.storage import SqliteAnalysisResultRepository
from jira_analyzer.tasktracker.jira import (
    JiraConnectionConfig,
    fetch_issue,
    jira_issue_to_analysis_input,
    search_issues,
)
from jira_analyzer.tasktracker.jira.jira_parser import load_issues
from jira_analyzer.ui.results_viewer import ResultsViewer
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)


# Page names for navigation
PAGE_ANALYSIS = "analysis"
PAGE_RESULTS = "results"

SCORING_OPTIONS = {
    "0/1": "binary",
    "0-100%": "percent",
    "0-5": "five",
}
SCORING_LABEL_BY_VALUE = {
    value: label for label, value in SCORING_OPTIONS.items()
}

TRANSLATIONS = {
    "en": {
        "language": "Language",
        "english": "English",
        "russian": "Russian",
        "title": "Jira AI Task Linter",
        "caption": "Analyze Jira issues from JSON, a single Jira key, or a JQL query.",
        "settings": "Settings",
        "issue_source": "Issue source",
        "connection": "Connection",
        "jira_server_url": "Jira server URL",
        "jira_username": "Jira username",
        "jira_token": "Jira API token/password",
        "verify_ssl": "Verify SSL",
        "query": "Query",
        "jira_query_mode": "Jira query mode",
        "issue_key": "Issue key",
        "jira_issue_key": "Jira issue key",
        "max_results": "Max results",
        "upload_jira_json": "Upload Jira JSON",
        "use_sample": "Use sample data (data/input.json)",
        "run_analysis": "Run Analysis",
        "worker_count": "Analysis threads",
        "no_issues": "No issues were found.",
        "analyzing": "Analyzing {count} issues via LLM with {workers} workers...",
        "analysis_complete": "Analysis complete.",
        "analysis_error": "An error occurred during analysis: {error}",
        "analysis_prompt": "Analysis prompt",
        "prompt_caption": (
            "Configure the system prompt, general prompt, and any number of "
            "criteria. Each criterion is returned in the JSON result."
        ),
        "system_prompt": "System prompt",
        "general_prompt": "General prompt",
        "include_overall": "Include overall issue conclusion",
        "criteria": "Criteria",
        "criteria_search": "Search criteria",
        "no_matching_criteria": "No criteria match the search.",
        "criterion": "Criterion {number}",
        "select_criterion": "Select criterion",
        "remove": "Delete criterion",
        "delete_selected_criteria": "Delete selected",
        "delete_all_criteria": "Delete all",
        "criterion_name": "Criterion name",
        "criterion_description": "Criterion description",
        "scoring_system": "Scoring system",
        "default_scoring_system": "Scoring system for all criteria",
        "include_criterion_review": "Include criterion review",
        "add_criterion": "Add criterion",
        "prompt_config_io": "Prompt config import/export",
        "export_prompt_config": "Export prompt config",
        "import_prompt_config": "Import prompt config",
        "prompt_config_file": "Prompt config JSON",
        "prompt_config_imported": "Prompt config imported.",
        "invalid_prompt_config": "Invalid prompt config: {error}",
        "jira_server_required": "Jira server URL is required.",
        "jql_required": "JQL query is required.",
        "fetching_jql": "Fetching issues from Jira by JQL...",
        "jira_issue_required": "Jira issue key is required.",
        "fetching_issue": "Fetching {issue} from Jira...",
        "invalid_json": "Invalid format: JSON must be a list of issues.",
        "sample_not_found": "Sample file not found at {path}",
        "markdown_report": "Markdown report",
        "table": "Table",
        "details": "Details",
        "download_json": "Download JSON",
        "download_markdown": "Download Markdown",
        "issue": "Issue {number}: {name}",
        "failed_issue": "Failed to analyze this issue: {error}",
        "original_description": "Original Description",
        "no_description": "No description provided",
        "verdict": "Verdict",
        "criteria_breakdown": "Criteria Breakdown",
        "diagnosis": "Diagnosis",
        "no_diagnosis": "No diagnosis available",
        "criteria_reviews": "Criteria Reviews",
        "overall_conclusion": "Overall Conclusion",
        "recommendations": "Recommendations",
        "no_recommendations": "No recommendations available",
        "exclude_closed": "Exclude closed tasks",
        "include_closed_tasks": "Include closed tasks",
        "data_selection": "Data Selection",
        "analysis_execution_settings": "Analysis Execution Settings",
        "split_by_criterion": "Analyze each criterion separately",
        "split_by_criterion_help": "When enabled, each criterion is analyzed in a separate LLM request. This provides more detailed analysis but takes longer.",
        "page_analysis": "Analysis",
        "page_results": "Results",
        "navigation": "Navigation",
        "results_viewer_title": "Analysis Results",
        "results_viewer_caption": "Browse and view detailed analysis results from SQLite database.",
        "results_list": "Results List",
        "search_results": "Search Results",
        "filter_by_status": "Filter by Status",
        "minimum_score": "Minimum Score",
        "no_matching_results": "No results match your search criteria.",
        "view_details": "View Details",
        "issue_title": "{id}: {title}",
        "result_details": "Result Details",
        "task_id": "Task ID",
        "status": "Status",
        "quality_score": "Quality Score",
        "assignee": "Assignee",
        "created_at": "Created At",
        "analyzed_at": "Analyzed At",
        "issue_summary_heading": "Issue Summary",
        "analysis_results": "Analysis Results",
        "no_analysis_data": "No analysis data available.",
        "score": "Score",
        "review": "Review",
        "results_loading_error": "Error loading results: {error}",
        "result_not_found": "Result not found: {id}",
        "no_analysis_results": "No analysis results found in the database. Run an analysis first."
    },
    "ru": {
        "language": "Язык",
        "english": "Английский",
        "russian": "Русский",
        "title": "Jira AI анализатор задач",
        "caption": "Анализируйте Jira-задачи из JSON, по ключу задачи или через JQL.",
        "settings": "Настройки",
        "issue_source": "Источник задач",
        "connection": "Подключение",
        "jira_server_url": "URL сервера Jira",
        "jira_username": "Пользователь Jira",
        "jira_token": "API токен/пароль Jira",
        "verify_ssl": "Проверять SSL",
        "query": "Запрос",
        "jira_query_mode": "Режим запроса Jira",
        "issue_key": "Ключ задачи",
        "jira_issue_key": "Ключ задачи Jira",
        "max_results": "Максимум результатов",
        "upload_jira_json": "Загрузить Jira JSON",
        "use_sample": "Использовать пример (data/input.json)",
        "run_analysis": "Запустить анализ",
        "worker_count": "Количество потоков анализа",
        "no_issues": "Задачи не найдены.",
        "analyzing": "Анализируем задач через LLM: {count}, потоков: {workers}...",
        "analysis_complete": "Анализ завершён.",
        "analysis_error": "Во время анализа произошла ошибка: {error}",
        "analysis_prompt": "Промпт анализа",
        "prompt_caption": (
            "Настройте системный промпт, общий промпт и любое количество "
            "критериев. Каждый критерий возвращается в JSON-результате."
        ),
        "system_prompt": "Системный промпт",
        "general_prompt": "Общий промпт",
        "include_overall": "Добавлять общий вывод по задаче",
        "criteria": "Критерии",
        "criteria_search": "Поиск по критериям",
        "no_matching_criteria": "Критерии по поиску не найдены.",
        "criterion": "Критерий {number}",
        "select_criterion": "Выбрать критерий",
        "remove": "Удалить критерий",
        "delete_selected_criteria": "Удалить выбранные",
        "delete_all_criteria": "Удалить все",
        "criterion_name": "Название критерия",
        "criterion_description": "Описание критерия",
        "scoring_system": "Система оценивания",
        "default_scoring_system": "Система оценивания для всех критериев",
        "include_criterion_review": "Добавлять рецензию по критерию",
        "add_criterion": "Добавить критерий",
        "prompt_config_io": "Импорт/экспорт конфига промпта",
        "export_prompt_config": "Экспортировать конфиг промпта",
        "import_prompt_config": "Импортировать конфиг промпта",
        "prompt_config_file": "JSON конфига промпта",
        "prompt_config_imported": "Конфиг промпта импортирован.",
        "invalid_prompt_config": "Некорректный конфиг промпта: {error}",
        "jira_server_required": "URL сервера Jira обязателен.",
        "jql_required": "JQL-запрос обязателен.",
        "fetching_jql": "Получаем задачи из Jira по JQL...",
        "jira_issue_required": "Ключ задачи Jira обязателен.",
        "fetching_issue": "Получаем {issue} из Jira...",
        "invalid_json": "Некорректный формат: JSON должен быть списком задач.",
        "sample_not_found": "Файл примера не найден: {path}",
        "markdown_report": "Markdown-отчёт",
        "table": "Таблица",
        "details": "Детали",
        "download_json": "Скачать JSON",
        "download_markdown": "Скачать Markdown",
        "issue": "Задача {number}: {name}",
        "failed_issue": "Не удалось проанализировать задачу: {error}",
        "original_description": "Исходное описание",
        "no_description": "Описание отсутствует",
        "verdict": "Вердикт",
        "criteria_breakdown": "Оценки по критериям",
        "diagnosis": "Диагностика",
        "no_diagnosis": "Диагностика отсутствует",
        "criteria_reviews": "Рецензии по критериям",
        "overall_conclusion": "Общий вывод",
        "recommendations": "Рекомендации",
        "no_recommendations": "Рекомендации отсутствуют",
        "exclude_closed": "Исключить закрытые задачи",
        "include_closed_tasks": "Включить закрытые задачи",
        "data_selection": "Выбор данных",
        "analysis_execution_settings": "Настройки выполнения анализа",
        "split_by_criterion": "Анализировать каждый критерий отдельно",
        "split_by_criterion_help": "При включении каждый критерий анализируется в отдельном запросе к ИИ. Это обеспечивает более детальный анализ, но занимает больше времени.",
        "page_analysis": "Анализ",
        "page_results": "Результаты",
        "navigation": "Навигация",
        "results_viewer_title": "Результаты анализа",
        "results_viewer_caption": "Просмотр детализированных результатов анализа из базы данных SQLite.",
        "results_list": "Список результатов",
        "search_results": "Поиск результатов",
        "filter_by_status": "Фильтр по статусу",
        "minimum_score": "Минимальный балл",
        "no_matching_results": "Нет результатов, соответствующих критериям поиска.",
        "view_details": "Просмотр деталей",
        "issue_title": "{id}: {title}",
        "result_details": "Детали результата",
        "task_id": "ID задачи",
        "status": "Статус",
        "quality_score": "Оценка качества",
        "assignee": "Исполнитель",
        "created_at": "Создано",
        "analyzed_at": "Проанализировано",
        "issue_summary_heading": "Сводка по задаче",
        "analysis_results": "Результаты анализа",
        "no_analysis_data": "Нет данных анализа.",
        "score": "Балл",
        "review": "Рецензия",
        "results_loading_error": "Ошибка загрузки результатов: {error}",
        "result_not_found": "Результат не найден: {id}",
        "no_analysis_results": "Нет результатов анализа в базе данных. Сначала выполните анализ."
    }
}

def _select_language():
    language_options = {"en": "English", "ru": "Русский"}
    if "ui_language" not in st.session_state:
        st.session_state.ui_language = "ru"

    current_language = st.session_state.ui_language
    st.sidebar.header(TRANSLATIONS[current_language]["settings"])
    selected_language = st.sidebar.selectbox(
        TRANSLATIONS[current_language]["language"],
        options=list(language_options.keys()),
        format_func=lambda language: language_options[language],
        key="ui_language",
    )

    def translate(key: str, **kwargs) -> str:
        text = TRANSLATIONS[selected_language].get(key, TRANSLATIONS["en"][key])
        return text.format(**kwargs) if kwargs else text

    return translate

def _apply_default_scoring_system_to_criteria() -> None:
    selected_label = st.session_state.analysis_default_scoring_label
    selected_scoring = SCORING_OPTIONS[selected_label]
    st.session_state.analysis_default_scoring_system = selected_scoring
    _set_all_criteria_scoring(
        st.session_state.analysis_criteria,
        selected_scoring,
    )
    _ensure_criteria_ui_ids(st.session_state.analysis_criteria)
    for criterion in st.session_state.analysis_criteria:
        st.session_state[
            _criterion_widget_key(criterion, "criterion_scoring")
        ] = selected_label

def _set_all_criteria_scoring(criteria: list[dict], scoring_system: str) -> None:
    for criterion in criteria:
        criterion["scoring_system"] = scoring_system

def _new_criterion_ui_id() -> str:
    next_id = int(st.session_state.get("next_criterion_ui_id", 1))
    st.session_state.next_criterion_ui_id = next_id + 1
    return f"criterion_{next_id}"

def _ensure_criteria_ui_ids(criteria: list[dict]) -> None:
    for criterion in criteria:
        if not criterion.get("_ui_id"):
            criterion["_ui_id"] = _new_criterion_ui_id()

def _criterion_widget_key(criterion: dict, field: str) -> str:
    ui_id = criterion.get("_ui_id")
    if not ui_id:
        ui_id = _new_criterion_ui_id()
        criterion["_ui_id"] = ui_id
    return f"{field}_{ui_id}"

def _clear_criterion_widget_state() -> None:
    prefixes = (
        "criterion_title_",
        "criterion_description_",
        "criterion_scoring_",
        "criterion_review_",
        "criterion_selected_",
    )
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(prefixes):
            del st.session_state[key]

def _sync_criterion_selection_from_widgets(criteria: list[dict]) -> None:
    _ensure_criteria_ui_ids(criteria)
    for criterion in criteria:
        widget_key = _criterion_widget_key(criterion, "criterion_selected")
        if widget_key in st.session_state:
            criterion["selected"] = bool(st.session_state[widget_key])

def _delete_selected_criteria(criteria: list[dict]) -> int:
    before_count = len(criteria)
    criteria[:] = [
        criterion for criterion in criteria if not criterion.get("selected", False)
    ]
    return before_count - len(criteria)

def _delete_all_criteria(criteria: list[dict]) -> int:
    deleted_count = len(criteria)
    criteria.clear()
    return deleted_count

def _remove_criterion(index: int) -> bool:
    criteria = st.session_state.analysis_criteria
    if index < 0 or index >= len(criteria):
        return False

    criteria.pop(index)
    _clear_criterion_widget_state()
    return True

def _filter_criteria(criteria: list[dict], query: str) -> list[tuple[int, dict]]:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return list(enumerate(criteria))

    filtered = []
    for index, criterion in enumerate(criteria):
        haystack = " ".join(
            [
                str(criterion.get("title", "")),
                str(criterion.get("description", "")),
            ]
        ).lower()
        if normalized_query in haystack:
            filtered.append((index, criterion))
    return filtered

def _sync_criteria_search() -> None:
    st.session_state.criteria_search = st.session_state.criteria_search_input

def _build_prompt_config_export() -> dict:
    return {
        "version": 1,
        "system_prompt": st.session_state.analysis_system_prompt,
        "general_prompt": st.session_state.analysis_general_prompt,
        "include_overall_conclusion": (
            st.session_state.analysis_include_overall_conclusion
        ),
        "default_scoring_system": st.session_state.analysis_default_scoring_system,
        "criteria": [
            {
                "title": str(criterion.get("title", "")),
                "description": str(criterion.get("description", "")),
                "scoring_system": _normalize_scoring_system(
                    criterion.get("scoring_system", "percent")
                ),
                "include_review": bool(criterion.get("include_review", False)),
            }
            for criterion in st.session_state.analysis_criteria
        ],
    }

def _normalize_prompt_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValueError("Root value must be a JSON object.")

    criteria = config.get("criteria")
    if not isinstance(criteria, list):
        raise ValueError("Field 'criteria' must be a list.")

    imported_criteria = []
    for index, criterion in enumerate(criteria, start=1):
        if not isinstance(criterion, dict):
            raise ValueError(f"Criterion {index} must be an object.")
        imported_criteria.append(
            {
                "title": str(criterion.get("title", "")),
                "description": str(criterion.get("description", "")),
                "scoring_system": _normalize_scoring_system(
                    criterion.get("scoring_system", "percent")
                ),
                "include_review": bool(criterion.get("include_review", False)),
                "selected": False,
                "_ui_id": _new_criterion_ui_id(),
            }
        )

    default_scoring_system = _normalize_scoring_system(
        config.get("default_scoring_system", "percent")
    )
    return {
        "system_prompt": str(config.get("system_prompt", "")),
        "general_prompt": str(config.get("general_prompt", "")),
        "include_overall_conclusion": bool(
            config.get("include_overall_conclusion", True)
        ),
        "default_scoring_system": default_scoring_system,
        "criteria": imported_criteria,
    }

def _apply_prompt_config_to_state(config: dict) -> None:
    st.session_state.analysis_system_prompt = config["system_prompt"]
    st.session_state.analysis_general_prompt = config["general_prompt"]
    st.session_state.analysis_include_overall_conclusion = config[
        "include_overall_conclusion"
    ]
    st.session_state.analysis_default_scoring_system = config[
        "default_scoring_system"
    ]
    st.session_state.analysis_default_scoring_label = SCORING_LABEL_BY_VALUE[
        config["default_scoring_system"]
    ]
    st.session_state.analysis_criteria = config["criteria"]
    _ensure_criteria_ui_ids(st.session_state.analysis_criteria)
    _clear_criterion_widget_state()

def _normalize_scoring_system(value) -> str:
    if value in SCORING_LABEL_BY_VALUE:
        return value
    if value in SCORING_OPTIONS:
        return SCORING_OPTIONS[value]
    raise ValueError(f"Unsupported scoring system: {value}")

def _render_results_page(t, force_reload: bool = False) -> None:
    """Render the results viewer page.

    Args:
        t: Translation function.
        force_reload: Whether to force reload results from database.

    New page for viewing SQLite results in master-detail format.
    """
    db_path = st.sidebar.text_input("Database Path", value="data/analysis.db", help="Path to SQLite database for analysis results")

    try:
        repo = SqliteAnalysisResultRepository(db_path)
        viewer = ResultsViewer(repo, t)
        viewer.render(force_reload=force_reload)
    except Exception as error:
        st.error(t("results_loading_error", error=error))
        logger.exception("Results viewer error")

def _render_prompt_editor(t) -> AnalysisPromptConfig:
    with st.expander(t("analysis_prompt"), expanded=False):
        # Integrated Import/Export configuration controls
        st.subheader(t("prompt_config_io"))
        config_json = json.dumps(
            _build_prompt_config_export(),
            ensure_ascii=False,
            indent=2,
        )
        uploaded_config = st.file_uploader(
            t("prompt_config_file"),
            type=["json"],
            key="analysis_prompt_config_upload",
        )
        btn_cols = st.columns(2)
        with btn_cols[0]:
            if st.button(t("import_prompt_config"), disabled=uploaded_config is None, use_container_width=True):
                try:
                    if uploaded_config is not None:
                        st.session_state.pending_analysis_prompt_config = (
                            _normalize_prompt_config(json.load(uploaded_config))
                        )
                        st.rerun()
                except Exception as error:
                    st.error(t("invalid_prompt_config", error=error))
        with btn_cols[1]:
            st.download_button(
                t("export_prompt_config"),
                data=config_json,
                file_name="analysis_prompt_config.json",
                mime="application/json",
                use_container_width=True,
            )

        st.divider()
        
        st.subheader(t("analysis_prompt"))
        
        st.caption(t("prompt_caption"))
        system_prompt = st.text_area(
            t("system_prompt"),
            height=120,
            key="analysis_system_prompt",
        )
        general_prompt = st.text_area(
            t("general_prompt"),
            height=160,
            key="analysis_general_prompt",
        )
        include_overall_conclusion = st.checkbox(
            t("include_overall"),
            key="analysis_include_overall_conclusion",
        )

        st.subheader(t("criteria"))
        st.selectbox(
            t("default_scoring_system"),
            options=list(SCORING_OPTIONS.keys()),
            key="analysis_default_scoring_label",
            on_change=_apply_default_scoring_system_to_criteria,
        )
        criteria_search = st.text_input(
            t("criteria_search"),
            key="criteria_search_input",
            on_change=_sync_criteria_search,
        )

        _sync_criterion_selection_from_widgets(st.session_state.analysis_criteria)

        filtered_criteria = _filter_criteria(
            st.session_state.analysis_criteria,
            criteria_search,
        )
        if criteria_search and not filtered_criteria:
            st.info(t("no_matching_criteria"))

        for index, criterion in filtered_criteria:
            _render_criterion_editor(index, criterion, t)

        action_cols = st.columns([2, 1, 1])
                
        with action_cols[0]:
            if st.button(
                t("add_criterion"), type="secondary", use_container_width=True
            ):
                st.session_state.analysis_criteria.append(
                    {
                        "title": "",
                        "description": "",
                        "scoring_system": st.session_state.analysis_default_scoring_system,
                        "include_review": False,
                        "selected": False,
                        "_ui_id": _new_criterion_ui_id(),
                    }
                )
                st.rerun()
                
        selected_count = sum(
            1
            for criterion in st.session_state.analysis_criteria
            if criterion.get("selected", False)
        )
        with action_cols[1]:
            if st.button(
                t("delete_selected_criteria"),
                disabled=selected_count == 0,
                use_container_width=True
            ):
                _delete_selected_criteria(st.session_state.analysis_criteria)
                _clear_criterion_widget_state()
                st.rerun()
        with action_cols[2]:
            if st.button(
                t("delete_all_criteria"),
                disabled=not st.session_state.analysis_criteria,
                use_container_width=True
            ):
                _delete_all_criteria(st.session_state.analysis_criteria)
                _clear_criterion_widget_state()
                st.rerun()

    criteria = [
        CriterionConfig(
            title=str(criterion.get("title", "")),
            description=str(criterion.get("description", "")),
            scoring_system=criterion.get("scoring_system", "percent"),
            include_review=bool(criterion.get("include_review", False)),
        )
        for criterion in st.session_state.analysis_criteria
    ]
    return AnalysisPromptConfig(
        system_prompt=system_prompt,
        general_prompt=general_prompt,
        criteria=criteria,
        include_overall_conclusion=include_overall_conclusion,
    )

def _ensure_prompt_state() -> None:
    defaults = get_default_analysis_prompt_config()
    if "analysis_system_prompt" not in st.session_state:
        st.session_state.analysis_system_prompt = defaults.system_prompt
    if "analysis_general_prompt" not in st.session_state:
        st.session_state.analysis_general_prompt = defaults.general_prompt
    if "analysis_include_overall_conclusion" not in st.session_state:
        st.session_state.analysis_include_overall_conclusion = (
            defaults.include_overall_conclusion
        )
    if "analysis_default_scoring_system" not in st.session_state:
        st.session_state.analysis_default_scoring_system = "percent"
    if "analysis_default_scoring_label" not in st.session_state:
        st.session_state.analysis_default_scoring_label = SCORING_LABEL_BY_VALUE[
            st.session_state.analysis_default_scoring_system
        ]
    if "criteria_search" not in st.session_state:
        st.session_state.criteria_search = ""
    if "criteria_search_input" not in st.session_state:
        st.session_state.criteria_search_input = st.session_state.criteria_search
    if "analysis_criteria" not in st.session_state:
        st.session_state.analysis_criteria = [
            {
                "title": criterion.title,
                "description": criterion.description,
                "scoring_system": criterion.scoring_system,
                "include_review": criterion.include_review,
                "selected": False,
                "_ui_id": _new_criterion_ui_id(),
            }
            for criterion in defaults.criteria
        ]
    else:
        _ensure_criteria_ui_ids(st.session_state.analysis_criteria)
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "pending_analysis_prompt_config" in st.session_state:
        _apply_prompt_config_to_state(st.session_state.pending_analysis_prompt_config)
        del st.session_state.pending_analysis_prompt_config


def _render_criterion_editor(index: int, criterion: dict, t) -> None:
    with st.container(border=True):
        header_cols = st.columns(
            [0.24, 7.8, 0.55],
            gap="small",
            vertical_alignment="center",
        )
        with header_cols[0]:
            criterion["selected"] = st.checkbox(
                t("select_criterion"),
                value=bool(criterion.get("selected", False)),
                key=_criterion_widget_key(criterion, "criterion_selected"),
                label_visibility="collapsed",
            )
        with header_cols[1]:
            st.write(t("criterion", number=index + 1))
        with header_cols[2]:
            if st.button(
                "❌",
                key=_criterion_widget_key(criterion, "remove_criterion"),
                help=t("remove"),
            ):
                if _remove_criterion(index):
                    st.rerun()

        criterion["title"] = st.text_input(
            t("criterion_name"),
            value=criterion.get("title", ""),
            key=_criterion_widget_key(criterion, "criterion_title"),
        )
        criterion["description"] = st.text_area(
            t("criterion_description"),
            value=criterion.get("description", ""),
            height=100,
            key=_criterion_widget_key(criterion, "criterion_description"),
        )
        cols = st.columns([1, 1], vertical_alignment="bottom")
        with cols[0]:
            current_scoring = criterion.get("scoring_system", "percent")
            current_label = SCORING_LABEL_BY_VALUE.get(current_scoring, "0-100%")
            selected_label = st.selectbox(
                t("scoring_system"),
                options=list(SCORING_OPTIONS.keys()),
                index=list(SCORING_OPTIONS.keys()).index(current_label),
                key=_criterion_widget_key(criterion, "criterion_scoring"),
            )
            criterion["scoring_system"] = SCORING_OPTIONS[selected_label]
        with cols[1]:
            st.write("")
            criterion["include_review"] = st.checkbox(
                t("include_criterion_review"),
                value=bool(criterion.get("include_review", False)),
                key=_criterion_widget_key(criterion, "criterion_review"),
            )

def _load_issues(
    *,
    t,
    source: str,
    uploaded_file,
    use_sample: bool,
    jira_server: str,
    jira_query_mode: str,
    jira_issue: str,
    jira_jql: str,
    jira_username: str,
    jira_token: str,
    jira_verify_ssl: bool,
    jira_max_results: int,
    exclude_closed: bool = True,
) -> list[dict]:
    if source == "JSON":
        return _load_json_issues(uploaded_file, use_sample, t)

    if not jira_server:
        raise ValueError(t("jira_server_required"))

    config = JiraConnectionConfig(
        server=jira_server,
        username=jira_username or None,
        token=jira_token or None,
        verify_ssl=jira_verify_ssl,
    )

    if jira_query_mode == "JQL":
        if not jira_jql.strip():
            raise ValueError(t("jql_required"))
        with st.spinner(t("fetching_jql")):
            issues = [
                jira_issue_to_analysis_input(issue)
                for issue in search_issues(
                    jira_jql,
                    config,
                    max_results=jira_max_results,
                )
            ]
            if exclude_closed:
                issues = [issue for issue in issues if not _is_closed_status_streamlit(issue)]
            return issues

    if not jira_issue:
        raise ValueError(t("jira_issue_required"))
    with st.spinner(t("fetching_issue", issue=jira_issue)):
        issue = jira_issue_to_analysis_input(fetch_issue(jira_issue, config))
        if exclude_closed and _is_closed_status_streamlit(issue):
            raise ValueError(f"Issue {jira_issue} is closed and excluded from analysis.")
        return [issue]

def _load_json_issues(uploaded_file, use_sample: bool, t) -> list[dict]:
    if uploaded_file is not None:
        data = json.load(uploaded_file)
        if not isinstance(data, list):
            raise ValueError(t("invalid_json"))
        return data

    if use_sample:
        project_root = Path(__file__).resolve().parents[3]
        sample_path = project_root / "data" / "input.json"
        if not sample_path.exists():
            raise FileNotFoundError(t("sample_not_found", path=sample_path))
        return load_issues(str(sample_path))

    return []

def _extract_criterion_scores(result: dict) -> list:
    criteria = result.get("criteria")
    if isinstance(criteria, dict) and criteria:
        scores = []
        for criterion_result in criteria.values():
            if isinstance(criterion_result, dict) and "score" in criterion_result:
                scores.append(criterion_result["score"])
        if scores:
            return scores

    scores = result.get("criteria_scores")
    if isinstance(scores, dict) and scores:
        return list(scores.values())

    return []

def _build_results_table(results: list[dict]) -> pd.DataFrame:
    rows = []
    for index, result in enumerate(results, start=1):
        row = {
            "jira_key": result.get("jira_key") or result.get("key") or f"Issue {index}",
            "input_element_type": result.get("input_element_type", "N/A"),
        }
        if "verdict" in result:
            row["verdict"] = result["verdict"]
        if "overall_conclusion" in result:
            row["overall_conclusion"] = result["overall_conclusion"]

        for score_index, score in enumerate(_extract_criterion_scores(result), start=1):
            row[f"К{score_index}"] = score

        rows.append(row)

    return pd.DataFrame(rows)

def _is_closed_status_streamlit(issue: dict) -> bool:
    status = issue.get("status", "").lower()
    closed_statuses = {"closed", "done", "resolved", "cancelled"}
    return status in closed_statuses

def _render_results(results: list[dict], t) -> None:
    markdown_report = build_markdown_report(results)

    report_tab, json_tab = st.tabs(
        [t("markdown_report"), "JSON", ]
    )

    with report_tab:
        st.markdown(markdown_report)
        st.download_button(
            t("download_markdown"),
            data=markdown_report,
            file_name="analysis_report.md",
            mime="text/markdown",
        )

    with json_tab:
        st.json(results)
        st.download_button(
            t("download_json"),
            data=json.dumps(results, ensure_ascii=False, indent=2),
            file_name="analysis_result.json",
            mime="application/json",
        )

    st.divider()

def main() -> None:
    """Main application entry point with page navigation."""
    st.set_page_config(
        page_title="Jira AI Linter",
        page_icon="J",
        layout="wide",
    )
    t = _select_language()

    # Page navigation
    page = st.sidebar.radio(
        t("navigation"),
        options=[PAGE_ANALYSIS, PAGE_RESULTS],
        format_func=lambda x: t(f"page_{x}"),
        horizontal=True,
    )

    # Track page transitions for results reload
    previous_page = st.session_state.get("previous_page")
    is_entering_results_page = page == PAGE_RESULTS and previous_page != PAGE_RESULTS
    st.session_state.previous_page = page

    # Route to appropriate page
    if page == PAGE_RESULTS:
        st.title(t("results_viewer_title"))
        st.caption(t("results_viewer_caption"))
        _render_results_page(t, force_reload=is_entering_results_page)
    else:
        # Analysis page - Refactored main() implementation
        # Main area: Complete analysis pipeline
        # Sidebar: Advanced settings only

        # SIDEBAR: Advanced settings (keep in sidebar)
        with st.sidebar.expander(t("connection"), expanded=False):
            jira_server = st.text_input(
                t("jira_server_url"),
                value="http://127.0.0.1:8081",
            )
            jira_username = st.text_input(t("jira_username"))
            jira_token = st.text_input(t("jira_token"), type="password")
            jira_verify_ssl = st.checkbox(t("verify_ssl"), value=False)
            jira_max_results = st.number_input(
                t("max_results"),
                min_value=1,
                max_value=200,
                value=50,
                step=1,
            )

        db_path = st.sidebar.text_input("Database Path", value="data/analysis.db", help="Path to SQLite database for intermediate results")

        # MAIN AREA: Complete analysis pipeline

        # Section 1: Data selection
        st.header(t("data_selection"))
        source = st.radio(t("issue_source"), ["Jira", "JSON"], horizontal=True)

        uploaded_file = None
        use_sample = False
        jira_issue = ""
        jira_jql = ""
        jira_query_mode = "Issue key"
        exclude_closed = True

        if source == "Jira":
            st.subheader(t("query"))
            jira_query_mode = st.radio(
                t("jira_query_mode"),
                ["Issue key", "JQL"],
                horizontal=True,
                format_func=lambda value: t("issue_key") if value == "Issue key" else value,
            )
            if jira_query_mode == "Issue key":
                jira_issue = st.text_input(t("jira_issue_key"), value="YA-1")
            else:
                jira_jql = st.text_area(
                    "JQL",
                    value="project = YA",
                    height=100,
                )

            exclude_closed = st.checkbox(
                t("exclude_closed"),
                value=True,
            )
        else:
            uploaded_file = st.file_uploader(t("upload_jira_json"), type=["json"])
            use_sample = st.checkbox(
                t("use_sample"),
                value=not uploaded_file,
            )

        st.divider()

        # Section 2: Analysis configuration (prompt settings)
        _ensure_prompt_state()
        prompt_config = _render_prompt_editor(t)

        st.divider()

        # Section 3: Analysis execution settings
        st.header(t("analysis_execution_settings"))
        worker_count = st.slider(
            t("worker_count"),
            min_value=1,
            max_value=10,
            value=4,
            step=1,
        )
        split_by_criterion = st.checkbox(
            t("split_by_criterion"),
            value=False,
            help=t("split_by_criterion_help"),
        )

        st.divider()

        # Section 4: Run analysis button
        if st.button(t("run_analysis"), type="primary"):
            st.session_state.analysis_results = None
            try:
                issues = _load_issues(
                    t=t,
                    source=source,
                    uploaded_file=uploaded_file,
                    use_sample=use_sample,
                    jira_server=jira_server,
                    jira_query_mode=jira_query_mode,
                    jira_issue=jira_issue,
                    jira_jql=jira_jql,
                    jira_username=jira_username,
                    jira_token=jira_token,
                    jira_verify_ssl=jira_verify_ssl,
                    jira_max_results=int(jira_max_results),
                    exclude_closed=exclude_closed,
                )
                if not issues:
                    st.warning(t("no_issues"))
                    return

                with st.spinner(
                    t("analyzing", count=len(issues), workers=int(worker_count))
                ):
                    repo = SqliteAnalysisResultRepository(db_path)
                    
                    # Create a meaningful run name based on analysis type
                    if source == "Jira":
                        if jira_query_mode == "Issue key":
                            run_name = f"Issue Analysis: {jira_issue}"
                        else:
                            run_name = f"JQL Analysis: {jira_jql[:50]}..."
                    else:
                        run_name = "JSON Dataset Analysis"
                    
                    # Create analysis service first to get run_id
                    service = AnalysisService(
                        prompt_config=prompt_config,
                        worker_count=int(worker_count),
                        split_by_criterion=split_by_criterion,
                        repo=repo,
                    )
                    
                    # Create analysis run and get run_id
                    run_id = service.create_analysis_run(run_name=run_name)
                    st.session_state.current_run_id = run_id
                    
                    # Perform analysis using the service with run_id
                    results = service.analyze_issues(issues)

                st.session_state.analysis_results = results
                st.success(t("analysis_complete"))
            except Exception as error:
                st.error(t("analysis_error", error=error))
                logger.exception("UI analysis error")

        if st.session_state.analysis_results:
            _render_results(st.session_state.analysis_results, t)

if __name__ == "__main__":
    main()
