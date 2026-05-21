"""Basic tests for template manager system."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from jira_analyzer.template_manager import TemplateManager


def test_template_substitution():
    """Test basic placeholder substitution - happy path only."""
    
    with TemporaryDirectory() as temp_dir:
        # Create a test template file
        template_file = Path(temp_dir) / "test_template.txt"
        template_file.write_text("Analyze task: {title}\nDescription: {desc}")
        
        # Test substitution works
        template_mgr = TemplateManager(temp_dir)
        template = template_mgr.load_template("test_template.txt")
        result = template_mgr.substitute(template, {"title": "Fix bug", "desc": "Critical error"})
        
        assert result == "Analyze task: Fix bug\nDescription: Critical error"
