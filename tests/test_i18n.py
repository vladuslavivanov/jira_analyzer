"""Basic tests for internationalization system."""

from jira_analyzer.i18n import get_text, set_language


def test_translation_works():
    """Test that translations can be retrieved - happy path only."""
    result_en = get_text("app_title", "en")
    result_ru = get_text("app_title", "ru")
    assert result_en == "Jira AI Analyzer"
    assert result_ru == "AI Анализатор Jira"
