"""Basic tests for configuration system."""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from jira_analyzer.config import ConfigLoader, AppConfig


def test_config_loading():
    """Test that config can be loaded from YAML - happy path only."""
    
    # Create a sample config file
    config_content = """
llm:
  provider_type: openai-compatible
  api_key: test-key
  base_url: http://localhost:8000/v1
  model: test-model

logging:
  level: INFO
  log_llm_prompts: false

jira:
  use_mock: true

i18n:
  language: en
"""
    
    with NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name
    
    try:
        # Test config loads correctly
        config = ConfigLoader.load_from_path(temp_path)
        assert isinstance(config, AppConfig)
        assert config.llm.api_key == "test-key"
        assert config.llm.base_url == "http://localhost:8000/v1"
        assert config.llm.model == "test-model"
        assert config.logging.level == "INFO"
        assert config.jira.use_mock is True
        assert config.i18n.language == "en"
    finally:
        # Clean up temp file
        Path(temp_path).unlink()
