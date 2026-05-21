"""Internationalization support for Jira Analyzer.

This module provides simple dictionary-based translations
for English and Russian languages. No complex translation
infrastructure - just string lookup.
"""

from .translations import get_text, set_language

__all__ = ["get_text", "set_language"]
