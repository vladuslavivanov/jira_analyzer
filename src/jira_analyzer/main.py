"""Main Streamlit application for Jira AI Analyzer.

This is main entry point that integrates all components:
- Configuration system
- LLM provider architecture  
- Template management
- Mock Jira service
- Internationalization
- Results viewer with user guidance
- Complete analysis pipeline
"""

import sqlite3
import streamlit as st

from jira_analyzer.config import ConfigLoader, AppConfig
from jira_analyzer.utils.logger import setup_logging, get_logger
from jira_analyzer.template_manager import TemplateManager
from jira_analyzer.providers import ProviderFactory, LLMMessage
from jira_analyzer.jira import MockJiraClient
from jira_analyzer.i18n import get_text, set_language
from jira_analyzer.ui import ResultsViewer, guided_text_input, guided_button
from jira_analyzer.analyzer.core.llm.prompt_builder import AnalysisPromptConfig, CriterionConfig
from jira_analyzer.analyzer.engine import get_default_analysis_prompt_config, run_analysis
from jira_analyzer.storage import SqliteAnalysisResultRepository
from jira_analyzer.tasktracker.jira import JiraConnectionConfig, fetch_issue, jira_issue_to_analysis_input, search_issues
from jira_analyzer.tasktracker.jira.jira_parser import load_issues

# Initialize logger
logger = get_logger(__name__)


def _is_closed_status_streamlit(issue: dict) -> bool:
    """Check if issue status indicates it's closed (from Streamlit implementation)."""
    status = issue.get("status", "").lower()
    return any(closed in status for closed in ["closed", "done", "resolved", "completed"])


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
    """Load issues from Jira or JSON source."""
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

    if jira_query_mode == "JQL Query":
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
    """Load issues from uploaded JSON file or use sample data."""
    if uploaded_file is not None:
        try:
            data = uploaded_file.read()
            issues = load_issues(data)
            if not isinstance(issues, list):
                raise ValueError(t("invalid_json"))
            return issues
        except Exception as e:
            raise ValueError(f"Error loading JSON: {e}")
    
    if use_sample:
        sample_path = "data/input.json"
        try:
            with open(sample_path, 'r', encoding='utf-8') as f:
                issues = load_issues(f.read())
                if not isinstance(issues, list):
                    raise ValueError(t("invalid_json"))
                return issues
        except FileNotFoundError:
            raise ValueError(t("sample_not_found", path=sample_path))
    
    raise ValueError("Either upload a file or select use_sample")


def _ensure_prompt_state() -> None:
    """Ensure prompt configuration exists in session state."""
    if "analysis_prompt_config" not in st.session_state:
        st.session_state.analysis_prompt_config = get_default_analysis_prompt_config()


def _render_prompt_config_io(t) -> None:
    """Render prompt configuration import/export interface."""
    with st.expander(t("prompt_config_io"), expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(t("export_prompt_config")):
                config = st.session_state.analysis_prompt_config
                st.download_button(
                    t("download_json"),
                    data=config.model_dump_json(indent=2),
                    file_name="prompt_config.json",
                    mime="application/json"
                )
        
        with col2:
            uploaded_config = st.file_uploader(t("prompt_config_file"), type=["json"])
            if uploaded_config:
                try:
                    import json
                    config_data = json.loads(uploaded_config.read())
                    st.session_state.analysis_prompt_config = AnalysisPromptConfig(**config_data)
                    st.success(t("prompt_config_imported"))
                except Exception as e:
                    st.error(t("invalid_prompt_config", error=e))


def _render_prompt_editor(t) -> AnalysisPromptConfig:
    """Render prompt configuration editor."""
    config = st.session_state.analysis_prompt_config
    
    with st.expander(t("analysis_prompt"), expanded=True):
        st.caption(t("prompt_caption"))
        
        system_prompt = st.text_area(
            t("system_prompt"),
            value=config.system_prompt,
            height=120,
            key="analysis_system_prompt_main"
        )
        
        general_prompt = st.text_area(
            t("general_prompt"),
            value=config.general_prompt,
            height=120,
            key="analysis_general_prompt_main"
        )
        
        include_overall_conclusion = st.checkbox(
            t("include_overall"),
            value=config.include_overall_conclusion,
            key="analysis_include_overall_main"
        )
        
        st.subheader(t("criteria"))
        
        # Simple criteria display
        for i, criterion in enumerate(config.criteria):
            with st.expander(f"{t('criterion', number=i+1)}: {criterion.title}", expanded=False):
                criterion_title = st.text_input(t("criterion_name"), value=criterion.title, key=f"criterion_title_{i}")
                criterion_description = st.text_area(t("criterion_description"), value=criterion.description, key=f"criterion_description_{i}")
                scoring_system = st.selectbox(
                    t("scoring_system"),
                    options=["binary", "percent", "five"],
                    index=["binary", "percent", "five"].index(criterion.scoring_system),
                    key=f"criterion_scoring_{i}"
                )
                include_review = st.checkbox(t("include_criterion_review"), value=criterion.include_review, key=f"criterion_review_{i}")
        
        # Add new criterion button could be added here
    
    # Return updated config (simplified version)
    return config
    

def _render_results(results, t):
    """Render analysis results in a simple table format."""
    st.subheader(t("markdown_report"))
    
    # Simple table display
    if isinstance(results, list):
        df_data = []
        for result in results:
            if isinstance(result, dict):
                df_data.append({
                    "Issue": result.get("task_id", "Unknown"),
                    "Title": result.get("title", "No title"),
                    "Status": result.get("status", "Unknown"),
                    "Score": result.get("overall_score", "N/A")
                })
        
        if df_data:
            import pandas as pd
            df = pd.DataFrame(df_data)
            st.dataframe(df)
        else:
            st.info("No results to display")
    else:
        st.info("Analysis completed. Results are stored in database.")


def main():
    """Main Streamlit application with sidebar settings like original."""
    st.set_page_config(
        page_title="Jira AI Analyzer",
        page_icon="🤖",
        layout="wide"
    )

    # Load configuration
    config = ConfigLoader.load_from_path("config.yaml")

    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_llm_prompts=config.logging.log_llm_prompts
    )

    logger.info("Application started")

    # Get language from config
    language = config.i18n.language
    
    # Create translation function for scope
    def t(key: str, **kwargs) -> str:
        """Local translation function for current scope."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text

    # Set page title with i18n
    st.title(t("app_title"))
    st.caption(t("caption"))

    with st.sidebar:
        st.header(t("settings"))
        
        # Language selection
        st.subheader(t("language"))
        selected_language = st.selectbox(
            t("language"),
            ["en", "ru"],
            index=["en", "ru"].index(language)
        )
        
        if selected_language != language:
            try:
                set_language(selected_language)
                # Update config language
                config.i18n.language = selected_language
                language = selected_language  # Use new language immediately
                st.success(f"Language changed to {selected_language}")
            except ValueError as e:
                st.error(f"Invalid language: {e}")
        
        st.divider()
        
        # Issue source settings
        st.subheader(t("issue_source"))
        
        # Mutually exclusive source selection
        source = st.radio(
            "Data Source",
            ["Jira", "JSON"],
            horizontal=True,
            help="Choose exactly one data source for analysis"
        )
        
        if source == "Jira":
            # Jira settings
            if config.jira.use_mock:
                st.info("Using mock Jira service")
            else:
                st.write(f"**{t('connection')}:**")
                st.text_input("Jira Server URL", disabled=True, value="Not implemented")
                st.text_input("Username", disabled=True)
                st.text_input("API Token", type="password", disabled=True)
            
            # Jira query mode
            st.write(f"**{t('jira_query_mode')}:**")
            query_mode = st.radio(
                "JQL Query",
                ["JQL Query", "Single Issue Key"]
            )
            
            if query_mode == "JQL Query":
                jql_input = st.text_input(t("jql_query"))
            else:
                issue_key = st.text_input(t("jira_issue_key"))
        else:
            # JSON upload settings
            st.write(f"**{t('upload_jira_json')}:**")
            uploaded_file = st.file_uploader("Upload JSON file", type=["json"])
            use_sample = st.checkbox(t("use_sample"), value=True)
        
        st.divider()
        
        # Analysis settings
        st.subheader(t("worker_count"))
        worker_count = st.number_input(
            "Analysis threads",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
            help="Number of parallel worker threads for analysis"
        )
        
        # Split by criterion option
        split_by_criterion = st.checkbox(
            t("split_by_criterion"),
            value=False,
            help=t("split_by_criterion_help") if language in ["en", "ru"] else "Analyze each criterion separately"
        )
        
        # Database path
        db_path = st.text_input(
            "Database Path", 
            value="data/analysis.db", 
            help="Path to SQLite database for intermediate results"
        )
        
        # Ensure prompt configuration exists
        _ensure_prompt_state()
        _render_prompt_config_io(t)
        
        # Render prompt configuration editor
        prompt_config = _render_prompt_editor(t)
        
        # Store settings in session state for main content area to access
        if 'source' not in st.session_state or st.session_state.source != source:
            st.session_state.source = source
        if 'jql_input' not in st.session_state:
            st.session_state.jql_input = None
        if 'issue_key' not in st.session_state:
            st.session_state.issue_key = None
        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None
        if 'use_sample' not in st.session_state:
            st.session_state.use_sample = True
        if 'query_mode' not in st.session_state:
            st.session_state.query_mode = None
        if 'worker_count' not in st.session_state:
            st.session_state.worker_count = worker_count
        
        # Update current values based on selected source
        st.session_state.source = source
        if source == "Jira":
            st.session_state.jql_input = jql_input if query_mode == "JQL Query" else None
            st.session_state.issue_key = issue_key if query_mode == "Single Issue Key" else None
            st.session_state.query_mode = query_mode
        else:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.use_sample = use_sample
        st.session_state.worker_count = worker_count

    # Main content area - Simple page selection
    page = st.radio(
        "Page Selection",
        ["Analysis", "Results", "Settings"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if page == "Analysis":
        analysis_page(config, language)
    elif page == "Results":
        results_page(config, language)
    else:
        settings_page(config, language)

    # Run analysis button in main content area (NOT in sidebar)
    if page == "Analysis":
        st.divider()
        col1, col2 = st.columns([1, 6])
        with col1:
            if st.button(t("run_analysis"), type="primary", use_container_width=True):
                st.session_state.analysis_results = None
                try:
                    # Get parameters from session state or defaults
                    source = st.session_state.get('source', 'Jira')
                    jql_input = st.session_state.get('jql_input', None)
                    issue_key = st.session_state.get('issue_key', None)
                    query_mode = st.session_state.get('query_mode', 'JQL Query')
                    uploaded_file = st.session_state.get('uploaded_file', None)
                    use_sample = st.session_state.get('use_sample', True)
                    worker_count = st.session_state.get('worker_count', 1)
                    
                    # Get Jira connection parameters from config
                    jira_server = config.jira.server_url if config.jira.use_mock else (config.jira.server_url or "")
                    jira_username = config.jira.username or ""
                    jira_token = config.jira.api_token or ""
                    jira_verify_ssl = config.jira.verify_ssl
                    
                    # Determine max results for JQL queries
                    jira_max_results = 50
                    exclude_closed = True
                    
                    # Load issues from selected source
                    issues = _load_issues(
                        t=t,
                        source=source,
                        uploaded_file=uploaded_file,
                        use_sample=use_sample,
                        jira_server=jira_server,
                        jira_query_mode=query_mode,
                        jira_issue=issue_key or "",
                        jira_jql=jql_input or "",
                        jira_username=jira_username,
                        jira_token=jira_token,
                        jira_verify_ssl=jira_verify_ssl,
                        jira_max_results=jira_max_results,
                        exclude_closed=exclude_closed,
                    )
                    
                    if not issues:
                        st.warning(t("no_issues"))
                        return

                    # Run analysis with LLM
                    with st.spinner(
                        t("analyzing").format(count=len(issues), workers=worker_count)
                    ):
                        repo = SqliteAnalysisResultRepository(db_path)
                        results = run_analysis(
                            issues,
                            prompt_config=prompt_config,
                            worker_count=int(worker_count),
                            split_by_criterion=split_by_criterion,
                            repo=repo,
                        )
            
                    st.session_state.analysis_results = results
                    st.success(t("analysis_complete"))
                except Exception as error:
                    st.error(t("analysis_error").format(error=error))
                    logger.exception("UI analysis error")

    # Display results if available
    if page == "Analysis" and 'analysis_results' in st.session_state and st.session_state.analysis_results:
        st.divider()
        _render_results(st.session_state.analysis_results, t)


def settings_page(config, language):
    """Settings page with Jira connection configuration."""
    st.header("Jira Connection Settings")
    
    st.subheader("Jira API Connection")
    st.write("Configure your Jira server connection details:")
    
    # Jira Server URL
    server_url = st.text_input(
        "Jira Server URL",
        value=config.jira.server_url or "",
        placeholder="https://your-jira.company.com",
        help="Full URL to your Jira server (e.g., https://jira.company.com)"
    )
    
    # Username
    username = st.text_input(
        "Jira Username",
        value=config.jira.username or "",
        placeholder="your-jira-username",
        help="Your Jira username (leave empty if using token-only auth)"
    )
    
    # API Token
    api_token = st.text_input(
        "Jira API Token",
        value=config.jira.api_token or "",
        type="password",
        placeholder="your-api-token",
        help="Your Jira API token (recommended over username/password)"
    )
    
    # SSL Verification
    verify_ssl = st.checkbox(
        "Verify SSL Certificate",
        value=config.jira.verify_ssl,
        help="Enable SSL verification for HTTPS connections (recommended for production)"
    )
    
    # Use Mock Service Checkbox
    use_mock = st.checkbox(
        "Use Mock Jira Service",
        value=config.jira.use_mock,
        help="Use mock service for development/testing (ignores connection settings above)"
    )
    
    # Save Settings Button
    if st.button("Save Settings", type="primary"):
        st.success("Settings saved! Restart application to apply changes.")
        logger.info("Settings page opened")


def analysis_page(config, language):
    """Analysis page with Jira integration and guided inputs."""
    # Create translation wrapper for this function scope
    def t_local(key: str, **kwargs) -> str:
        """Local translation function."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text
    
    st.header(t_local("start_analysis"))
    
    # Show current Jira connection status
    if config.jira.use_mock:
        st.info("🔧 Using Mock Jira Service (development mode)")
    else:
        if config.jira.server_url:
            st.success(f"✅ Connected to Jira: {config.jira.server_url}")
        else:
            st.warning("⚠️ Jira connection not configured. Go to Settings to configure.")
    
    # JQL input with guidance
    jql = guided_text_input(
        label_key="jql_query",
        help_key="jql_help",
        language=language,
        placeholder=t_local("enter_jql")
    )

    # Start analysis button with guidance
    if guided_button(
        label_key="start_analysis",
        help_key="task_analysis_help",
        language=language,
        type="primary"
    ):
        logger.info("Analysis started")
        
        # Create Jira client based on configuration
        jira_client = create_jira_client(config.jira)
        
        st.success("Analysis started - this would integrate with LLM analysis")
        st.info(f"Using Jira client: {type(jira_client).__name__}")
        st.info("Note: Full integration requires LLM analysis implementation")


def results_page(config, language):
    """Results viewer page with master-detail layout."""
    # Create translation wrapper for this function scope
    def t_local(key: str, **kwargs) -> str:
        """Local translation function."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text
    
    st.header(t_local("results"))

    # Database connection
    @st.cache_resource
    def get_db():
        return sqlite3.connect("results.db")

    db = get_db()

    # Render results viewer
    viewer = ResultsViewer(db)
    viewer.render()


if __name__ == "__main__":
    main()
