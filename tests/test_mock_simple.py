"""Basic tests for mock Jira service."""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from jira_analyzer.jira import MockJiraClient


def test_mock_json_loading():
    """Test that mock service returns JSON data - happy path only."""
    # Create sample data matching spec format
    data = [
        {
            "id": "TEST-1", 
            "key": "TEST-1",
            "fields": {
                "summary": "Test task",
                "description": "Test description",
                "status": {"name": "Open"},
                "priority": {"name": "Medium"},
                "assignee": {"displayName": "Test User"},
                "reporter": {"displayName": "Test Reporter"},
            }
        }
    ]
    
    with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    
    try:
        # Create client and fetch data
        client = MockJiraClient(temp_path)
        result = client.search_issues()
        
        # Verify basic functionality
        assert len(result) == 1
        assert result[0]["key"] == "TEST-1"
        assert result[0]["fields"]["summary"] == "Test task"
    finally:
        # Clean up temp file
        Path(temp_path).unlink()
