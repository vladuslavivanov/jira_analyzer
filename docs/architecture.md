# Architecture Description

# 1. Architectural Overview

The system is a modular AI-driven Jira task analysis platform designed for:

* automated issue inspection,
* multi-criteria AI evaluation,
* local/offline experimentation,
* simplified deployment.

The architecture follows a layered component-oriented approach with:

* presentation layer,
* orchestration layer,
* AI analysis layer,
* integration layer,
* persistence layer.

The implementation intentionally simplifies several production concerns due to its research-oriented nature.

---

# 2. Architectural Principles

## 2.1 Separation of Responsibilities

Responsibilities are distributed as follows:

| Layer            | Responsibility          |
| ---------------- | ----------------------- |
| Web UI           | User interaction        |
| Analysis Service | Workflow orchestration  |
| Analyzer         | AI analysis logic       |
| Adapters/Clients | External communication  |
| Repositories     | Persistence abstraction |

---

## 2.2 Simplified Monolithic Design

The system is intentionally implemented as a lightweight modular monolith:

* single backend process,
* local SQLite storage,
* embedded queue handling,
* optional mock infrastructure.

This reduces operational complexity while preserving architectural clarity.

---

# 3. Component Responsibilities

# 3.1 Web UI (Streamlit)

## Responsibilities

* collect user input,
* display reports,
* configure task tracker access,
* trigger analysis requests.

The UI does NOT directly access repositories or databases.

---

# 3.2 Streamlit Web Service

## Responsibilities

Acts as:

* HTTP/API controller,
* bridge between UI and backend services.

Responsibilities:

* validate requests,
* invoke analysis workflows,
* request final results from Analysis Service.

---

# 3.3 Analysis Service

## Core Orchestration Layer

Owns:

* analysis workflow lifecycle,
* task batching,
* pending/completed state management,
* aggregation of analysis results,
* coordination between repositories and Analyzer.

This is the primary orchestrator of the system.

---

# 3.4 Analyzer

## AI Analysis Engine

Owns:

* prompt preparation,
* criteria decomposition,
* semantic analysis execution,
* merging partial LLM outputs.

The Analyzer does NOT own:

* workflow orchestration,
* persistence,
* concurrency management.

---

# 3.5 LLM Client

## Responsibilities

Encapsulates all LLM-provider communication.

Owns:

* asynchronous request queue,
* rate limiting,
* retries,
* timeout handling,
* provider communication.

This simplifies concurrency management by centralizing it in one component.

---

# 3.6 Tasks Repository

## Responsibilities

Provides unified access to tasks regardless of source.

Supports:

* Jira API retrieval,
* local dataset retrieval.

The repository abstracts task acquisition from the orchestration layer.

---

# 3.7 Task Tracker Adapter

## Responsibilities

Transforms external task-tracker data into normalized internal domain objects.

This isolates:

* Jira-specific schemas,
* transport details,
* external field mappings.

---

# 3.8 Jira Client

## Responsibilities

Low-level communication with:

* real Jira REST API,
* mock Jira service.

Handles:

* HTTP requests,
* serialization,
* response parsing.

---

# 3.9 Fake Tasks Storage

## Responsibilities

Stores mock Jira tasks in local storage.

This replaces the earlier raw "JSON Dataset" abstraction.

The storage format may internally still be JSON files, but architecturally it is treated as a storage subsystem rather than direct file access.

---

# 3.10 Mock Jira Service

## Responsibilities

Provides a lightweight Jira-compatible REST API for:

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
