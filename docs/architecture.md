# Jira AI Analyzer - Current Architecture Specification

**Date:** May 12, 2026  
**Version:** 0.1.0  
**Status:** Post-Phase 1 Refactoring

## System Overview

Jira AI Analyzer is a containerized microservice application that performs AI-driven quality analysis of Jira task tracker issues. It supports parallel processing, multiple LLM providers, and flexible storage backends.

## Core Components

### 1. **Analysis Service** (`src/jira_analyzer/analyzer/service.py`)
- **Purpose:** Orchestrates analysis workflows and LLM usage
- **Features:**
  - Parallel issue processing with configurable workers
  - Split-by-criterion analysis for non-reasoning LLMs
  - LLM provider abstraction with request queuing
  - Error handling and result merging

### 2. **LLM Client** (`src/jira_analyzer/analyzer/core/llm/client.py`)
- **Purpose:** Manages queued LLM requests with concurrency control
- **Features:**
  - Configurable worker pools
  - Request queuing and batching
  - Async support for future enhancements

### 3. **LLM Provider Interface** (`src/jira_analyzer/analyzer/core/llm/provider.py`)
- **Purpose:** Abstraction for LLM communication
- **Implementations:**
  - DeepSeekProvider (OpenAI-compatible API)
  - Extensible for future providers (OpenAI, Claude, etc.)

### 4. **Analysis Engine** (`src/jira_analyzer/analyzer/engine.py`)
- **Purpose:** Simplified wrapper delegating to AnalysisService
- **Features:** Backward compatibility with existing CLI/Streamlit code

### 5. **Storage Layer** (`src/jira_analyzer/storage/`)
- **Purpose:** Flexible result persistence
- **Implementations:**
  - **SqliteAnalysisResultRepository**: SQLite database storage
  - **File-based**: JSON file output (legacy)
- **Interface:** `AnalysisResultRepository` abstraction

### 6. **User Interfaces**
- **Streamlit Web UI** (`src/jira_analyzer/app/streamlit.py`): Interactive browser interface
- **CLI** (`src/jira_analyzer/app/cli.py`): Command-line interface with uv build tool
- **Unified Entry Points:** Both interfaces delegate to AnalysisService

### 7. **Task Tracker Integration**
- **Jira Client** (`src/jira_analyzer/tasktracker/jira/jira_client.py`): REST API communication
- **Jira Parser** (`src/jira_analyzer/tasktracker/jira/jira_parser.py`): Data transformation
- **Mock Jira Server** (`src/mock_jira/server.py`): Testing double

### 8. **Configuration & Utils**
- **Config** (`src/jira_analyzer/utils/config.py`): Environment-based configuration
- **Logger** (`src/jira_analyzer/utils/logger.py`): Structured logging
- **Prompt Builder** (`src/jira_analyzer/analyzer/core/llm/prompt_builder.py`): Template-based prompts

## Data Flow

```
User Input (CLI/Web UI)
    ↓
Analysis Service
    ├─→ LLM Client ─→ LLM Provider ─→ DeepSeek API
    ├─→ Task Tracker ─→ Jira Client ─→ Real/Mock Jira
    └─→ Progress Tracking ─→ Storage Layer (Analysis Sessions)
        ↓
    Analysis Results
        ├─→ Storage Layer ─→ SQLite DB (Persistent Results)
        ├─→ UI Access ─→ Streamlit (Real-time Progress/Results)
        └─→ Report Generation ─→ Markdown/Statistics (From Stored Data)
```

## Key Architectural Decisions

### 1. **Service Layer Pattern**
- **Decision:** Extract orchestration logic into dedicated AnalysisService
- **Rationale:** Separate algorithm from workflow coordination
- **Benefit:** Better testability and maintainability

### 2. **Provider Abstraction**
- **Decision:** LLM provider interface with pluggable implementations
- **Rationale:** Enable multi-provider support without code changes
- **Benefit:** Future-proof for different LLM backends

### 3. **Repository Pattern for Storage**
- **Decision:** Abstract data persistence behind repository interfaces
- **Rationale:** Decouple business logic from storage details
- **Benefit:** Easy to swap storage backends (SQLite, PostgreSQL, cloud)

### 4. **Request Queuing**
- **Decision:** Queue LLM requests with configurable concurrency
- **Rationale:** Handle API rate limits and optimize resource usage
- **Benefit:** Better reliability and performance control

### 5. **Split-Criteria Analysis**
- **Decision:** Support per-criterion LLM requests for complex analysis
- **Rationale:** Enable use with non-reasoning LLMs
- **Benefit:** Broader LLM compatibility

### 6. **Persistent Analysis State** ⭐ *NEW*
- **Decision:** Store analysis progress and results in persistent storage
- **Rationale:** Enable resumable analysis, UI access, and historical reporting
- **Benefit:** User can track progress, access results from UI, generate reports from stored data

### 7. **Simplified Storage Model** ⭐ *UPDATED*
- **Decision:** Minimal data model - only issue info + analysis results
- **Rationale:** Keep it simple for current web-service needs, future analytics can extend
- **Benefit:** Fast implementation, easy maintenance, overwrite semantics for re-analysis

## Storage Options

| Backend | Use Case | Configuration | Features |
|---------|----------|---------------|----------|
| **SQLite** | Current implementation, simple persistence | `--output results.db` | Issue + result storage, overwrite on re-analysis |
| **JSON Files** | Legacy, simple export | `--output results.json` | Basic result export |
| **Future: PostgreSQL** | Enterprise scaling | Repository pattern ready | Extended analytics, concurrent access |

### Storage Requirements ⭐ *UPDATED*
- **Issue + Result Storage:** Only essential issue metadata and analysis results
- **Overwrite Semantics:** Re-analysis replaces previous results (no history)
- **Repository Abstraction:** SQLite now, extensible to other DBs later
- **Future Analytics:** Schema can be extended without breaking changes

## External Dependencies

- **LLM Providers:** DeepSeek (primary), OpenAI-compatible APIs
- **Task Trackers:** Jira REST API, extensible to others
- **Build Tool:** uv (Python package manager)
- **UI Framework:** Streamlit
- **Database:** SQLite (built-in), extensible to others

## Deployment

- **Containerized:** Docker support included
- **Entry Points:** `jira-analyzer` (web UI), `mock-jira` (test server)
- **Environment:** Python 3.12+, virtual environment via uv

## Testing Strategy

- **Unit Tests:** Component isolation with mocks
- **Integration Tests:** End-to-end workflows
- **Mock Services:** Jira server for testing without external dependencies
- **Provider Compatibility:** Test with different LLM backends

## Future Extensions

- **Multi-LLM Support:** OpenAI, Claude, local models
- **Additional Task Trackers:** Azure DevOps, GitHub Issues
- **Advanced Storage:** PostgreSQL, cloud databases
- **Caching Layer:** Redis for LLM response caching
- **Async Processing:** Full async support for high-throughput scenarios
- **Analysis Analytics:** ⭐ Trend analysis, quality metrics, performance insights
- **Real-time UI:** ⭐ Live progress tracking, result visualization
- **Report Automation:** ⭐ Scheduled reports from stored analysis data

---

**Architecture Status:** Phase 1 Complete (Foundation Layer)
- ✅ Service layer extraction
- ✅ LLM provider abstraction
- ✅ Storage repository pattern
- 🔄 **NEW:** Persistent analysis state and progress tracking
- 🔄 **NEW:** UI-accessible results and real-time progress
- 🔄 **NEW:** Analytics-ready data model
- ⏳ Phase 2: Controller and task repository abstractions
- ⏳ Phase 3: Caching and resilience patterns