"""Main Streamlit application for Jira AI Analyzer.

This is the main entry point that integrates all components:
- Configuration system
- LLM provider architecture  
- Template management
- Mock Jira service
- Internationalization
- Results viewer with user guidance
"""

import sqlite3
import streamlit as st

from jira_analyzer.config import ConfigLoader
from jira_analyzer.utils.logger import setup_logging, get_logger
from jira_analyzer.template_manager import TemplateManager
from jira_analyzer.providers import ProviderFactory, LLMMessage
from jira_analyzer.jira import MockJiraClient
from jira_analyzer.i18n import get_text
from jira_analyzer.ui import ResultsViewer, guided_text_input, guided_button

# Initialize logger
logger = get_logger(__name__)


def main():
    """Main Streamlit application."""
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

    # Set page title with i18n
    st.title(get_text("app_title", language))

    # Simple page selection
    page = st.radio(
        "Navigation",
        ["Analysis", "Results"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if page == "Analysis":
        analysis_page(config, language)
    else:
        results_page(config, language)


def analysis_page(config, language):
    """Analysis page with guided inputs and task analysis."""
    st.header(get_text("start_analysis", language))

    # JQL input with guidance
    jql = guided_text_input(
        label_key="jql_query",
        help_key="jql_help",
        language=language,
        placeholder=get_text("enter_jql", language)
    )

    # Start analysis button with guidance
    if guided_button(
        label_key="start_analysis",
        help_key="task_analysis_help",
        language=language,
        type="primary"
    ):
        logger.info("Analysis started")
        st.success("Analysis started - this would integrate with LLM analysis")
        st.info("Note: Full integration requires LLM analysis implementation")


def results_page(config, language):
    """Results viewer page with master-detail layout."""
    st.header(get_text("results", language))

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
