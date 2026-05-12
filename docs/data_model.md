# Jira AI Analyzer - Simplified Data Model Specification

**Date:** May 12, 2026
**Version:** 0.1.0
**Status:** Minimal Viable Implementation

## Overview

Simplified data model for basic issue analysis storage. Only essential data is stored - issue information and analysis results. Future analytics data will be added later.

**Key Principles:**
- **Minimal Storage:** Only issue metadata + analysis results
- **Overwrite on Re-analysis:** No historical versions, latest result only
- **SQLite First:** Current implementation uses SQLite
- **Future-Proof:** Repository abstraction enables DB migration

## Core Entity: Analyzed Issues

**Purpose:** Store issue information and latest analysis results

**Schema:**
```sql
CREATE TABLE analyzed_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_key TEXT UNIQUE NOT NULL,       -- Jira issue key (e.g., 'YA-1')
    element_type TEXT NOT NULL,           -- Issue type (Task, Risk, etc.)
    title TEXT,                           -- Issue title/summary
    description TEXT,                     -- Issue description
    status TEXT,                          -- Jira status
    assignee TEXT,                        -- Assigned user
    project_key TEXT,                     -- Project identifier
    created_at TEXT NOT NULL,             -- Record creation timestamp
    updated_at TEXT NOT NULL,             -- Last analysis timestamp
    analysis_result TEXT NOT NULL,        -- Complete analysis JSON
    analysis_score REAL,                  -- Overall quality score (0-100)
    analysis_verdict TEXT,                -- Accept/Reject/Review
    processing_time_ms INTEGER,           -- Analysis duration
    error_message TEXT                    -- Error if analysis failed
);
```

**Key Fields:**
- `issue_key`: Unique identifier, overwritten on re-analysis
- `analysis_result`: Complete JSON result from LLM
- `analysis_score/verdict`: Extracted summary fields for quick queries
- `updated_at`: When this issue was last analyzed

## Data Relationships

No complex relationships - single table design for simplicity.

## JSON Structure for Analysis Result

```json
{
  "criteria": {
    "completeness": {
      "title": "Completeness and specificity",
      "score": 85,
      "review": "Good detail level..."
    },
    "measurability": {
      "title": "Measurability",
      "score": 70,
      "review": "Needs clearer acceptance criteria..."
    }
  },
  "criteria_scores": {
    "completeness": 85,
    "measurability": 70
  },
  "overall_conclusion": "Issue meets basic quality standards...",
  "overall_score": 78,
  "verdict": "Accept"
}
```

## Indexes for Performance

```sql
CREATE INDEX idx_issues_key ON analyzed_issues(issue_key);
CREATE INDEX idx_issues_project ON analyzed_issues(project_key);
CREATE INDEX idx_issues_updated ON analyzed_issues(updated_at DESC);
CREATE INDEX idx_issues_score ON analyzed_issues(analysis_score);
```

## Repository Abstraction

**Interface:** `AnalysisResultRepository`
```python
class AnalysisResultRepository(ABC):
    @abstractmethod
    def save_issue_analysis(self, issue_key: str, analysis_data: dict) -> None:
        """Save or update issue analysis result"""

    @abstractmethod
    def get_issue_analysis(self, issue_key: str) -> dict | None:
        """Get latest analysis for issue"""

    @abstractmethod
    def get_project_analyses(self, project_key: str) -> list[dict]:
        """Get all analyses for project"""

    @abstractmethod
    def get_recent_analyses(self, limit: int = 100) -> list[dict]:
        """Get most recently analyzed issues"""
```

**SQLite Implementation:** `SqliteAnalysisResultRepository`
- Uses `analyzed_issues` table
- Overwrites existing records on re-analysis
- Supports future migration to PostgreSQL/MySQL

## Data Lifecycle

### Issue Analysis Flow
1. **New Issue:** Insert new record in `analyzed_issues`
2. **Re-analysis:** Update existing record (same `issue_key`)
3. **No History:** Previous analyses are lost (by design)

### Data Retention
- **All Records:** Retained indefinitely for analytics
- **Cleanup:** Manual deletion if needed (future feature)

## Implementation Status

### ✅ Completed
- Repository abstraction interface
- SQLite implementation with basic CRUD operations
- Integration with AnalysisService
- Test coverage for storage layer

### 🔄 Current Phase: Basic Storage Integration
- [ ] Update AnalysisService to save results to database
- [ ] Add CLI option to save to database
- [ ] Wire Streamlit UI to display/save analysis results

### 🔮 Future Phases
- **Phase 2:** UI Integration (Add analysis sessions for progress tracking)
- **Phase 3:** Analytics Foundation (Add metrics calculation, trend analysis)
- **Phase 4:** Advanced Features (Dashboard, reporting, cleanup)

## API Integration

### Service Layer
```python
class AnalysisService:
    def __init__(self, result_repository: AnalysisResultRepository):
        self.result_repository = result_repository

    def analyze_issue(self, issue: dict) -> dict:
        # ... analysis logic ...
        self.result_repository.save_issue_analysis(issue['key'], result)
        return result
```

### CLI Usage
```bash
# Save to database instead of JSON
jira-analyzer --jira-server ... --output results.db

# Query existing results
jira-analyzer --query-project PROJ --output report.md
```

---

**Data Model Status:** Minimal Viable Implementation
- ✅ Essential issue + result storage only
- ✅ Overwrite semantics (no history)
- ✅ SQLite implementation
- ✅ Repository abstraction for future DB flexibility
- 🔄 Implementation: Basic storage layer integration</content>
<parameter name="filePath">/Users/i1turin/Projects/ipkn-jira-ai-linter/jira_analyzer/docs/data_model.md