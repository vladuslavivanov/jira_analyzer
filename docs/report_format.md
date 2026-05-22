# Analysis Report Format

## Overview

This document describes the format and structure of the analysis report displayed in the Jira AI Analyzer Streamlit application. The report is generated after analyzing Jira issues using AI-based quality assessment.

## Report Layout

The analysis report uses a **master-detail layout** consisting of:

### Master List (Task Selection)

A dropdown list (selectbox) that displays all analyzed issues in the format:
```
{task_id} - {title truncated to 50 chars}...
```

Example:
```
PROJ-001 - Fix login bug with user authentication failure...
```

**Behavior:**
- User selects one task from the list
- Selection updates the detail panel below
- Tasks are sorted by their original order in the analysis

### Detail Panel

The detail panel is divided into two equal columns (50/50 split):

#### Left Column: Task Information

Displays metadata about the analyzed Jira issue:

| Field | Description | Source |
|-------|-------------|--------|
| **Task ID** | Jira issue key (e.g., PROJ-001) | `result['key']` or `result['jira_key']` |
| **Task Title** | Issue title or description | `result['title']` or `result['input_description']` |
| **Status** | Jira issue status | `result['status']` |
| **Type** | Issue type (Bug, Task, Story, etc.) | `result['input_element_type']` |
| **Assignee** | Person assigned to the issue | `result['assignee']` |
| **Updated At** | Last update timestamp | `result['updated_at']` |

**Notes:**
- Title is truncated to 100 characters if it's too long
- "Not assigned" is shown if assignee is missing
- "Unknown" is shown for missing fields

#### Right Column: Quality Analysis

Displays the AI-generated quality assessment:

| Component | Description | Source |
|-----------|-------------|--------|
| **Quality Score** | Overall quality score with color coding | `result['total_score']` or `result['overall_score']` |
| **Conclusion** | Overall assessment of issue quality | `result['overall_conclusion']` or `result['rationale']` |
| **Criteria Breakdown** | Expandable section with detailed criteria scores | `result['criteria']` |

**Score Color Coding:**

| Score Range | Color | Meaning |
|-------------|-------|---------|
| 1-40 | Red | Poor quality - needs significant improvement |
| 41-70 | Orange | Moderate quality - has issues |
| 71-100 | Green | Good quality - meets criteria |

**Scoring Options:**
- **Percentage-based (0-100)**: Displayed as "75%"
- **Range-based (0-10)**: Displayed as "8/10"
- **Missing**: Displayed as "N/A"

### Criteria Breakdown (Expandable Section)

When expanded, shows detailed scores for each quality criterion:

```
## Criterion 1: Completeness and specificity
Score: 80/100
Review: The issue provides good context but could be more specific about API versions.

## Criterion 2: Measurability and acceptance criteria
Score: 60/100
Review: Lacks clear success criteria and acceptance tests.
```

Each criterion includes:
- **Criterion Title**: Name of the quality criterion
- **Score**: Individual score for this criterion
- **Review** (optional): Detailed explanation from the AI

### Recommendations Section

Displays actionable suggestions for improving the issue:

```
Recommendations:

1. Add specific API version requirements
2. Include browser compatibility information
3. Define clear acceptance criteria with quantifiable metrics
```

**Source**: `result['recommendations']`

**Format:** Numbered list (1, 2, 3, ...)

### Download Button

Provides a JSON export of the full analysis result:

- **Label**: "Download Result (JSON)" / "Скачать результат (JSON)" (localized)
- **File Name**: `{task_id}_analysis.json`
- **Content**: Complete result object including all fields

**JSON Output Format:**

```json
{
  "key": "PROJ-001",
  "jira_key": "PROJ-001",
  "title": "Fix login bug",
  "description": "Users cannot login after upgrade",
  "status": "Open",
  "assignee": "john.doe",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-16T14:20:00Z",
  "input_element_type": "Bug",
  "input_description": "Users cannot login...",
  "total_score": 75.0,
  "overall_conclusion": "Good issue with clear scope...",
  "criteria": {
    "completeness_and_specificity": {
      "title": "Completeness and specificity",
      "description": "Check whether the issue contains concrete names...",
      "scoring_system": "percent",
      "score": 80,
      "review": "The issue provides good context...",
      "recommendations": ["Add API version requirements"]
    }
  },
  "criteria_scores": {
    "completeness_and_specificity": 80,
    "measurability_and_acceptance_criteria": 70
  },
  "recommendations": [
    "Add specific API version requirements",
    "Include browser compatibility information"
  ]
}
```

## Data Flow

### Analysis Pipeline

```
1. Input: Jira issues (from JQL, single issue key, or JSON file)
   ↓
2. AI Analysis: LLM evaluates each issue against quality criteria
   ↓
3. Storage: Results saved to SQLite database
   ↓
4. Display: _render_results() function formats and shows the report
   ↓
5. User Interaction: User selects task, views details, downloads JSON
```

### Data Format Mapping

| LLM Response | Display Field | Storage Column |
|--------------|---------------|----------------|
| `total_score` | Quality Score | `total_score` |
| `overall_conclusion` | Conclusion | `summary` |
| `recommendations` (array) | Recommendations | `recommendations` |
| `criteria` (object) | Criteria Breakdown | `raw_response` |
| `key` | Task ID | `task_id` |
| `input_description` | Title | `title` |
| `status` | Status | `status` |

## Error Handling

### Display Errors

If an analysis fails, the report displays an error message:

```
**Error:** [error_message]
```

**Example:**
```
**Error:** No description provided
```

**Behavior:**
- Failed analyses are filtered out from the master list
- Only valid results are shown in the dropdown
- Error details are shown in the detail panel when error is present

### Missing Data

When data is missing, the following fallbacks are used:

| Field | Missing Value Display |
|-------|---------------------|
| Task ID | "Unknown" |
| Title | "No title" |
| Status | "Unknown" |
| Type | "Unknown" |
| Assignee | "Not assigned" |
| Score | "N/A" |
| Conclusion | Not displayed |

## Internationalization

All UI text supports English and Russian:

| English | Russian | Translation Key |
|---------|---------|-----------------|
| Select Task | Выберите задачу | `select_task` |
| Task Information | Информация о задаче | `task_information` |
| Task ID | ID Задачи | `task_id` |
| Task Title | Название задачи | `task_title` |
| Quality Analysis | Анализ качества | `quality_analysis` |
| Quality Score | Оценка качества | `quality_score` |
| Download Result (JSON) | Скачать результат (JSON) | `download_result` |

**Language Selection:** Available in the sidebar settings

## Implementation Details

### Primary Function

**File**: `src/jira_analyzer/main.py`  
**Function**: `_render_results(results, language: str)`

**Parameters:**
- `results`: List of analysis result dictionaries
- `language`: Language code ("en" or "ru")

### Key Features

1. **Filtering**: Removes error results from display
2. **Localization**: Uses `get_text()` function for all UI strings
3. **Flexibility**: Handles multiple score formats and field mappings
4. **Export**: Provides JSON download of complete analysis

### Related Components

- **Results Viewer**: `src/jira_analyzer/ui/results_viewer.py` - Similar layout for viewing stored results
- **Database Repository**: `src/jira_analyzer/storage/sqlite_repository.py` - Stores analysis results
- **Translations**: `src/jira_analyzer/i18n/translations.py` - Provides localized strings

## User Experience

### Typical Workflow

1. **Run Analysis**: User navigates to Analysis page, configures options, clicks "Run Analysis"
2. **View Report**: Analysis completes, report automatically appears below
3. **Browse Results**: User uses dropdown to select different tasks
4. **Review Details**: User reads task info and quality assessment
5. **Explore Criteria**: User expands "Criteria Breakdown" to see detailed scores
6. **Review Recommendations**: User reads actionable suggestions
7. **Download**: User clicks download button to export full JSON

### Visual Hierarchy

```
Analysis Report
├── [Dropdown: Select Task]
├── ───── [Divider]
├── [Column 1: Task Information]
│   ├── **Task ID**: PROJ-001
│   ├── **Task Title**: Fix login bug
│   ├── **Status**: Open
│   ├── **Type**: Bug
│   ├── **Assignee**: john.doe
│   └── **Updated At**: 2025-01-16 14:20:00
│
├── [Column 2: Quality Analysis]
│   ├── ### Quality Score: 75%
│   └── **Conclusion**: Good issue with clear scope...
│       └── [Expandable: Criteria Breakdown]
│
├── Recommendations
│   ├── 1. Add specific API version requirements
│   └── 2. Include browser compatibility information
│
└── [Download Button]
```

## Customization

### Modifying Score Color Ranges

Edit the color logic in `_render_results()`:

```python
if 1 <= total_score <= 40:
    color = "red"
elif 41 <= total_score <= 70:
    color = "orange"
else:
    color = "green"
```

### Adding Custom Fields

Add new fields to the display by extending the column sections:

```python
# In Left Column
custom_field = result.get("custom_field", "Not set")
st.write(f"**Custom Field:** {custom_field}")

# In Right Column
custom_score = result.get("custom_score")
if custom_score:
    st.write(f"**Custom Score:** {custom_score}")
```

### Changing Layout Proportions

Modify the columns split ratio:

```python
# 40% left, 60% right
col1, col2 = st.columns([0.4, 0.6])
```

## Performance Considerations

- **Caching**: No caching used - fresh data loaded each time
- **Large Result Sets**: All results shown in dropdown (no pagination)
- **JSON Export**: Performed on-demand, not pre-generated
- **Criteria Expansion**: Lazy-loaded when user clicks expand

## Troubleshooting

### Common Issues

**Issue**: "[missing:select_task]" shown in UI
- **Cause**: Translation key not defined or missing
- **Fix**: Add key to `src/jira_analyzer/i18n/translations.py`

**Issue**: Scores showing as "N/A"
- **Cause**: Analysis returned no score or invalid format
- **Fix**: Check `total_score` field in raw response

**Issue**: Criteria breakdown not showing
- **Cause**: No criteria data in analysis result
- **Fix**: Verify LLM response includes `criteria` object

**Issue**: Download button not working
- **Cause**: Invalid JSON structure or large data size
- **Fix**: Check browser console for errors, simplify result structure

## Future Enhancements

Potential improvements to the report:

1. **Search/Filter**: Add search box to filter tasks in dropdown
2. **Sort Options**: Allow sorting by score, status, or update time
3. **Comparison Mode**: View multiple tasks side-by-side
4. **Trend Analysis**: Show score changes over time
5. **Export Formats**: CSV, Excel, or PDF export options
6. **Print-friendly**: Optimized layout for printing reports
7. **Annotations**: Add user notes to results
8. **Share Links**: Generate shareable URLs for specific analyses

## References

- **Streamlit Results Spec**: `.agent/specs/07-streamlit-results-viewer.md`
- **UI Refactor ADR**: `.agent/knowledge/ADR-005-streamlit-ui-refactor.md`
- **Prompt Builder**: `src/jira_analyzer/analyzer/core/llm/prompt_builder.py`
- **Analysis Service**: `src/jira_analyzer/analyzer/service.py`

---

**Document Version**: 1.0  
**Last Updated**: 2025-05-22  
**Maintainer**: Student MVP Project Team