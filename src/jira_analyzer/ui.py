import json
from pathlib import Path

import pandas as pd
import streamlit as st

from jira_analyzer.analyzer.core.llm.prompt_builder import (
    AnalysisPromptConfig,
    CriterionConfig,
)
from jira_analyzer.analyzer.engine import (
    get_default_analysis_prompt_config,
    get_default_prompt_template,
    run_analysis,
)
from jira_analyzer.app.output_handler import build_markdown_report
from jira_analyzer.tasktracker.jira import (
    JiraConnectionConfig,
    fetch_issue,
    jira_issue_to_analysis_input,
    search_issues,
)
from jira_analyzer.tasktracker.jira.jira_parser import load_issues
from jira_analyzer.utils.logger import setup_logger

logger = setup_logger(__name__)

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
        "criterion": "Criterion {number}",
        "move_up": "Up",
        "move_down": "Down",
        "remove": "Remove",
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
        "legacy_raw_prompt": "Legacy raw prompt",
        "default_legacy_prompt": "Default legacy prompt",
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
        "overall_score": "Overall Score",
        "verdict": "Verdict",
        "criteria_breakdown": "Criteria Breakdown",
        "diagnosis": "Diagnosis",
        "no_diagnosis": "No diagnosis available",
        "criteria_reviews": "Criteria Reviews",
        "overall_conclusion": "Overall Conclusion",
        "recommendations": "Recommendations",
        "no_recommendations": "No recommendations available",
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
        "criterion": "Критерий {number}",
        "move_up": "Выше",
        "move_down": "Ниже",
        "remove": "Удалить",
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
        "legacy_raw_prompt": "Старый сырой промпт",
        "default_legacy_prompt": "Старый промпт по умолчанию",
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
        "overall_score": "Общая оценка",
        "verdict": "Вердикт",
        "criteria_breakdown": "Оценки по критериям",
        "diagnosis": "Диагностика",
        "no_diagnosis": "Диагностика отсутствует",
        "criteria_reviews": "Рецензии по критериям",
        "overall_conclusion": "Общий вывод",
        "recommendations": "Рекомендации",
        "no_recommendations": "Рекомендации отсутствуют",
    },
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
    for index in range(len(st.session_state.analysis_criteria)):
        st.session_state[f"criterion_scoring_{index}"] = selected_label


def _set_all_criteria_scoring(criteria: list[dict], scoring_system: str) -> None:
    for criterion in criteria:
        criterion["scoring_system"] = scoring_system


def _clear_criterion_widget_state() -> None:
    prefixes = (
        "criterion_title_",
        "criterion_description_",
        "criterion_scoring_",
        "criterion_review_",
    )
    for key in list(st.session_state.keys()):
        if key.startswith(prefixes):
            del st.session_state[key]


def _move_criterion(index: int, direction: int) -> None:
    criteria = st.session_state.analysis_criteria
    target_index = index + direction
    if target_index < 0 or target_index >= len(criteria):
        return

    criteria[index], criteria[target_index] = criteria[target_index], criteria[index]
    _clear_criterion_widget_state()


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
    _clear_criterion_widget_state()


def _normalize_scoring_system(value) -> str:
    if value in SCORING_LABEL_BY_VALUE:
        return value
    if value in SCORING_OPTIONS:
        return SCORING_OPTIONS[value]
    raise ValueError(f"Unsupported scoring system: {value}")


def main() -> None:
    st.set_page_config(
        page_title="Jira AI Linter",
        page_icon="J",
        layout="wide",
    )
    t = _select_language()
    st.title(t("title"))
    st.caption(t("caption"))
    source = st.sidebar.radio(t("issue_source"), ["Jira", "JSON"], horizontal=True)
    worker_count = st.sidebar.number_input(
        t("worker_count"),
        min_value=1,
        value=1,
        step=1,
    )

    prompt_config = _render_prompt_editor(t)

    uploaded_file = None
    use_sample = False
    jira_server = ""
    jira_issue = ""
    jira_jql = ""
    jira_username = ""
    jira_token = ""
    jira_verify_ssl = True
    jira_query_mode = "Issue key"
    jira_max_results = 50

    if source == "Jira":
        with st.sidebar.expander(t("connection"), expanded=False):
            jira_server = st.text_input(
                t("jira_server_url"),
                value="http://127.0.0.1:8081",
            )
            jira_username = st.text_input(t("jira_username"))
            jira_token = st.text_input(t("jira_token"), type="password")
            jira_verify_ssl = st.checkbox(t("verify_ssl"), value=False)

        st.sidebar.subheader(t("query"))
        jira_query_mode = st.sidebar.radio(
            t("jira_query_mode"),
            ["Issue key", "JQL"],
            horizontal=True,
            format_func=lambda value: t("issue_key") if value == "Issue key" else value,
        )
        if jira_query_mode == "Issue key":
            jira_issue = st.sidebar.text_input(t("jira_issue_key"), value="YA-1")
        else:
            jira_jql = st.sidebar.text_area(
                "JQL",
                value="project = YA",
                height=100,
            )
            jira_max_results = st.sidebar.number_input(
                t("max_results"),
                min_value=1,
                max_value=200,
                value=50,
                step=1,
            )
    else:
        uploaded_file = st.sidebar.file_uploader(t("upload_jira_json"), type=["json"])
        use_sample = st.sidebar.checkbox(
            t("use_sample"),
            value=not uploaded_file,
        )

    if st.button(t("run_analysis"), type="primary"):
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
            )
            if not issues:
                st.warning(t("no_issues"))
                return

            with st.spinner(
                t("analyzing", count=len(issues), workers=int(worker_count))
            ):
                results = run_analysis(
                    issues,
                    prompt_config=prompt_config,
                    worker_count=int(worker_count),
                )

            st.success(t("analysis_complete"))
            _render_results(results, t)
        except Exception as error:
            st.error(t("analysis_error", error=error))
            logger.exception("UI analysis error")


def _render_prompt_editor(t) -> AnalysisPromptConfig:
    _ensure_prompt_state()

    with st.expander(t("analysis_prompt"), expanded=True):
        _render_prompt_config_io(t)

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

        for index, criterion in enumerate(st.session_state.analysis_criteria):
            _render_criterion_editor(index, criterion, t)

        if st.button(t("add_criterion"), type="secondary"):
            st.session_state.analysis_criteria.append(
                {
                    "title": "",
                    "description": "",
                    "scoring_system": st.session_state.analysis_default_scoring_system,
                    "include_review": False,
                }
            )
            st.rerun()

        with st.expander(t("legacy_raw_prompt"), expanded=False):
            st.text_area(
                t("default_legacy_prompt"),
                value=get_default_prompt_template(),
                height=240,
                disabled=True,
            )

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
    if "analysis_criteria" not in st.session_state:
        st.session_state.analysis_criteria = [
            {
                "title": criterion.title,
                "description": criterion.description,
                "scoring_system": criterion.scoring_system,
                "include_review": criterion.include_review,
            }
            for criterion in defaults.criteria
        ]
    if "pending_analysis_prompt_config" in st.session_state:
        _apply_prompt_config_to_state(st.session_state.pending_analysis_prompt_config)
        del st.session_state.pending_analysis_prompt_config


def _render_prompt_config_io(t) -> None:
    with st.expander(t("prompt_config_io"), expanded=False):
        config_json = json.dumps(
            _build_prompt_config_export(),
            ensure_ascii=False,
            indent=2,
        )
        st.download_button(
            t("export_prompt_config"),
            data=config_json,
            file_name="analysis_prompt_config.json",
            mime="application/json",
        )

        uploaded_config = st.file_uploader(
            t("prompt_config_file"),
            type=["json"],
            key="analysis_prompt_config_upload",
        )
        if st.button(t("import_prompt_config"), disabled=uploaded_config is None):
            try:
                if uploaded_config is None:
                    return
                st.session_state.pending_analysis_prompt_config = (
                    _normalize_prompt_config(json.load(uploaded_config))
                )
                st.rerun()
            except Exception as error:
                st.error(t("invalid_prompt_config", error=error))


def _render_criterion_editor(index: int, criterion: dict, t) -> None:
    with st.container(border=True):
        header_cols = st.columns([5, 1, 1, 1])
        with header_cols[0]:
            st.markdown(t("criterion", number=index + 1))
        with header_cols[1]:
            st.button(
                t("move_up"),
                key=f"move_criterion_up_{index}",
                disabled=index == 0,
                on_click=_move_criterion,
                args=(index, -1),
            )
        with header_cols[2]:
            st.button(
                t("move_down"),
                key=f"move_criterion_down_{index}",
                disabled=index == len(st.session_state.analysis_criteria) - 1,
                on_click=_move_criterion,
                args=(index, 1),
            )
        with header_cols[3]:
            if st.button(t("remove"), key=f"remove_criterion_{index}"):
                st.session_state.analysis_criteria.pop(index)
                _clear_criterion_widget_state()
                st.rerun()

        criterion["title"] = st.text_input(
            t("criterion_name"),
            value=criterion.get("title", ""),
            key=f"criterion_title_{index}",
        )
        criterion["description"] = st.text_area(
            t("criterion_description"),
            value=criterion.get("description", ""),
            height=100,
            key=f"criterion_description_{index}",
        )
        cols = st.columns([1, 1])
        with cols[0]:
            current_scoring = criterion.get("scoring_system", "percent")
            current_label = SCORING_LABEL_BY_VALUE.get(current_scoring, "0-100%")
            selected_label = st.selectbox(
                t("scoring_system"),
                options=list(SCORING_OPTIONS.keys()),
                index=list(SCORING_OPTIONS.keys()).index(current_label),
                key=f"criterion_scoring_{index}",
            )
            criterion["scoring_system"] = SCORING_OPTIONS[selected_label]
        with cols[1]:
            criterion["include_review"] = st.checkbox(
                t("include_criterion_review"),
                value=bool(criterion.get("include_review", False)),
                key=f"criterion_review_{index}",
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
            return [
                jira_issue_to_analysis_input(issue)
                for issue in search_issues(
                    jira_jql,
                    config,
                    max_results=jira_max_results,
                )
            ]

    if not jira_issue:
        raise ValueError(t("jira_issue_required"))
    with st.spinner(t("fetching_issue", issue=jira_issue)):
        return [jira_issue_to_analysis_input(fetch_issue(jira_issue, config))]


def _load_json_issues(uploaded_file, use_sample: bool, t) -> list[dict]:
    if uploaded_file is not None:
        data = json.load(uploaded_file)
        if not isinstance(data, list):
            raise ValueError(t("invalid_json"))
        return data

    if use_sample:
        project_root = Path(__file__).resolve().parents[2]
        sample_path = project_root / "data" / "input.json"
        if not sample_path.exists():
            raise FileNotFoundError(t("sample_not_found", path=sample_path))
        return load_issues(str(sample_path))

    return []


def _render_results(results: list[dict], t) -> None:
    df = pd.DataFrame(results)
    markdown_report = build_markdown_report(results)

    json_tab, report_tab, table_tab, details_tab = st.tabs(
        ["JSON", t("markdown_report"), t("table"), t("details")]
    )

    with json_tab:
        st.json(results)
        st.download_button(
            t("download_json"),
            data=json.dumps(results, ensure_ascii=False, indent=2),
            file_name="analysis_result.json",
            mime="application/json",
        )

    with report_tab:
        st.markdown(markdown_report)
        st.download_button(
            t("download_markdown"),
            data=markdown_report,
            file_name="analysis_report.md",
            mime="text/markdown",
        )

    with table_tab:
        display_cols = [
            "jira_key",
            "input_element_type",
            "overall_score",
            "verdict",
            "diagnosis",
            "recommendations",
        ]
        available_cols = [column for column in display_cols if column in df.columns]
        st.dataframe(df[available_cols] if available_cols else df, width="stretch")

    with details_tab:
        for index, result in enumerate(results, start=1):
            header_name = (
                result.get("jira_key")
                or result.get("key")
                or result.get("input_element_type")
                or "Unknown"
            )
            st.subheader(t("issue", number=index, name=header_name))

            if "error" in result:
                st.error(t("failed_issue", error=result["error"]))
                st.write(t("original_description"))
                st.info(result.get("input_description", t("no_description")))
                st.divider()
                continue

            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric(t("overall_score"), result.get("overall_score", "N/A"))
                st.write(f"{t('verdict')}: {result.get('verdict', 'N/A')}")

                scores = result.get("criteria_scores", {})
                if isinstance(scores, dict) and scores:
                    st.write(t("criteria_breakdown"))
                    for key, value in scores.items():
                        st.write(f"- {key.replace('_', ' ').title()}: {value}")

            with col2:
                st.write(t("original_description"))
                st.info(result.get("input_description", t("no_description")))

                st.write(t("diagnosis"))
                st.write(result.get("diagnosis", t("no_diagnosis")))

                criteria = result.get("criteria", {})
                if isinstance(criteria, dict) and criteria:
                    st.write(t("criteria_reviews"))
                    for key, criterion_result in criteria.items():
                        if not isinstance(criterion_result, dict):
                            continue
                        title = criterion_result.get(
                            "title",
                            key.replace("_", " ").title(),
                        )
                        score = criterion_result.get("score", "N/A")
                        scoring_system = criterion_result.get(
                            "scoring_system",
                            "N/A",
                        )
                        st.markdown(f"**{title}**: {score} ({scoring_system})")
                        if criterion_result.get("review"):
                            st.write(criterion_result["review"])

                if result.get("overall_conclusion"):
                    st.write(t("overall_conclusion"))
                    st.write(result["overall_conclusion"])

                st.write(t("recommendations"))
                st.markdown(
                    result.get(
                        "recommendations",
                        t("no_recommendations"),
                    )
                )

            st.divider()


if __name__ == "__main__":
    main()
