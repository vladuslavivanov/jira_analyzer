"""Template manager for Jira Analyzer prompt templates.

Provides simple {placeholder} template loading and substitution
from text files. Templates are stored in the templates/ directory.
"""

from pathlib import Path
from typing import Dict


class TemplateManager:
    """Load and substitute values in text templates.

    Templates use {placeholder} syntax for variable substitution.

    Student implementation: simple file I/O and string formatting.
    """

    def __init__(self, templates_dir: str):
        """Initialize with templates directory path.

        Args:
            templates_dir: Path to directory containing template files
        """
        self._templates_dir = Path(templates_dir)

    def load_template(self, template_name: str) -> str:
        """Load template text from file.

        Args:
            template_name: Name of template file (e.g., "task_analysis.txt")

        Returns:
            Template text as string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = self._templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")

    def substitute(
        self,
        template_text: str,
        values: Dict[str, str]
    ) -> str:
        """Replace {placeholder} with values.

        Args:
            template_text: Template string with {placeholder} markers
            values: Dictionary mapping placeholder names to values

        Returns:
            Template with placeholders replaced

        Raises:
            ValueError: If template variable is missing values

        Example:
            template = "Analyze task: {title}\\nDescription: {desc}"
            values = {"title": "Fix bug", "desc": "Critical error"}
            result = "Analyze task: Fix bug\\nDescription: Critical error"
        """
        try:
            return template_text.format(**values)
        except KeyError as e:
            raise ValueError(f"Missing template value: {e}")
