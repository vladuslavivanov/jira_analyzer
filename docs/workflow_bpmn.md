# BPMN Diagram Description — Jira AI Analyzer Workflow

## Participants (Pools / Lanes)

### Pool: User

**Lane:** User

### Pool: Jira AI Analyzer System

**Lanes:**

* Streamlit UI
* Analysis Service
* Analyzer
* Task Repository
* Result Repository

### Pool: External Systems

**Lanes:**

* Jira / Mock Jira
* LLM Provider
* SQLite Storage

---

## Main Process Flow

### 1. Start Analysis Request

**Start Event:**
**"User Requests Issue Analysis"**

Flow:

1. **User Task:**
   **Configure and start analysis**

2. **Service Task (Streamlit UI):**
   **Submit analysis request**

3. **Service Task (Analysis Service):**
   **Initialize analysis workflow**

---

### 2. Select Issue Source

**Exclusive Gateway (XOR):**
**"Issue source type?"**

Conditions:

* Jira source
* Local JSON source

---

### Branch A — Jira Source

1. **Service Task (Task Repository):**
   **Load tasks by issue key or JQL**

2. **Service Task (Task Tracker Adapter):**
   **Fetch issue data**

3. **Service Task (Jira Client):**
   **Call Jira REST API**

4. **Exclusive Gateway:**
   **"Use Mock Jira?"**

#### Mock Jira path

5. **Service Task (Mock Jira):**
   **Query mock Jira service**

6. **Service Task (Fake Task Storage):**
   **Read mock issue JSON**

7. **Service Task (Task Repository):**
   **Normalize Jira issue format**

#### Real Jira path

5. **Service Task (Task Repository):**
   **Normalize Jira issue format**

---

### Branch B — Local JSON Source

1. **Service Task (Task Repository):**
   **Load local issue dataset**

2. **Service Task (Fake Task Storage):**
   **Read sample JSON**

3. **Service Task (Task Repository):**
   **Normalize issue format**

---

### Merge Point

**Exclusive Gateway (Merge):**
**"Issues loaded"**

Result:

* Normalized issue collection available for analysis

---

### 3. Restore Existing Analysis State

1. **Service Task (Result Repository):**
   **Query existing analysis results**

2. **Service Task (SQLite Storage):**
   **Read stored analysis state**

3. **Service Task (Result Repository):**
   **Mark pending tasks**

4. **Service Task (SQLite Storage):**
   **Persist pending state**

---

### 4. Analyze Pending Tasks

**Multi-Instance Subprocess (Loop):**
**"Analyze Pending Task"**

Loop cardinality:

* One instance per pending issue

Subprocess steps:

#### 4.1 Prepare Analysis

1. **Service Task (Analyzer):**
   **Prepare prompts**

2. **Service Task (Analyzer):**
   **Split analysis criteria (optional)**

---

#### 4.2 Execute LLM Analysis

**Parallel Gateway (AND Split):**
**"Execute criterion analysis"**

Parallel branches:

* One branch per criterion or LLM request

Per branch:

1. **Service Task (LLM Client):**
   **Submit LLM request**

   Boundary events:

   * Timeout
   * Retry
   * Error handling

2. **Service Task (LLM Provider):**
   **Execute inference**

3. **Receive response**

---

**Parallel Gateway (AND Join):**
**"All LLM responses complete"**

4. **Service Task (Analyzer):**
   **Merge partial analysis results**

---

#### 4.3 Persist Task Result

1. **Service Task (Result Repository):**
   **Save analysis result**

2. **Service Task (SQLite Storage):**
   **Update stored state**

3. **Boundary Error Event:**
   **Analysis failure**

Failure path:

* **Service Task:** Save failed result
* **Service Task:** Persist error details
* Continue to next issue

---

### 5. Finalize Analysis

**End-of-loop condition:**
**"All pending tasks processed"**

1. **Service Task (Analysis Service):**
   **Generate final report**

2. **Service Task (Streamlit UI):**
   **Return analysis results**

3. **User Task:**
   **Review analysis output**

---

## BPMN Gateway Mapping

| Sequence Construct | BPMN Element                                |
| ------------------ | ------------------------------------------- |
| `alt`              | Exclusive Gateway (XOR)                     |
| `loop`             | Multi-instance subprocess                   |
| `par`              | Parallel Gateway (AND)                      |
| retries/timeouts   | Boundary Timer/Error Events                 |
| async LLM queue    | Service Task with asynchronous continuation |

---

## Recommended BPMN Structure

Use **three pools**:

1. **User**
2. **Jira AI Analyzer**
3. **External Systems**

Inside the **Jira AI Analyzer** pool, use lanes for:

* UI
* Analysis Service
* Analyzer
* Task Repository
* Result Repository

This keeps orchestration responsibilities visible while avoiding an overly message-heavy BPMN model.
