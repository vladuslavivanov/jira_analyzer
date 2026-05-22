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
    """Jira integration configuration.
    
    Supports both real Jira servers and mock service.
    """
    use_mock: bool = False  # Use mock service instead of real Jira
    
    # Real Jira connection settings (required when use_mock=False)
    server_url: Optional[str] = None  # Jira server URL (e.g., "https://jira.company.com")
    username: Optional[str] = None  # Jira username for authentication
    api_token: Optional[str] = None  # Jira API token for authentication
    verify_ssl: bool = True  # SSL verification for HTTPS connections
    
    # Mock service settings (used when use_mock=True)
    mock_dataset_path: str = "src/jira_analyzer/jira/data/jira_mock_data.json"
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
