"""Configuration dataclasses for Jira Analyzer.

All configuration is defined using dataclasses for type safety and 
clear structure. No global variables are used - config is passed via
dependency injection.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM provider configuration.
    
    SECURITY: All fields are required - no default URLs or model names.
    Suitable for internal/self-hosted LLM services.
    """
    provider_type: str
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None


@dataclass
class LogConfig:
    """Logging configuration."""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_llm_prompts: bool = False  # Log LLM interactions?


@dataclass
class JiraConfig:
    """Jira integration configuration."""
    use_mock: bool = True  # Use fake service?
    mock_dataset_path: str = "data/jira_mock_data.json"
    error_on_jql: str = ""  # JQL that triggers error (empty = none)


@dataclass
class I18nConfig:
    """Internationalization configuration."""
    language: str = "en"  # "en" or "ru"


@dataclass
class AppConfig:
    """Main application configuration.

    This configuration object is passed throughout the application via
    dependency injection instead of using global variables.
    """
    llm: LLMConfig
    logging: LogConfig = field(default_factory=LogConfig)
    jira: JiraConfig = field(default_factory=JiraConfig)
    i18n: I18nConfig = field(default_factory=I18nConfig)
