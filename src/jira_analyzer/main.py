"""Main Streamlit application for Jira AI Analyzer.

This is main entry point that integrates all components:
- Configuration system
- LLM provider architecture  
- Template management
- Mock Jira service
- Internationalization
- Results viewer with user guidance
- Complete analysis pipeline

Organization according to ADR-005:
- Sidebar: Global settings only (language, database path, Jira connection)
- Main Analysis Page: Workflow controls and analysis execution
- Results Page: Separate master-detail view for results
"""

import json
import sqlite3
import streamlit as st
from dataclasses import replace
from datetime import datetime

from jira_analyzer.config import ConfigLoader
from jira_analyzer.utils.logger import setup_logging, get_logger
from jira_analyzer.i18n import get_text, set_language
from jira_analyzer.ui import ResultsViewer
from jira_analyzer.analyzer.core.llm.prompt_builder import AnalysisPromptConfig, CriterionConfig
from jira_analyzer.analyzer.engine import get_default_analysis_prompt_config, run_analysis
from jira_analyzer.storage import SqliteAnalysisResultRepository
from jira_analyzer.tasktracker.jira import JiraConnectionConfig, fetch_issue, jira_issue_to_analysis_input, search_issues
from jira_analyzer.app.output_handler import build_markdown_report

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
        raise ValueError("Jira server URL is required")

    config = JiraConnectionConfig(
        server=jira_server,
        username=jira_username or None,
        token=jira_token or None,
        verify_ssl=jira_verify_ssl,
    )

    if jira_query_mode == "JQL Query":
        if not jira_jql.strip():
            raise ValueError("JQL query is required")
        with st.spinner("Fetching issues from Jira..."):
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
        raise ValueError("Jira issue key is required")
    with st.spinner(f"Fetching issue {jira_issue} from Jira..."):
        issue = jira_issue_to_analysis_input(fetch_issue(jira_issue, config))
        if exclude_closed and _is_closed_status_streamlit(issue):
            raise ValueError(f"Issue {jira_issue} is closed and excluded from analysis.")
        return [issue]


def _load_json_issues(uploaded_file, use_sample: bool, t) -> list[dict]:
    """Load issues from uploaded JSON file."""
    if uploaded_file is not None:
        try:
            data = uploaded_file.read()
            issues = json.loads(data)
            if not isinstance(issues, list):
                raise ValueError("Invalid JSON format: expected list of issues")
            for item in issues:
                if "element_type" not in item or "description" not in item:
                    raise ValueError(
                        "Each object must have 'element_type' and 'description' fields"
                    )
            return issues
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Error loading JSON: {e}")
    
    raise ValueError("Please upload a JSON file")


def _ensure_prompt_state() -> None:
    """Ensure prompt configuration exists in session state."""
    if "analysis_prompt_config" not in st.session_state:
        st.session_state.analysis_prompt_config = get_default_analysis_prompt_config()


def _render_prompt_config_io(language: str) -> None:
    """Render prompt configuration import/export interface."""
    # Create translation function for this component
    def t(key: str, **kwargs) -> str:
        """Local translation function with proper language parameter."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text

    with st.expander(t("prompt_config_io"), expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_config = st.file_uploader(t("prompt_config_file"), type=["json"])
            if uploaded_config:
                try:
                    import json
                    config_data = json.loads(uploaded_config.read())
                    # Convert criteria dictionaries to CriterionConfig objects
                    if 'criteria' in config_data:
                        config_data['criteria'] = [CriterionConfig(**criterion) for criterion in config_data['criteria']]
                    st.session_state.analysis_prompt_config = AnalysisPromptConfig(**config_data)
                    st.success(t("prompt_config_imported"))
                except Exception as e:
                    st.error(t("invalid_prompt_config", error=e))
        
        with col2:
            if st.button(t("export_prompt_config")):
                config = st.session_state.analysis_prompt_config
                st.download_button(
                    t("download_json"),
                    data=config.model_dump_json(indent=2),
                    file_name="prompt_config.json",
                    mime="application/json"
                )


def _render_prompt_editor(language: str) -> AnalysisPromptConfig:
    """Render prompt configuration editor with proper state updates, import/export, and criteria management."""
    # Create translation function for this component
    def t(key: str, **kwargs) -> str:
        """Local translation function with proper language parameter."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text

    config = st.session_state.analysis_prompt_config
    
    with st.expander(t("analysis_prompt"), expanded=True):
        # ===========================
        # CONFIG IMPORT/EXPORT
        # ===========================
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_config = st.file_uploader(t("prompt_config_file"), type=["json"], key="prompt_upload")
            if uploaded_config:
                try:
                    import json
                    config_data = json.loads(uploaded_config.read())
                    # Convert criteria dictionaries to CriterionConfig objects
                    if 'criteria' in config_data:
                        config_data['criteria'] = [CriterionConfig(**criterion) for criterion in config_data['criteria']]
                    st.session_state.analysis_prompt_config = AnalysisPromptConfig(**config_data)
                    st.success(t("prompt_config_imported"))
                    config = st.session_state.analysis_prompt_config  # Update local config
                    st.rerun()
                except Exception as e:
                    st.error(t("invalid_prompt_config", error=e))
        
        with col2:
            if st.button(t("export_prompt_config"), key="prompt_export_btn"):
                st.download_button(
                    t("download_json"),
                    data=config.model_dump_json(indent=2),
                    file_name="prompt_config.json",
                    mime="application/json",
                    key="prompt_download_btn"
                )
        
        st.divider()
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
        
        # Simple criteria display with proper updates
        updated_criteria = []
        for i, criterion in enumerate(config.criteria):
            with st.expander(f"{t('criterion', number=i+1)}: {criterion.title}", expanded=False):
                updated_title = st.text_input(t("criterion_name"), value=criterion.title, key=f"criterion_title_{i}")
                updated_description = st.text_area(t("criterion_description"), value=criterion.description, key=f"criterion_description_{i}")
                updated_scoring = st.selectbox(
                    t("scoring_system"),
                    options=["binary", "percent", "five"],
                    index=["binary", "percent", "five"].index(criterion.scoring_system),
                    key=f"criterion_scoring_{i}"
                )
                updated_review = st.checkbox(t("include_criterion_review"), value=criterion.include_review, key=f"criterion_review_{i}")
                
                # Create updated criterion object
                updated_criterion = replace(
                    criterion,
                    title=updated_title,
                    description=updated_description,
                    scoring_system=updated_scoring,
                    include_review=updated_review
                )
                updated_criteria.append(updated_criterion)
        
        # Add new criterion button
        st.divider()
        col_add1, col_add2 = st.columns([1, 4])
        with col_add1:
            if st.button("➕ Add Criterion", key="add_criterion_btn", use_container_width=True):
                try:
                    new_criterion = CriterionConfig(
                        title="New Criterion",
                        description="Description of the criterion",
                        scoring_system="binary",
                        include_review=True
                    )
                    # Add new criterion to the list and update config immediately
                    updated_criteria.append(new_criterion)
                    config = replace(config, criteria=updated_criteria)
                    st.session_state.analysis_prompt_config = config
                    st.success("New criterion added! Edit it above.")
                    st.rerun()
                except ImportError:
                    # Fallback if domain module not available
                    st.error("Unable to add criterion - criterion class not found")
                except Exception as e:
                    st.error(f"Error adding criterion: {e}")
        
        # Create updated configuration with all changes
        updated_config = replace(
            config,
            system_prompt=system_prompt,
            general_prompt=general_prompt,
            include_overall_conclusion=include_overall_conclusion,
            criteria=updated_criteria
        )
        
        # Update session state with the new configuration
        st.session_state.analysis_prompt_config = updated_config
    
    return updated_config
    

def _render_results(results, language: str):
    """Render analysis results as single-page markdown report with download option.
    
    This matches the original implementation using build_markdown_report function
    and displays the complete report with the ability to download as markdown file.
    """
    # Create translation function for this component
    def t(key: str, **kwargs) -> str:
        """Local translation function with proper language parameter."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text

    st.subheader(t("markdown_report"))
    
    if not isinstance(results, list) or not results:
        st.info("No results to display")
        return
    
    # Filter out error results for complete report
    valid_results = [r for r in results if not r.get('error')]
    
    if not valid_results:
        st.warning("Analysis failed for all issues. Check error messages.")
        return
    
    # Generate markdown report using original implementation
    try:
        markdown_report = build_markdown_report(valid_results)
    except Exception as e:
        logger.error(f"Failed to generate markdown report: {e}")
        st.error(f"Failed to generate report: {e}")
        return
    
    # Display the markdown report
    st.markdown(markdown_report)
    
    # Download button for markdown file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="Download Markdown Report",
        data=markdown_report,
        file_name=f"jira_analysis_report_{timestamp}.md",
        mime="text/markdown",
        key="download_markdown_report"
    )


def main():
    """Main Streamlit application with reorganized UI according to ADR-005."""
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
    
    # Create translation function for main scope
    def t(key: str, **kwargs) -> str:
        """Local translation function for current scope."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text

    # Set page title with i18n
    st.title(t("app_title"))
    st.caption(t("caption"))

    # ===========================
    # SIDEBAR: Global Settings Only
    # ===========================
    with st.sidebar:
        st.header(t("settings"))
        
        # Language selection
        st.subheader(t("language"))
        selected_language = st.selectbox(
            "Language / Язык",
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
        
        # Database path (global setting)
        st.subheader(t("database_settings"))
        db_path = st.text_input(
            t("database_path"), 
            value="data/analysis.db", 
            help=t("database_path_help")
        )
        
        st.divider()
        
        # Jira Connection Settings (global setting)
        st.subheader("Jira Connection Settings")
        
        # Use Mock Service Checkbox
        use_mock = st.checkbox(
            "Use Mock Jira Service",
            value=config.jira.use_mock,
            help="Use mock service for development/testing (ignores connection settings below)"
        )
        
        if not use_mock:
            # Jira Server URL
            jira_server = st.text_input(
                "Jira Server URL",
                value=config.jira.server_url or "",
                placeholder="https://your-jira.company.com",
                help="Full URL to your Jira server (e.g., https://jira.company.com)"
            )
            
            # Username
            jira_username = st.text_input(
                "Username",
                value=config.jira.username or "",
                placeholder="your-jira-username",
                help="Your Jira username (leave empty if using token-only auth)"
            )
            
            # API Token
            jira_token = st.text_input(
                "API Token",
                value=config.jira.api_token or "",
                type="password",
                placeholder="your-api-token",
                help="Your Jira API token (recommended over username/password)"
            )
            
            # SSL Verification
            jira_verify_ssl = st.checkbox(
                "Verify SSL Certificate",
                value=config.jira.verify_ssl,
                help="Enable SSL verification for HTTPS connections (recommended for production)"
            )
        else:
            jira_server = ""
            jira_username = ""
            jira_token = ""
            jira_verify_ssl = True
        
        # Store global settings in session state
        st.session_state.global_db_path = db_path
        st.session_state.jira_server = jira_server
        st.session_state.jira_username = jira_username
        st.session_state.jira_token = jira_token
        st.session_state.jira_verify_ssl = jira_verify_ssl

    # ===========================
    # MAIN CONTENT AREA
    # ===========================
    
    # Page selection
    page = st.radio(
        "Page Selection",
        [t("analysis_tab"), t("results_tab"), "Settings"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if page == t("analysis_tab"):
        analysis_page(config, language, db_path)
    elif page == t("results_tab"):
        results_page(config, language, db_path)
    else:
        settings_page(config, language)


def analysis_page(config, language, db_path):
    """Analysis page with complete workflow in main content area."""
    # Create translation function for this function scope
    def t(key: str, **kwargs) -> str:
        """Local translation function."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text

    st.header(t("start_analysis"))
    
    # ===========================
    # STEP 1: Data Source Selection
    # ===========================
    st.subheader(t("data_source"))
    source = st.radio(
        "Data Source",
        ["Jira", "JSON"],
        horizontal=True,
        help=t("select_data_source_help"),
        key="analysis_data_source"
    )
    # Initialize variables for all possible data sources
    uploaded_file = None
    use_sample = True
    query_mode = "JQL Query"
    issue_key = None
    jql_input = None
    
    # ===========================
    # STEP 2: Source-specific Inputs
    # ===========================
    if source == "Jira":
        st.write(f"**{t('jira_query_mode')}:**")
        query_mode = st.radio(
            "Query Mode",
            ["JQL Query", "Single Issue Key"],
            horizontal=True,
            key="analysis_jira_query_mode"
        )
        
        if query_mode == "JQL Query":
            st.write(f"**{t('jql_query')}:**")
            jql_input = st.text_input(
                t("jql_query"),
                placeholder=t("enter_jql"),
                key="analysis_jql_input"
            )
            issue_key = None
        else:
            st.write(f"**{t('jira_issue_key')}:**")
            issue_key = st.text_input(
                t("jira_issue_key"),
                placeholder="e.g., PROJ-123",
                key="analysis_issue_key"
            )
            jql_input = None
    else:
        st.write(f"**{t('upload_jira_json')}:**")
        uploaded_file = st.file_uploader(
            "Upload JSON file",
            type=["json"],
            key="analysis_json_upload"
        )
        use_sample = st.checkbox(
            t("use_sample"),
            value=True,
            key="analysis_use_sample"
        )
    
    st.divider()
    
    # ===========================
    # STEP 3: Prompt Configuration
    # ===========================
    _ensure_prompt_state()
    prompt_config = _render_prompt_editor(language)
    
    st.divider()
    
    # ===========================
    # STEP 4: Analysis Options
    # ===========================
    st.subheader("Analysis Options")
    col1, col2 = st.columns(2)
    
    with col1:
        split_by_criterion = st.checkbox(
            t("split_by_criterion"),
            value=False,
            help=t("split_by_criterion_help"),
            key="analysis_split_by_criterion"
        )
    
    with col2:
        worker_count = st.number_input(
            "Worker Count",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
            help="Number of parallel worker threads for analysis",
            key="analysis_worker_count"
        )
    
    st.divider()
    
    # ===========================
    # STEP 5: Run Analysis Button (PRIMARY ACTION)
    # ===========================
    if st.button(t("run_analysis"), type="primary", use_container_width=True, key="analysis_run_button"):
        st.session_state.analysis_results = None
        try:
            # Get parameters from session state or defaults
            jira_server = st.session_state.get('jira_server', "")
            jira_username = st.session_state.get('jira_username', "")
            jira_token = st.session_state.get('jira_token', "")
            jira_verify_ssl = st.session_state.get('jira_verify_ssl', True)
            
            # Determine max results for JQL queries
            jira_max_results = 50
            exclude_closed = True
            
            # Load issues from selected source
            with st.spinner("Loading issues..."):
                issues = _load_issues(
                    t=t,
                    source=source,
                    uploaded_file=uploaded_file if source == "JSON" else None,
                    use_sample=use_sample if source == "JSON" else False,
                    jira_server=jira_server,
                    jira_query_mode=query_mode if source == "Jira" else "",
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

    # ===========================
    # STEP 6: Display Results Summary
    # ===========================
    if 'analysis_results' in st.session_state and st.session_state.analysis_results:
        st.divider()
        _render_results(st.session_state.analysis_results, language)


def results_page(config, language, db_path):
    """Results viewer page with master-detail layout."""
    # Create translation function for this function scope
    def t(key: str, **kwargs) -> str:
        """Local translation function."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text

    st.header(t("results"))

    # Database connection
    @st.cache_resource
    def get_db():
        return sqlite3.connect(db_path, check_same_thread=False)

    db = get_db()

    # Render results viewer
    viewer = ResultsViewer(db)
    viewer.render()


def settings_page(config, language):
    """Settings page for detailed configuration."""
    # Create translation function for this function scope
    def t(key: str, **kwargs) -> str:
        """Local translation function."""
        text = get_text(key, language)
        return text.format(**kwargs) if kwargs else text

    st.header("Detailed Settings")
    st.info("Global settings are managed in the sidebar. Use this page for advanced configuration.")
    
    st.subheader("Current Configuration")
    st.write(f"Language: {language}")
    st.write(f"Database Path: {st.session_state.get('global_db_path', 'Not set')}")
    st.write(f"Jira Server: {st.session_state.get('jira_server', 'Not configured')}")
    
    logger.info("Settings page opened")


if __name__ == "__main__":
    main()
