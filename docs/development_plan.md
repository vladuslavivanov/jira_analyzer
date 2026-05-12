# Jira AI Analyzer - Development Plan

**Date:** May 12, 2026
**Version:** 0.1.0
**Status:** Ready for Implementation

## Overview

This development plan outlines the implementation of simplified persistent storage for the Jira AI Analyzer. The focus is on minimal viable storage - only essential issue information and analysis results, with overwrite semantics for re-analysis.

## Current Status

### ✅ Completed (Phase 1 Foundation)
- **Service Layer:** `AnalysisService` with parallel processing and split-criteria support
- **LLM Provider Abstraction:** Interface with DeepSeek implementation and request queuing
- **Repository Pattern:** `AnalysisResultRepository` interface with SQLite implementation
- **Basic Storage:** SQLite repository with CRUD operations and test coverage
- **Architecture:** Simplified data model with single `analyzed_issues` table

### 🔄 Current Phase: Basic Storage Integration
**Goal:** Wire the storage layer into the analysis workflow

## Development Plan

### Phase 1.5: Storage Integration

#### 1.1 Update AnalysisService to Save Results
**Objective:** Modify `AnalysisService` to persist analysis results to database
**Tasks:**
- [ ] Add `AnalysisResultRepository` dependency to `AnalysisService.__init__()`
- [ ] Update `analyze_issue()` method to save results after analysis
- [ ] Extract summary fields (score, verdict) from analysis result for quick queries
- [ ] Add error handling for storage failures
- [ ] Update method signatures to accept repository parameter

**Files to Modify:**
- `src/jira_analyzer/analyzer/service.py`
- `src/jira_analyzer/analyzer/engine.py` (backward compatibility)

**Testing:**
- [ ] Unit tests for service with repository integration
- [ ] Integration tests with SQLite storage
- [ ] Verify overwrite behavior on re-analysis

#### 1.2 Update CLI to Support Database Output
**Objective:** Add `--output-db` option to save results to SQLite database
**Tasks:**
- [ ] Add database output option to CLI argument parser
- [ ] Initialize `SqliteAnalysisResultRepository` when database output requested
- [ ] Pass repository to `AnalysisService`
- [ ] Maintain backward compatibility with JSON file output
- [ ] Add validation for database file path

**Files to Modify:**
- `src/jira_analyzer/app/cli.py`

**Testing:**
- [ ] CLI integration tests with database output
- [ ] Verify database file creation and data persistence
- [ ] Test with both JSON and database outputs

#### 1.3 Update Output Handler for Database Queries
**Objective:** Enable querying existing analysis results from database
**Tasks:**
- [ ] Add database query functionality to `OutputHandler`
- [ ] Implement methods to retrieve results by project/issue
- [ ] Add CLI options for querying existing results
- [ ] Generate reports from stored analysis data

**Files to Modify:**
- `src/jira_analyzer/app/output_handler.py`

**Testing:**
- [ ] Query functionality tests
- [ ] Report generation from database
- [ ] Error handling for missing data

### Phase 2: UI Integration

#### 2.1 Add Analysis Sessions for Progress Tracking
**Objective:** Implement basic session tracking for UI progress display
**Tasks:**
- [ ] Create `analysis_sessions` table schema
- [ ] Add session management to repository interface
- [ ] Update `AnalysisService` to create/manage sessions
- [ ] Add progress update methods

**Files to Create/Modify:**
- `src/jira_analyzer/storage/sqlite_repository.py` (extend)
- `src/jira_analyzer/analyzer/service.py` (add session methods)

#### 2.2 Wire Streamlit UI to Database
**Objective:** Connect Streamlit interface to persistent storage
**Tasks:**
- [ ] Add database connection options to Streamlit UI
- [ ] Display saved analysis results in UI
- [ ] Add result browsing and filtering capabilities
- [ ] Show analysis history and re-run options

**Files to Modify:**
- `src/jira_analyzer/app/streamlit.py`

**Testing:**
- [ ] UI integration tests with database
- [ ] Result display and navigation
- [ ] Performance with large result sets

### Phase 3: Analytics Foundation

#### 3.1 Add Basic Analytics Queries
**Objective:** Implement simple analytics on stored data
**Tasks:**
- [ ] Add aggregation queries (average scores by project/type)
- [ ] Implement trend analysis (score changes over time)
- [ ] Add filtering and sorting capabilities
- [ ] Create basic dashboard views

#### 3.2 Performance Optimization
**Objective:** Optimize database queries and add caching
**Tasks:**
- [ ] Add database indexes for common queries
- [ ] Implement query result caching
- [ ] Add pagination for large result sets
- [ ] Optimize bulk operations

### Phase 4: Advanced Features

#### 4.1 Data Cleanup and Maintenance
**Objective:** Add data management capabilities
**Tasks:**
- [ ] Implement data cleanup policies
- [ ] Add data export/import functionality
- [ ] Create backup and restore procedures

#### 4.2 Multi-Database Support
**Objective:** Enable migration to PostgreSQL/MySQL
**Tasks:**
- [ ] Implement PostgreSQL repository
- [ ] Add database migration tools
- [ ] Update configuration for multiple DB backends

## Implementation Priorities

### Immediate (This Week)
1. **Storage Integration** - Wire AnalysisService to save results
2. **CLI Database Support** - Add `--output-db` option
3. **Basic Querying** - Enable result retrieval and reporting

### Short-term (Next 2 Weeks)
1. **UI Integration** - Connect Streamlit to database
2. **Session Tracking** - Add progress monitoring
3. **Basic Analytics** - Simple aggregations and trends

### Long-term (Future)
1. **Advanced Analytics** - Complex statistics and dashboards
2. **Performance Optimization** - Caching and query optimization

## Technical Considerations

### Database Schema Evolution
- **Current:** Single `analyzed_issues` table
- **Future:** Add `analysis_sessions` table for UI progress
- **Migration:** Schema changes handled via SQL scripts

### Repository Pattern Benefits
- **Testability:** Easy mocking for unit tests
- **Flexibility:** Swap storage backends without code changes
- **Maintainability:** Clear separation of concerns

### Error Handling Strategy
- **Concurrent Access:** SQLite locking and transaction handling

### Backward Compatibility
- **CLI Options:** Maintain existing JSON output option
- **API Stability:** Keep existing interfaces functional
- **Migration Path:** Smooth transition from file-based to DB storage

## Success Criteria

### Functional Requirements
- [ ] Analysis results persist to SQLite database
- [ ] Re-analysis overwrites previous results
- [ ] CLI supports both JSON and database output
- [ ] Streamlit UI can display saved results
- [ ] Basic querying and reporting from database

### Non-Functional Requirements
- [ ] Storage operations don't impact analysis performance
- [ ] Database queries complete within reasonable time
- [ ] Backward compatibility maintained
- [ ] Test coverage > 90% for storage layer

## Testing Strategy

### Unit Testing
- Repository interface implementations
- Service layer with mocked storage

### Integration Testing
- End-to-end analysis with database storage
- UI interaction with persistent data
- Cross-session data consistency

---

**Development Status:** Ready for Phase 1.5 Implementation
- ✅ Architecture and data model finalized
- ✅ Repository pattern implemented
- 🔄 Ready to integrate storage into analysis workflow
