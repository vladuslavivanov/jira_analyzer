"""
Sample test file demonstrating pytest testing patterns.
This file serves as a template for writing tests in the jira_analyzer project.
"""

import pytest


# Basic test example
def test_sample_basic():
    """A basic test showing simple assertions."""
    assert 1 + 1 == 2
    assert "hello" in "hello world"
    assert len([1, 2, 3]) == 3


# Test with expected exception
def test_sample_exception():
    """Test that demonstrates checking for expected exceptions."""
    with pytest.raises(ValueError):
        int("not a number")

    with pytest.raises(ZeroDivisionError):
        1 / 0


# Parametrized test example
@pytest.mark.parametrize(
    "input_val, expected",
    [
        (2, 4),
        (3, 9),
        (4, 16),
        (5, 25),
    ],
)
def test_sample_parametrized(input_val, expected):
    """Parametrized test running the same test with different inputs."""
    result = input_val * input_val
    assert result == expected


# Fixture example
@pytest.fixture
def sample_data():
    """Fixture that provides test data."""
    return {"name": "Test Task", "status": "In Progress", "priority": "High"}


def test_with_fixture(sample_data):
    """Test using a fixture."""
    assert sample_data["name"] == "Test Task"
    assert sample_data["status"] == "In Progress"
    assert "priority" in sample_data


# Test with setup and teardown using fixtures
@pytest.fixture
def temp_file(tmp_path):
    """Fixture that creates and cleans up a temporary file."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Sample content")
    yield file_path
    # Cleanup happens automatically with tmp_path


def test_file_operations(temp_file):
    """Test demonstrating file operations using temporary fixture."""
    assert temp_file.exists()
    content = temp_file.read_text()
    assert content == "Sample content"


# Test class example
class TestSampleClass:
    """Example test class demonstrating grouped tests."""

    def test_method_one(self):
        """First test method in the class."""
        assert True

    def test_method_two(self):
        """Second test method in the class."""
        assert not False

    @pytest.mark.skip(reason="Demonstrating a skipped test")
    def test_skipped(self):
        """This test will be skipped."""
        assert False


# Test with markers
@pytest.mark.integration
def test_integration_example():
    """Example of an integration test marker."""
    # This test would run with: pytest -m integration
    assert True


@pytest.mark.unit
def test_unit_example():
    """Example of a unit test marker."""
    # This test would run with: pytest -m unit
    assert True


# Test for string operations
def test_string_operations():
    """Test demonstrating string assertions."""
    text = "Jira Task Analysis"

    assert text.startswith("Jira")
    assert text.endswith("Analysis")
    assert "Task" in text
    assert len(text.split()) == 3


# Test for list operations
def test_list_operations():
    """Test demonstrating list assertions."""
    items = ["item1", "item2", "item3"]

    assert len(items) == 3
    assert "item2" in items
    assert items[0] == "item1"
