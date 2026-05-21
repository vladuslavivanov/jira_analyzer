"""Configuration loader for YAML-based configuration."""

from pathlib import Path
from typing import Any, Dict
import yaml

from .models import AppConfig, LLMConfig, LogConfig, JiraConfig, I18nConfig


class ConfigLoader:
    """Load configuration from YAML files.

    This loader replaces the environment variable-based configuration
    with a cleaner YAML approach that doesn't rely on external defaults.
    """

    @staticmethod
    def load_from_path(config_path: str) -> AppConfig:
        """Load configuration from YAML file.

        Args:
            config_path: Path to config file (e.g., "config.yaml")

        Returns:
            AppConfig instance with loaded values

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid (missing required fields)

        Note:
            This method enforces that all LLM provider fields are present,
            ensuring no external service defaults are used (security requirement).
        """
        config_path_obj = Path(config_path)
        
        if not config_path_obj.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")

        # Read and parse YAML file
        data = yaml.safe_load(config_path_obj.read_text())

        # Validate required sections exist
        required_sections = ["llm"]
        for section in required_sections:
            if section not in data:
                raise ValueError(f"Missing required section: {section}")

        # Validate that all LLM fields are present (no external defaults)
        llm_section = data.get("llm", {})
        required_llm_fields = ["provider_type", "api_key", "base_url", "model"]
        missing_llm_fields = [
            field for field in required_llm_fields 
            if field not in llm_section
        ]
        
        if missing_llm_fields:
            raise ValueError(
                f"Missing required LLM config fields: {missing_llm_fields}. "
                "All provider fields must be explicitly configured "
                "(no external service defaults allowed)."
            )

        # Create nested config objects from YAML data
        llm_config = LLMConfig(**llm_section)
        log_config = LogConfig(**data.get("logging", {}))
        jira_config = JiraConfig(**data.get("jira", {}))
        i18n_config = I18nConfig(**data.get("i18n", {}))

        return AppConfig(
            llm=llm_config,
            logging=log_config,
            jira=jira_config,
            i18n=i18n_config
        )

    @staticmethod
    def load_default() -> AppConfig:
        """Load default configuration.

        SECURITY WARNING: This returns INVALID config for demonstration.
        Always use load_from_path() with proper config file.
        
        Returns:
            AppConfig with placeholder values (NOT FOR PRODUCTION)
        
        Note:
            This method only exists for development convenience. 
            For production use, always create a proper config file
            with explicit internal/self-hosted URLs.
        """
        return AppConfig(
            llm=LLMConfig(
                provider_type="openai-compatible",
                api_key="PLACEHOLDER_KEY_IN_CONFIG_FILE",
                base_url="PLACEHOLDER_URL_IN_CONFIG_FILE",
                model="PLACEHOLDER_MODEL_IN_CONFIG_FILE"
            )
        )
