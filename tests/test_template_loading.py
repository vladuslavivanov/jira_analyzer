from jira_analyzer.analyzer.core.llm.prompt_builder import (
    AnalysisPromptConfig,
    CriterionConfig,
    _format_criterion,
    _load_template,
    build_prompt_from_template,
    build_structured_prompt,
)


def test_load_template_from_existing_file():
    """Test that template files can be loaded successfully from resources directory."""
    system_prompt = _load_template("system-prompt.md")
    
    assert isinstance(system_prompt, str)
    assert len(system_prompt) > 0
    assert "strict but constructive" in system_prompt.lower()


def test_load_template_with_valid_path():
    """Test loading structured analysis template."""
    structured_template = _load_template("structured-analysis-prompt.md")
    
    assert isinstance(structured_template, str)
    assert "{element_type}" in structured_template
    assert "{description}" in structured_template
    assert "{general_prompt}" in structured_template


def test_load_template_with_subdirectory_path():
    """Test loading templates from subdirectories."""
    criterion_template = _load_template("templates/criterion-format.md")
    
    assert isinstance(criterion_template, str)
    assert "{criterion_index}" in criterion_template
    assert "{criterion_key}" in criterion_template
    assert "{criterion_title}" in criterion_template


def test_build_prompt_from_template_basic_placeholders():
    """Test that basic placeholder replacement works correctly."""
    template = "Type: {element_type}\nDescription: {description}"
    
    result = build_prompt_from_template("Task", "Test description", template)
    
    assert result == "Type: Task\nDescription: Test description"
    assert "{element_type}" not in result
    assert "{description}" not in result


def test_build_prompt_from_template_with_empty_values():
    """Test placeholder replacement with empty string values."""
    template = "Type: {element_type}\nDescription: {description}"
    
    result = build_prompt_from_template("", "", template)
    
    assert result == "Type: \nDescription: "
    assert "{element_type}" not in result
    assert "{description}" not in result


def test_build_prompt_from_template_with_complex_values():
    """Test placeholder replacement with complex/multiline values."""
    template = "Issue: {element_type}\nDetails: {description}"
    
    result = build_prompt_from_template(
        "Risk",
        "High probability security issue\nMitigation: patch by Friday",
        template
    )
    
    assert "Issue: Risk" in result
    assert "High probability security issue" in result
    assert "Mitigation: patch by Friday" in result


def test_build_structured_prompt_replaces_element_type():
    """Test that structured prompt replaces element_type placeholder."""
    config = AnalysisPromptConfig(
        system_prompt="Test system",
        general_prompt="Test general",
        criteria=[],
        include_overall_conclusion=False,
    )
    
    result = build_structured_prompt("Task", "Test description", config)
    
    assert "Issue type:\nTask" in result
    assert "{element_type}" not in result


def test_build_structured_prompt_replaces_description():
    """Test that structured prompt replaces description placeholder."""
    config = AnalysisPromptConfig(
        system_prompt="Test system",
        general_prompt="Test general", 
        criteria=[],
        include_overall_conclusion=False,
    )
    
    result = build_structured_prompt("Risk", "Security vulnerability in auth", config)
    
    assert "Issue description:\nSecurity vulnerability in auth" in result
    assert "{description}" not in result


def test_build_structured_prompt_replaces_general_prompt():
    """Test that structured prompt replaces general_prompt placeholder."""
    config = AnalysisPromptConfig(
        system_prompt="Test system",
        general_prompt="Analyze this issue thoroughly",
        criteria=[],
        include_overall_conclusion=False,
    )
    
    result = build_structured_prompt("Task", "Test", config)
    
    assert "General analysis prompt:\nAnalyze this issue thoroughly" in result
    assert "{general_prompt}" not in result


def test_format_criterion_replaces_all_placeholders():
    """Test that _format_criterion replaces all criterion-related placeholders."""
    criterion = CriterionConfig(
        title="Test Criterion",
        description="A test criterion description",
        scoring_system="percent",
        include_review=True,
    )
    
    result = _format_criterion(1, criterion, "test_key")
    
    assert "1. id: test_key" in result
    assert "title: Test Criterion" in result
    assert "description: A test criterion description" in result
    assert "scoring_system: percent" in result
    assert "{criterion_index}" not in result
    assert "{criterion_key}" not in result
    assert "{criterion_title}" not in result
    assert "{criterion_description}" not in result


def test_format_criterion_without_include_review():
    """Test criterion formatting when review is not included."""
    criterion = CriterionConfig(
        title="Simple Criterion",
        description="Simple description",
        scoring_system="binary",
        include_review=False,
    )
    
    result = _format_criterion(1, criterion, "simple_key")
    
    assert "Do not include a review field" in result
    assert "scoring_system: binary" in result


def test_format_criterion_with_include_review():
    """Test criterion formatting when review is included."""
    criterion = CriterionConfig(
        title="Review Criterion",
        description="Review description", 
        scoring_system="five",
        include_review=True,
    )
    
    result = _format_criterion(3, criterion, "review_key")
    
    assert "Include a review field" in result
    assert "3. id: review_key" in result
    assert "scoring_system: five" in result