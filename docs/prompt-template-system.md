# Prompt Template System Documentation

## Overview

The Prompt Template System provides a flexible, file-based configuration mechanism for controlling AI analysis behavior without modifying source code. This enables:

* Rapid iteration on analysis quality
* Customizable evaluation criteria for different use cases
* Separation of business logic from prompt engineering
* Version-controlled prompt variations
* A/B testing of different prompt strategies
* SpecializedAnalysis templates for different issue types
* **Zero hardcoded strings** - ALL prompt data is externalized in separate files

The system loads template files from `resources/prompts/` and assembles them into structured prompts for the LLM.

## File Structure

```
resources/prompts/
├── system-prompt.md                    # System-level LLM instructions
├── general-prompt.md                   # General analysis guidance
├── structured-analysis-prompt.md       # Main structured analysis template
├── default/
│   ├── criteria-config.json           # Default evaluation criteria configuration
│   └── instructions.json               # Scoring instructions, labels, etc.
└── templates/
    ├── criterion-format.md             # Individual criterion formatting template
    ├── scoring-instruction.md          # Scoring system instruction template
    └── scoring-label.md                # Scoring label template
```

## Template Files

### Core Prompt Files

#### `system-prompt.md`
Defines the LLM's role and persona for quality analysis.

Example content:
```markdown
You are a strict but constructive Jira issue quality analyst. Return only valid JSON that matches the requested schema.
```

#### `general-prompt.md`
Provides high-level analysis guidance and expectations.

Example content:
```markdown
Analyze the issue description. Evaluate whether it is clear, complete, measurable, and suitable for the specified issue type.
```

#### `structured-analysis-prompt.md`
The main template that assembles the complete analysis prompt with all placeholders.

Key placeholders:
* `{element_type}` - Issue type (Task, Risk, etc.)
* `{description}` - Issue text content
* `{general_prompt}` - General analysis instructions
* `{criteria_block}` - Formatted criteria definitions
* `{overall_instruction}` - Overall conclusion instructions
* `{json_schema}` - Generated JSON schema for output

### Template Components

#### `templates/criterion-format.md`
Defines how individual criteria are formatted in the prompt.

Other placeholders:
* `{criterion_index}` - Numeric index (1, 2, 3...)
* `{criterion_key}` - Generated key identifier
* `{criterion_title}` - Criterion display name
* `{criterion_description}` - Detailed description
* `{criterion_scoring_system}` - Type (binary/percent/five)
* `{scoring_instruction}` - Scoring guidance
* `{review_instruction}` - Review field instruction

#### `default/instructions.json` (NEW)
Contains all scoring-related prompt data including instructions and labels.

Key sections:
* Scoring system descriptions (binary/percent/five)
* Scoring instruction templates
* Scoring label formats
* Rating scale definitions

This file externalizes all hardcoded scoring data, allowing modifications without code changes.

#### `templates/scoring-instruction.md`
Defines the scoring instruction placeholder content.

Placeholder:
* `{scoring_instruction}` - Dynamic scoring system instructions

#### `templates/scoring-label.md`
Defines the scoring label placeholder content.

Placeholder:
* `{score_schema_label}` - Dynamic scoring label format

## Fail-Fast Behavior

The template system follows a strict fail-fast approach to ensure data integrity and prevent silent failures:

### Error Handling

* **Missing template files**: Immediate `FileNotFoundError`
  - Template files must exist at their expected paths
  - Create directory structure before starting
  - No auto-creation of missing files

* **Missing JSON configurations**: Immediate `FileNotFoundError`
  - `criteria-config.json` must exist in `default/` directory
  - `instructions.json` must exist in `default/` directory
  - Properly formatted JSON is required

* **Missing instruction data**: Immediate `KeyError`
  - All required keys must be present in JSON files
  - No default values or fallback content
  - Data must be complete and valid

* **No fallback mechanisms**: The system does not provide fallback messages or default templates
  - All content must be explicitly defined in files
  - Missing data causes immediate failure
  - This forces proper configuration and prevents silent failures

### Benefits of Fail-Fast Approach

* **Early error detection**: Configuration problems are caught immediately
* **No silent failures**: Missing data never results in incorrect behavior
* **Clear error messages**: Specific error types help identify issues quickly
* **Configuration integrity**: Ensures all required data is properly specified
* **Maintainability**: Forces attention to proper setup from the start

### Language Requirement

**All content must be in English only**

* Template files: English content required
* JSON configurations: English keys and values required
* Instruction text: English only
* No multilingual content or character sets
* LLM responses will be in English by default

### Setup Requirements

Ensure complete file structure before using the system:
1. Verify all template files exist in `resources/prompts/`
2. Ensure JSON files exist in `resources/prompts/default/`
3. Validate JSON syntax using `jq .` or JSON validators
4. Check that all required keys are present
5. Verify UTF-8 encoding for all files

## Placeholder Syntax

Placeholders use curly brace syntax: `{variable_name}`.

### System Placeholders
* `{element_type}` - Issue type from input
* `{description}` - Issue description text
* `{general_prompt}` - Content from general-prompt.md

### Generated Placeholders
* `{criteria_block}` - Assembled criteria definitions
* `{json_schema}` - Generated JSON schema for LLM output
* `{overall_instruction}` - Conditional overall conclusion instruction

### Component Placeholders
* `{scoring_instruction}` - Dynamic scoring system text
* `{score_schema_label}` - Dynamic scoring range label

## Criteria Configuration

### File Structure (`criteria-config.json`)

```json
{
  "version": 1,
  "criteria": [
    {
      "title": "Completeness and specificity",
      "description": "Check whether the issue contains concrete names, links, versions, API signatures, expected behavior, and enough context to act on it.",
      "scoring_system": "percent",
      "include_review": true
    }
  ]
}
```

### Criterion Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `title` | string | Yes | Human-readable criterion name |
| `description` | string | Yes | Detailed evaluation guidance |
| `scoring_system` | enum | Yes | `binary`, `percent`, or `five` |
| `include_review` | boolean | No | Whether to include review field (default: false) |
| `key` | string | No | Override automatic key generation. If omitted, derived from `title`. |

### Root Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `version` | integer | Yes | Schema version (currently `1`) |
| `criteria` | array | Yes | List of criterion objects |

### Scoring Systems

| System | Range | Use Case |
|--------|-------|----------|
| `binary` | 0-1 | Yes/no criteria, compliance checks |
| `percent` | 0-100 | Quality metrics, completeness scores |
| `five` | 0-5 | Likert-style evaluations, qualitative ratings |

## Analysis Config Export Format

When you export an analysis configuration (from the prompt editor or the results viewer), it uses the full `AnalysisConfig` schema. This is the same format accepted by the import function, so exported configs can be round-tripped.

### Full Schema

```json
{
  "version": 1,
  "system_prompt": "You are a code reviewer...",
  "general_prompt": "Analyze the following issue...",
  "include_overall_conclusion": true,
  "default_scoring_system": "percent",
  "criteria": [
    {
      "title": "Completeness and specificity",
      "description": "Check whether the issue contains concrete names, links...",
      "scoring_system": "percent",
      "include_review": true,
      "key": ""
    }
  ]
}
```

### Root Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `version` | integer | Yes | Schema version (`1`) |
| `system_prompt` | string | Yes | System prompt sent to the LLM |
| `general_prompt` | string | Yes | General analysis instruction |
| `include_overall_conclusion` | boolean | Yes | Whether to include `overall_conclusion` in results |
| `default_scoring_system` | enum | Yes | Default scoring for new criteria: `binary`, `percent`, or `five` |
| `criteria` | array | Yes | List of criterion objects (see [Criterion Properties](#criterion-properties)) |

### Run-Specific Metadata (Optional)

When exporting from the results viewer, these additional fields are included and preserved. They are silently ignored on import.

| Property | Type | Description |
|----------|------|-------------|
| `run_name` | string | Name of the analysis run |
| `created_at` | string | ISO timestamp of when the run was created |
| `split_by_criterion` | boolean | Whether criteria were evaluated in separate LLM calls |
| `reasoning_enabled` | boolean | Whether LLM reasoning/thinking was enabled |
| `reasoning_effort` | string | Reasoning effort level (`none`, `low`, `medium`, `high`) |

### Import Behaviour

- Unknown fields are silently ignored
- Missing `criteria` defaults to an empty list
- `default_scoring_system` accepts both canonical values (`percent`, `binary`, `five`) and display labels (`0-100%`, `0/1`, `0-5`)
- `reasoning_enabled` and the legacy `reasoning_mode` field are both accepted

## Modifying Prompts Without Code Changes

### Change Analysis Approach

1. Edit `general-prompt.md` to modify the high-level analysis strategy:

```markdown
# Original approach
Analyze the issue description. Evaluate whether it is clear, complete, measurable...

# Modified approach for strict compliance
Analyze the issue description against security best practices. Focus on:
- Authentication and authorization
- Data protection measures
- Input validation
- Error handling
- Audit trail requirements
```

2. Edit `system-prompt.md` to change the LLM's persona:

```markdown
# Original persona
You are a strict but constructive Jira issue quality analyst...

# Modified security-focused persona
You are a cybersecurity expert specializing in secure development practices...
```

Without restarting the application - changes are loaded dynamically.

### Add New Criterion

1. Edit `resources/prompts/default/criteria-config.json`:

```json
{
  "version": 1,
  "criteria": [
    {
      "title": "Completeness and specificity",
      "description": "Check whether the issue contains concrete names, links, versions, API signatures, expected behavior, and enough context to act on it.",
      "scoring_system": "percent",
      "include_review": true
    },
    {
      "title": "Security considerations",
      "description": "Evaluate whether the issue addresses security implications, including authentication, authorization, data protection, and compliance requirements.",
      "scoring_system": "five",
      "include_review": true,
      "key": "security"
    }
  ]
}
```

2. Restart the application - the new criterion will automatically appear in analysis.

### Modify Output Requirements

1. Edit `structured-analysis-prompt.md` to change the output requirements section:

```markdown
Output requirements:
- Return only valid JSON. Do not include markdown or explanatory text outside JSON.
- Follow the JSON schema below exactly and keep the exact criterion ids.
- Put every criterion result into the top-level "criteria" object.
- Each criterion result must include title, description, scoring_system, and score.
- Include a criterion review field only when that criterion explicitly asks for it.
- For each criterion, include recommendations as an array of 1-3 specific suggestions.
- Put a compact score map into "criteria_scores" for downstream parsing.
- criteria_scores values must mirror the matching criteria.*.score values.
- Compute total_score as the average of all criteria_scores.
- Aggregate all unique criterion recommendations into the top-level recommendations list.
- Provide a separate section for security recommendations per issue type.
- Do not add criteria that are not listed in the schema.
- For binary criteria, score must be 0 or 1.
- For percent criteria, score must be an integer from 0 to 100.
- For five-point criteria, score must be an integer from 0 to 5.
```

## Practical Examples

### Example 1: Mobile Development Focus

**Goal**: Customize analysis for mobile application issues.

**Changes required**:

1. `general-prompt.md`:
```markdown
Analyze the mobile app issue description. Evaluate user experience considerations including:
- Mobile-specific UI/UX patterns
- Touch interface design
- Screen responsiveness
- Battery and performance impact
- Mobile platform guidelines (iOS/Android)
```

2. `criteria-config.json`:
```json
{
  "version": 1,
  "criteria": [
    {
      "title": "Mobile UX Compliance",
      "description": "Check whether the issue considers mobile-specific UX patterns, touch targets, navigation patterns, and mobile design guidelines.",
      "scoring_system": "five",
      "include_review": true
    },
    {
      "title": "Platform Specificity",
      "description": "Evaluate whether the issue specifies target mobile platforms (iOS/Android) and platform-specific requirements or constraints.",
      "scoring_system": "percent",
      "include_review": false
    }
  ]
}
```

### Example 2: Data Quality Focus

**Goal**: Emphasize data completeness and validation in analysis.

**Changes required**:

1. `system-prompt.md`:
```markdown
You are a data quality specialist focused on completeness, accuracy, consistency, and validity of data requirements in Jira issues.
```

2. `criteria-config.json`:
```json
{
  "version": 1,
  "criteria": [
    {
      "title": "Data Completeness",
      "description": "Check whether the issue specifies all required data fields, data structures, input sources, and output formats.",
      "scoring_system": "percent",
      "include_review": true
    },
    {
      "title": "Validation Requirements",
      "description": "Evaluate whether data validation rules, error handling, and data quality checks are clearly defined.",
      "scoring_system": "percent",
      "include_review": true
    }
  ]
}
```

### Example 3 compliance Focus

**Goal**: Customize analysis for compliance/regulatory requirements.

**Changes required**:

1. `general-prompt.md`:
```markdown
Analyze the compliance issue description. Evaluate regulatory considerations including:
- Applicable regulations and standards
- Compliance documentation requirements
- Audit trail needs
- Data privacy considerations
- Risk assessment completeness
```

2. `criteria-config.json`:
```json
{
  "version": 1,
  "criteria": [
    {
      "title": "Regulatory Coverage",
      "description": "Check whether the issue identifies applicable regulations, standards, and compliance frameworks.",
      "scoring_system": "binary",
      "include_review": true
    },
    {
      "title": "Documentation Requirements",
      "description": "Evaluate whether compliance documentation, evidence collection, and audit requirements are specified.",
      "scoring_system": "percent",
      "include_review": false
    }
  ]
}
```

## Step-by-Step Customization Guide

### Step 1: Backup Current Configuration

```bash
# Create a backup of current templates
cp -r resources/prompts resources/prompts.backup
```

### Step 2: Identify Customization Scope

Determine what you want to change:

* Analysis approach → Edit `general-prompt.md`
* LLM persona → Edit `system-prompt.md`
* Evaluation criteria → Edit `criteria-config.json`
* Output format → Edit `structured-analysis-prompt.md`
* Criterion format → Edit `templates/criterion-format.md`

### Step 3: Make Targeted Changes

Edit only the files that need modification.

For adding criteria:
1. Add to `criteria-config.json`
2. Test with a single issue first
3. Validate output format matches expectations

For modifying prompts:
1. Edit the appropriate `.md` file
2. Preserve placeholder syntax
3. Test with various issue types

### Step 4: Validate Changes

```bash
# Run analysis with test data
python -m jira_analyzer --input test_issue.json --output test_result.json

# Verify output structure
jq keys test_result.json
```

### Step 5: Document Your Changes

Create a `resources/prompts/customization.md` documenting:

* What was changed and why
* Use case for the customization
* Any special considerations
* Validation approach

## Advanced Customization

### Creating Domain-Specific Templates

You can create multiple template sets for different domains:

```
resources/prompts/
├── default/
│   ├── criteria-config.json
│   └── instructions.json
├── mobile-dev/
│   ├── criteria-config.json
│   └── instructions.json
├── compliance/
│   ├── criteria-config.json
│   └── instructions.json
└── data-quality/
    ├── criteria-config.json
    └── instructions.json
```

Each domain-specific directory contains both the criteria configuration and the scoring instructions for that domain.

### Conditional Instructions

The system supports conditional instructions in `structured-analysis-prompt.md`:

```markdown
{overall_instruction}
```

This placeholder automatically expands to include or exclude the "overall_conclusion" field based on the `include_overall_conclusion` configuration flag.

### Custom Criterion Keys

Override automatic key generation by specifying the `key` property:

```json
{
  "title": "Long and Complex Title That Would Generate Ugly Keys",
  "description": "Description here",
  "scoring_system": "percent",
  "key": "custom_key"
}
```

## Troubleshooting

### Template Not Loading

**Symptom**: Changes to template files aren't reflected in analysis.

**Solution**: 
1. Verify file paths are correct
2. Check file encoding is UTF-8
3. Ensure placeholders are properly formatted with curly braces
4. Restart the application to force template reload

### Invalid JSON Schema

**Symptom**: LLM outputs invalid JSON or missing fields.

**Solution**:
1. Check `criteria-config.json` syntax
2. Verify scoring system values are valid (`binary`, `percent`, `five`)
3. Ensure all required fields are present
4. Validate JSON using `jq . resources/prompts/default/criteria-config.json`

### Criteria Not Appearing in Output

**Symptom**: Configured criteria missing from LLM response.

**Solution**:
1. Check `criterion_format.md` template is properly configured
2. Verify placeholder replacement is working
3. Ensure criteria titles and descriptions are not empty
4. Check for JSON parsing errors in logs

### Scoring System Not Working

**Symptom**: Unexpected scoring values or invalid ranges.

**Solution**:
1. Verify scoring system type matches expected usage
2. Check scoring instruction lookup in `prompt_builder.py`
3. Test scoring system with sample output
4. Review scoring label template configuration

## Best Practices

### File Organization
* Keep template files as pure markdown for readability
* Use descriptive custom keys for complex criteria
* Document any non-standard modifications
* Maintain separate template sets for different use cases

### Placeholder Usage
* Preserve all required placeholders in templates
* Ensure placeholder syntax is exactly `{variable_name}`
* Test placeholder replacement after any template changes
* Avoid using curly braces for other purposes in templates

### Criteria Configuration
* Use meaningful, descriptive titles
* Keep descriptions concise but comprehensive
* Choose appropriate scoring systems for each criterion
* Set `include_review` flag thoughtfully based on analysis depth

### Testing and Validation
* Always test with real Jira issues before deployment
* Validate output structure matches expected JSON schema
* Use multiple issue types and complexity levels in testing
* Monitor LLM performance for degraded response quality after changes

### Version Control
* Commit template changes with descriptive messages
* Tag significant template version changes
* Use branches for experimental customizations
* Maintain changelog of prompt modifications

## Technical Implementation Notes

The template system is implemented in `prompt_builder.py`:

* `_load_template()` - Loads template files from resources directory
* `_load_criteria_config()` - Parses JSON configuration into CriterionConfig objects
* `_load_instructions()` - Loads instructions.json with scoring data and labels
* `build_structured_prompt()` - Assembles the final prompt with placeholder replacement
* `_format_criterion()` - Formats individual criteria using template components
* `_build_json_schema_text()` - Generates valid JSON schema for LLM output

All placeholder replacement uses `.replace()` to avoid conflicts with JSON curly braces in template content. Loading functions raise immediate exceptions (FileNotFoundError, KeyError) for missing data as part of fail-fast behavior.

## Future Enhancements

Potential improvements to consider:

* Support for language-specific templates
* Template validation and schema checking
* Built-in A/B testing framework for prompt variants
* Template versioning and rollback capability
* Web interface for prompt editing without file access
* Export/import functionality for template configurations
* Integration with prompt management platforms