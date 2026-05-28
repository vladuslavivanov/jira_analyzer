# Architecture

Jira AI Analyzer is built as a lightweight modular monolith for AI-driven Jira issue evaluation. It combines a browser UI, AI analysis engine, Jira integration, and local persistence.

## Layers and responsibilities

- **UI layer**: Streamlit browser app with prompt editor, issue source selector, workflow settings, results viewer, and export controls.
- **Orchestration layer**: `AnalysisService` manages issue loading, analysis execution, batching, and persistence.
- **AI layer**: `Analyzer` builds prompts, splits analysis by criteria if needed, and merges structured LLM responses.
- **Integration layer**: Jira adapters normalize real Jira or mock Jira issues into internal issue objects.
- **Persistence layer**: SQLite repository stores analysis results and task state.

## Key components

- **Streamlit UI**: collects issue source settings (sample JSON, Jira issue key, JQL), Jira credentials, prompt configuration, and worker count, then starts analysis without direct database access.
- **AnalysisService**: the central workflow owner that requests tasks, invokes the analyzer, and persists results.
- **Analyzer**: prepares prompt content from configurable criteria and sends requests to an LLM provider.
- **LLM providers**: supports `fake` mode for local testing and `openai-compatible` mode for production-style LLM calls.
- **Jira client / task repository**: fetches and normalizes issues from Jira or local data sources.
- **Mock Jira service**: optional local Jira-compatible API for offline development.

## Behavior summary

1. User submits a request from the Streamlit UI.
2. AnalysisService loads issues via the task repository.
3. Analyzer converts issues into prompt requests and sends them to the LLM provider.
4. Results are collected, merged, and saved by the SQLite repository.
5. The UI reads final results and presents JSON/Markdown output.


* local development,
* offline testing,
* deterministic experiments.

---

# 3.11 Analysis Result Repository

## Responsibilities

Stores:

* analysis results,
* task processing states.

For simplicity, task states are stored together with results in SQLite.

This is fully acceptable for:

* local deployments,
* research systems,
* lightweight persistence requirements.

Example states:

* pending,
* processing,
* completed,
* failed.

---

# 3.12 Analysis Result Storage (SQLite)

## Responsibilities

Persistent single-file storage containing:

* analysed tasks,
* analysis state,
* AI-generated reports.

Benefits:

* portability,
* simple backups,
* reproducibility,
* no external DB dependency.

---

# 4. Corrected High-Level Flow

```text
User
 → Web UI
   → Streamlit Web Service
     → Analysis Service
         → Tasks Repository
             → Task Tracker Adapter
                 → Jira Client
                     → Jira / Mock Jira
```

Then:

```text
Analysis Service
 → Analyzer
     → LLM Client
         → LLM Provider
```

Finally:

```text
Analysis Service
 → Analysis Result Repository
     → SQLite Storage
```

And:

```text
Web UI
 ← Streamlit Web Service
 ← Analysis Service
```

---

# Sequence Diagram

Full sequence diagram of processing is presented in [./sequence_diagram.md](./sequence_diagram.md).

---

# Why This Version Is Architecturally Consistent

## Fixed Issues

| Previous Problem                        | Corrected                                 |
| --------------------------------------- | ----------------------------------------- |
| UI accessed repository directly         | UI only talks to Analysis Service         |
| Repository bypassed integration layer   | Access paths unified                      |
| Analyzer orchestrated workflow          | Analysis Service owns orchestration       |
| UI aggregated results                   | Backend aggregates                        |
| JSON file treated as raw infrastructure | Fake Tasks Storage abstraction introduced |
| Database Client inconsistency           | Removed entirely                          |
| Mock Jira implied production dependency | Now clearly integration option            |

---

# Simplifications Are Reasonable

For a student/research project, these decisions are technically justified:

| Simplification            | Reasonable? | Why                            |
| ------------------------- | ----------- | ------------------------------ |
| SQLite only               | Yes         | Minimal operational complexity |
| Task states in same table | Yes         | Simple lifecycle persistence   |
| LLM queue inside client   | Yes         | Centralized async handling     |
| No observability          | Yes         | Research scope                 |
| No auth layer             | Yes         | UI-managed credentials         |
| Optional caching omitted  | Yes         | Non-essential optimization     |

---

# Final Architectural Assessment

The corrected version is now internally coherent and follows consistent architectural boundaries while remaining intentionally lightweight.

It is now:

* clean enough for thesis/research documentation,
* realistic enough to resemble production architecture,
* simple enough to implement fully,
* extensible for future evolution.
