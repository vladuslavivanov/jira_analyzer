# Software Design Specification

## AI-Driven Jira Task Quality Audit System

---

# 1. Introduction

## 1.1 Purpose

This document describes the complete software design specification (SDS) for an AI-driven Jira task quality audit system.

The system performs automated semantic analysis of Jira tasks using Large Language Models (LLMs) and generates analytical reports for project managers, team leads, and project offices.

The specification is optimized for:

* AI-agent-driven development,
* incremental implementation,
* modular autonomous coding,
* code generation by LLM agents,
* test-driven implementation.

---

# 1.2 Scope

The product is an MVP-class internal web application implemented in Python.

Core capabilities:

* retrieving tasks from Jira,
* importing local datasets,
* performing LLM-based semantic analysis,
* storing analysis results,
* generating aggregated reports.

The system is designed primarily for:

* internal corporate environments,
* low operational complexity,
* research and experimentation.

---

# 1.3 Goals

## Functional Goals

* automated task quality analysis,
* scalable batch processing,
* configurable evaluation criteria,
* persistent analysis history,
* exportable reports.

## Technical Goals

* modular architecture,
* replaceable AI providers,
* maintainable codebase,
* AI-agent-friendly decomposition,
* low deployment complexity.

---

# 1.4 Target Audience

This document is intended for:

* developers,
* AI coding agents,
* software architects,
* research supervisors,
* DevOps engineers,
* QA engineers.

---

# 1.5 Definitions

| Term       | Description                      |
| ---------- | -------------------------------- |
| Jira       | Task tracking system             |
| LLM        | Large Language Model             |
| DoD        | Definition of Done               |
| JQL        | Jira Query Language              |
| Analyzer   | AI analysis engine               |
| Repository | Persistence abstraction          |
| Adapter    | External integration abstraction |
| MVP        | Minimum Viable Product           |

---

# 2. System Overview

# 2.1 Business Context

Poorly described tasks reduce development efficiency and increase coordination costs.

Manual auditing of large Jira backlogs is impractical.

The system automates:

* task quality inspection,
* semantic auditing,
* project reporting.

---

# 2.2 High-Level Architecture

The system follows a layered modular monolithic architecture.

## Main Layers

| Layer        | Responsibility         |
| ------------ | ---------------------- |
| Presentation | UI and interaction     |
| Application  | Workflow orchestration |
| AI Domain    | Semantic analysis      |
| Integration  | External systems       |
| Persistence  | Data storage           |

---

# 2.3 Architectural Principles

## Separation of Concerns

Each component owns a single primary responsibility.

---

## Replaceable Infrastructure

External systems are abstracted through:

* clients,
* adapters,
* repositories.

---

## AI-Agent-Oriented Modularity

The system is decomposed into:

* independently implementable modules,
* deterministic interfaces,
* isolated responsibilities.

This improves:

* autonomous code generation,
* automated testing,
* iterative implementation.

---

# 3. System Architecture

# 3.1 Container Architecture

## Main Containers

| Container           | Technology            |
| ------------------- | --------------------- |
| Web UI              | Streamlit             |
| Analysis Backend    | Python                |
| Persistence Storage | SQLite                |
| Jira Integration    | REST API              |
| LLM Provider        | OpenAI-compatible API |

---

# 3.2 Component Architecture

# Presentation Layer

## Streamlit Web UI

Responsibilities:

* collect user input,
* display reports,
* configure integrations,
* upload datasets.

---

## Streamlit Web Service

Responsibilities:

* request validation,
* controller logic,
* backend orchestration entry point.

---

# Application Layer

## Analysis Service

Primary orchestration component.

Responsibilities:

* workflow coordination,
* task batching,
* lifecycle management,
* aggregation,
* repository coordination.

---

# AI Domain Layer

## Analyzer

Responsibilities:

* prompt preparation,
* semantic decomposition,
* criteria evaluation,
* result merging.

The Analyzer does NOT:

* store data,
* manage workflows,
* access external storage directly.

---

## LLM Client

Responsibilities:

* async request queue,
* retries,
* rate limiting,
* timeout handling,
* LLM communication.

---

# Integration Layer

## Tasks Repository

Unified interface for task acquisition.

Supports:

* Jira retrieval,
* local datasets.

---

## Task Tracker Adapter

Normalizes external tracker schemas.

---

## Jira Client

Low-level Jira REST communication.

---

## Mock Jira Service

Local development/testing service.

---

## Fake Tasks Storage

Local mock task storage.

May internally use:

* JSON files,
* static datasets.

---

# Persistence Layer

## Analysis Result Repository

Stores:

* analysis results,
* task analysis state.

---

## SQLite Storage

Persistent single-file database.

Stores:

* task metadata,
* analysis results,
* states,
* reports.

---

# 4. Logical Data Model

# 4.1 Core Entities

## JiraTask

| Field       | Type     |
| ----------- | -------- |
| task_id     | string   |
| title       | string   |
| description | text     |
| status      | string   |
| assignee    | string   |
| created_at  | datetime |
| updated_at  | datetime |

---

## AnalysisCriteria

| Field        | Type   |
| ------------ | ------ |
| criteria_id  | string |
| name         | string |
| description  | text   |
| scoring_type | enum   |

---

## AnalysisResult

| Field           | Type     |
| --------------- | -------- |
| task_id         | string   |
| analysis_state  | enum     |
| total_score     | float    |
| summary         | text     |
| recommendations | text     |
| raw_response    | text     |
| analyzed_at     | datetime |

---

## AnalysisReport

| Field              | Type     |
| ------------------ | -------- |
| report_id          | string   |
| generated_at       | datetime |
| report_format      | enum     |
| aggregated_metrics | json     |

---

# 4.2 Analysis State Machine

```text
PENDING
  -> PROCESSING
      -> COMPLETED
      -> FAILED
```

---

# 5. Functional Design

# 5.1 User Scenarios

# Scenario 1 — Single Task Audit

Flow:

1. User enters Jira task ID.
2. System retrieves task.
3. Analyzer evaluates task.
4. Results displayed in UI.

---

# Scenario 2 — Group Audit via JQL

Flow:

1. User submits JQL query.
2. Tasks retrieved from Jira.
3. Existing analysis states checked.
4. Missing tasks analyzed asynchronously.
5. Aggregated report generated.

---

# Scenario 3 — Local Dataset Analysis

Flow:

1. User uploads dataset.
2. Tasks loaded from local storage.
3. Analysis executed asynchronously.
4. Results persisted.
5. Export generated.

---

# 5.2 Functional Requirements Mapping

| Requirement        | Component            |
| ------------------ | -------------------- |
| Jira integration   | Jira Client          |
| Task normalization | Task Tracker Adapter |
| AI analysis        | Analyzer             |
| Async processing   | LLM Client           |
| Persistence        | Result Repository    |
| Report generation  | Analysis Service     |
| UI interaction     | Streamlit UI         |

---

# 6. Detailed Component Design

# 6.1 Analysis Service

## Responsibilities

* orchestrate workflows,
* manage analysis lifecycle,
* coordinate repositories,
* aggregate reports.

---

## Public Interface

```python
class AnalysisService:
    def analyze_task(task_id: str) -> AnalysisResult
    def analyze_jql(jql: str) -> Report
    def analyze_dataset(path: str) -> Report
    def generate_report(filters: dict) -> Report
```

---

# 6.2 Analyzer

## Responsibilities

* decompose prompts,
* execute criteria analysis,
* combine responses.

---

## Public Interface

```python
class Analyzer:
    def analyze(task: JiraTask,
                criteria: list[AnalysisCriteria]) -> AnalysisResult
```

---

# 6.3 LLM Client

## Responsibilities

* queue management,
* retries,
* async execution.

---

## Public Interface

```python
class LLMClient:
    async def request(prompt: str) -> str
```

---

# 6.4 Tasks Repository

## Responsibilities

* retrieve tasks,
* abstract data sources.

---

## Public Interface

```python
class TasksRepository:
    def get_task(task_id: str) -> JiraTask
    def search_tasks(jql: str) -> list[JiraTask]
    def load_dataset(path: str) -> list[JiraTask]
```

---

# 6.5 Result Repository

## Responsibilities

* store results,
* manage states.

---

## Public Interface

```python
class AnalysisResultRepository:
    def get_state(task_id: str)
    def save_pending(task_id: str)
    def save_result(result: AnalysisResult)
    def get_results(filters: dict)
```

---

# 7. Prompt Engineering Design

# 7.1 Prompt Architecture

Prompts are externalized into:

* Markdown files,
* JSON configuration.

---

# 7.2 Prompt Layers

| Layer           | Purpose             |
| --------------- | ------------------- |
| System Prompt   | Global AI behavior  |
| Analysis Prompt | Audit task          |
| Criteria Prompt | Specific evaluation |

---

# 7.3 Criteria Evaluation

Supported scoring:

* binary,
* 5-point,
* percentage.

---

# 8. Concurrency Design

# 8.1 Async Model

Concurrency is centralized inside `LLMClient`.

Responsibilities:

* request queue,
* worker scheduling,
* retry handling.

---

# 8.2 Processing Model

```text
Task Batch
 -> Analysis Service
     -> Analyzer
         -> LLM Queue
             -> LLM Workers
```

Full sequence diagram of processing is presented in [./sequence_diagram.md](./sequence_diagram.md).

---

# 9. Persistence Design

# 9.1 SQLite Schema

## tasks

| Column      | Type     |
| ----------- | -------- |
| task_id     | TEXT     |
| title       | TEXT     |
| description | TEXT     |
| created_at  | DATETIME |

* posibly other metadata attributes

---

## analysis_results

| Column     | Type     |
| ---------- | -------- |
| task_id    | TEXT     |
| state      | TEXT     |
| score      | REAL     |
| report     | TEXT     |
| updated_at | DATETIME |

---

## reports

| Column         | Type     |
| -------------- | -------- |
| report_id      | TEXT     |
| created_at     | DATETIME |
| report_content | TEXT     |

---

# 9.2 Persistence Strategy

The database acts as:

* analysis cache,
* historical storage,
* workflow state storage.

This intentionally simplifies architecture.

---

# 10. Report Generation

# 10.1 Supported Formats

| Format   | Status |
| -------- | ------ |
| JSON     | Must   |
| Markdown | Should |

---

# 10.2 Aggregation

Performed by `AnalysisService`.

Includes:

* score averages,
* problematic tasks,
* criteria statistics,
* zombie-task detection.

---

# 11. Error Handling Design

# 11.1 Jira Errors

Handled cases:

* invalid credentials,
* invalid JQL,
* unavailable API.

---

# 11.2 Dataset Errors

Handled cases:

* corrupted dataset,
* invalid schema,
* unsupported format.

---

# 11.3 LLM Errors

Handled cases:

* timeout,
* rate limit,
* malformed response,
* retry exhaustion.

---

# 12. Non-Functional Design

# 12.1 Performance

Target:

* asynchronous processing for task batches,
* reduced waiting time for >10 tasks.

---

# 12.2 Scalability

Supports:

* tens of thousands of tasks,
* low concurrent user count.

---

# 12.3 Security

Secrets stored in:

* environment variables,
* protected config files.

---

# 12.4 Deployment Constraints

Requirements:

* internal deployment only,
* no external SaaS dependencies except LLM API.

---

# 13. Deployment Architecture

# 13.1 MVP Deployment

```text
Single Host
 ├── Streamlit App
 ├── Python Backend
 ├── SQLite DB
 └── Local Config Files
```

---

# 13.2 External Dependencies

| Dependency       | Purpose           |
| ---------------- | ----------------- |
| Jira API         | Task retrieval    |
| LLM Provider API | Semantic analysis |

---

# 14. AI-Agent-Driven Development Optimization

# 14.1 Development Principles

The project is intentionally optimized for:

* AI-assisted coding,
* autonomous implementation,
* incremental generation.

---

# 14.2 Module Isolation

Each module should:

* expose deterministic interfaces,
* avoid hidden side effects,
* minimize shared mutable state.

---

# 14.3 Recommended Repository Structure

```text
project/
├── ui/
├── application/
├── domain/
├── infrastructure/
├── repositories/
├── prompts/
├── datasets/
├── reports/
├── tests/
└── docs/
```

---

# 14.4 AI-Agent-Friendly Constraints

## Prefer

* pure functions,
* typed DTOs,
* explicit interfaces,
* isolated modules,
* declarative configs.

---

## Avoid

* global mutable state,
* hidden dependencies,
* tightly coupled services,
* implicit runtime magic.

---

# 14.5 Recommended Implementation Order

## Phase 1

* DTOs
* repositories
* SQLite schema

## Phase 2

* Jira integration
* dataset loading

## Phase 3

* LLM client
* Analyzer

## Phase 4

* Analysis orchestration

## Phase 5

* Streamlit UI

## Phase 6

* reporting/export

---

# 15. Testing Strategy

# 15.1 Unit Testing

Coverage targets:

* repositories,
* adapters,
* Analyzer logic,
* prompt builders.

---

# 15.2 Integration Testing

Coverage:

* Jira API integration,
* SQLite persistence,
* LLM request pipeline.

---

# 15.3 Dataset-Based Regression Testing

Static datasets should be used for:

* deterministic testing,
* prompt regression validation,
* evaluation consistency.

---

# 17. Conclusion

The system architecture provides:

* modularity,
* extensibility,
* low operational complexity,
* AI-agent-oriented implementation structure.

The design intentionally balances:

* engineering simplicity,
* architectural clarity,
* future extensibility,
* research-oriented flexibility.
