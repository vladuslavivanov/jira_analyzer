# Project Sync Plan: current code ↔ design spec

## Purpose
This plan documents the work needed to align the current `jira_analyzer` implementation with the `docs/design_spec.md` architecture and functional requirements.

## High-level goals
- align public interfaces with the design spec
- ensure modular separation of responsibilities
- add missing repository and service behaviors
- verify persistence and report generation match design expectations
- preserve existing CLI and Streamlit usage while improving architecture

## Gap analysis
The current project contains many intended components, but several design spec expectations are not fully represented:

- `AnalysisService` exists, but the design spec interface is not exposed as named methods such as `analyze_task`, `analyze_jql`, `analyze_dataset`, `generate_report`.
- The repository abstraction is present, but the domain model and interfaces are minimal.
- The current Jira integration is focused on low-level REST client usage; there is no unified task repository or adapter layer.
- Persistence is implemented for results storage, but the SQLite schema is narrow and does not model task metadata or report entries.
- The project lacks a clear orchestration layer that coordinates Jira retrieval, analysis, persistence, and reporting in one service.

## Sync tasks

1. [x] Create formal sync plan document (`docs/sync_plan.md`).
2. [x] Add or improve `AnalysisService` public interface to match design spec methods.
3. [x] Add task retrieval abstraction for Jira issues and local datasets.
4. [ ] Review and extend SQLite repository schema to better match analysis results and report state.
5. [ ] Add or improve `AnalysisResultRepository` behavior and persistence tests.
6. [ ] Ensure `LLMClient` and prompt builder match async/concurrency design expectations.
7. [ ] Verify CLI and Streamlit entry points can use the new service and repository abstractions.
8. [x] Add or update tests for the new service interface and workflow.

## Implementation notes
- Keep changes incremental and test-driven.
- Avoid breaking existing CLI/Streamlit behavior if possible.
- Use the design spec as the canonical source for component names and responsibilities.

## Tracking
- Completed items will be updated here as work progresses.
