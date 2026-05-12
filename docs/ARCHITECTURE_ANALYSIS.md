# Jira AI Analyzer - Architecture Analysis Report

**Date:** May 12, 2026  
**Project:** ipkn-jira-ai-linter/jira_analyzer  
**Diagram Reference:** [C4 Architecture Diagram](docs/resources/c4-arch.drawio)

---

## 1. Complete Description of Proposed Architecture

### System Overview
The proposed architecture follows a **C4 model** implementing an AI-driven Jira issue quality analysis system. It's designed as a containerized microservice application with clear separation of concerns, external integrations, and scalable analysis capabilities.

### Architecture Layers

#### External Systems (Outside Container)
1. **Web UI** - Streamlit-based interactive browser interface
   - Purpose: User interaction, issue configuration, prompt editing
   - Capabilities: Single issue lookup, JQL queries, report preview, result download
   
2. **LLM Provider** - DeepSeek LLM service (Software system)
   - Purpose: External AI language model for quality analysis
   - Protocol: REST API with JSON request/response
   
3. **Mock Jira Service** - Testing double for Jira
   - Purpose: Local testing and development without external Jira dependency
   - Capabilities: Issue lookup by key, JQL query support

#### AI Analysis Agent Container (Main System)

**Core Application Components:**

1. **LLM Client** (Component: Python, greenlet.protocol)
   - Responsibility: Communication gateway with DeepSeek LLM
   - Features:
     - Manages API calls and authentication
     - Handles JSON response parsing
     - Error handling and retry logic
     - Temperature and format configuration

2. **Controller** (Component: Python, HTTP REST API)
   - Responsibility: Request routing and orchestration
   - Functions:
     - Routes incoming requests to appropriate services
     - Coordinates workflow between components
     - Implements business logic flow

3. **Analyzer** (Component: Python, Callable)
   - Responsibility: Core analysis engine
   - Functions:
     - Implements parallel analysis logic
     - Issue processing and data transformation
     - Worker thread management
     - Quality scoring coordination

4. **Analysis Service** (Component: Python, Service)
   - Responsibility: Business logic layer
   - Functions:
     - Orchestrates analysis workflows
     - Manages prompt templates and configurations
     - Coordinates between analyzer and repositories

5. **Task Tracker Adapter** (Component: Python, Adapter)
   - Responsibility: Integration bridge to task tracking systems
   - Functions:
     - Translates between Jira and internal data models
     - Provides abstraction over Jira specifics
     - Supports multiple task tracker backends

6. **Jira Client** (Component: Python, py-jira)
   - Responsibility: Direct Jira REST API communication
   - Functions:
     - Issue fetching and searching
     - JQL query execution
     - User authentication management

7. **Task Repository** (Component: Python, Repository Pattern)
   - Responsibility: Task data persistence abstraction
   - Functions:
     - Stores and retrieves Jira issue data
     - Query interface implementation

8. **Database Client** (Component: Python, DB Connection)
   - Responsibility: Database connectivity layer
   - Functions:
     - Connection pooling
     - Transaction management
     - SQL/NoSQL abstraction

9. **Analysis Result Repository** (Component: Python, Repository Pattern)
   - Responsibility: Analysis output persistence abstraction
   - Functions:
     - Stores analysis results
     - Query interface for historical data
     - Result archival management

10. **Analysis Result Storage** (Component: Cache SQL-like)
    - Responsibility: Persistent storage of analysis results
    - Functions:
      - Permanent result archival
      - Historical data retrieval
      - Report generation source

### Data Flow Architecture

**Issue Analysis Workflow:**
```
Web UI / CLI → Controller → Analyzer Service
   ↓
   ├─→ Task Tracker Adapter ─→ Jira Client ─→ Real Jira or Mock Jira
   │
   ├─→ LLM Client ─→ DeepSeek LLM Provider
   │
   └─→ Analysis Service
       ├─→ Analysis Result Repository ─→ Analysis Result Storage
       └─→ Output Handler
```

**Result Management Workflow:**
```
Analysis Results
   ↓
Analysis Result Repository
   ├─→ Cache Layer (hot data)
   └─→ Analysis Result Storage (cold data)
```

---

## 2. Analysis of Proposed Architecture

### 2.1 Strengths of the Design

#### Separation of Concerns ✓
- **Controller**: Request routing and orchestration
- **Analyzer**: Core algorithm implementation
- **Services**: Business logic (Analysis Service)
- **Adapters**: Integration points (Task Tracker Adapter)
- **Repositories**: Data persistence (Repository Pattern)
- **Clients**: External communication (LLM Client, Jira Client)

**Benefit:** Changes to one component have minimal impact on others.

#### Scalability Considerations ✓
- **Parallel Processing**: Engine supports multi-worker analysis
- **Repository Pattern**: Easy to swap storage backends
- **Adapter Pattern**: Supports multiple task tracking systems
- **Database Client**: Enables connection pooling and optimization

**Benefit:** System can grow from single-machine to distributed architecture.

#### Testing and Mockability ✓
- **Mock Jira Service**: Integration testing without real Jira
- **Adapter Pattern**: Easy to create test doubles
- **Repository Pattern**: In-memory or mock repositories for testing
- **Dependency Inversion**: Depends on abstractions, not concrete implementations

**Benefit:** High test coverage possible without external dependencies.

#### External Integration Points ✓
- **LLM Provider**: Modular AI backend (easily swap DeepSeek for OpenAI, Claude, etc.)
- **Task Tracker**: Adapter pattern enables Jira, Azure DevOps, GitHub Issues integration
- **Result Storage**: Flexible persistence (SQL, NoSQL, cloud storage)

**Benefit:** Vendor lock-in minimized, flexibility maximized.

#### User Interface Flexibility ✓
- **Web UI**: Interactive analysis and configuration
- **CLI**: Automation and scripting
- **Dual Entry Points**: Accommodate different user workflows

**Benefit:** Multiple user personas supported.

### 2.2 Potential Concerns and Gaps

#### 1. Storage Architecture Incomplete
**Observation:** Two storage abstractions (Task Repository + Analysis Result Repository)
- **Gap:** Unclear relationship between cache and persistent storage
- **Concern:** Potential data consistency issues
- **Recommendation:** Define cache invalidation strategy and update patterns

#### 2. Controller Responsibility Ambiguity
**Observation:** Controller described as "REST API" but unclear if HTTP-only or higher level
- **Gap:** Unclear how CLI integrates with Controller
- **Concern:** Different request routing logic for Web vs CLI
- **Recommendation:** Define abstract Request/Response contract for both UI types

#### 3. Analysis Service Purpose
**Observation:** Both Analyzer and Analysis Service appear to handle business logic
- **Gap:** Overlapping responsibilities
- **Concern:** Potential for feature creep and muddled layers
- **Recommendation:** Analyzer = algorithm, Service = orchestration and configuration

#### 4. LLM Client Abstraction
**Observation:** Direct DeepSeek integration without interface
- **Gap:** Provider-specific details leak into application
- **Concern:** Switching LLM providers requires code changes
- **Recommendation:** Define `ILLMProvider` interface for provider abstraction

#### 5. Database Client Scope
**Observation:** Generic "Database Client" shown but connection protocol unspecified
- **Gap:** Unclear what databases are supported
- **Concern:** May create performance bottlenecks if not designed for analytics
- **Recommendation:** Define DB schema for task repository and result storage

#### 6. Jira Client Resilience
**Observation:** No caching or retry mechanisms shown
- **Gap:** Network failures could cause cascading issues
- **Concern:** Poor user experience with flaky Jira servers
- **Recommendation:** Add circuit breaker, retry logic, and optional local caching

### 2.3 Architecture Trade-offs

| Aspect | Choice | Trade-off |
|--------|--------|-----------|
| **Parallel Analysis** | Multi-threaded workers | Simpler than distributed but limited scalability |
| **Repository Pattern** | Abstraction layer for all data | Extra code but flexible storage |
| **Adapter Pattern** | For task trackers | More abstraction but future-proof |
| **Monolithic Container** | Single deployable unit | Simpler deployment but less flexible scaling |
| **Dual UI (Web + CLI)** | Both provided | More code to maintain but better UX |

### 2.4 Quality Attributes

| Attribute | Assessment | Justification |
|-----------|------------|---------------|
| **Scalability** | ⭐⭐⭐⭐ | Repository pattern, adapter pattern, multi-threading ready |
| **Maintainability** | ⭐⭐⭐⭐ | Clear separation of concerns, well-defined interfaces |
| **Testability** | ⭐⭐⭐⭐⭐ | Mock services, repository pattern, dependency inversion |
| **Flexibility** | ⭐⭐⭐⭐ | LLM agnostic, task tracker agnostic, storage agnostic |
| **Performance** | ⭐⭐⭐ | Parallel workers, but monolithic may have bottlenecks |
| **Reliability** | ⭐⭐⭐ | No explicit error handling shown, needs resilience patterns |

---

## 3. Verification of Current Project Architecture (AS-IS)

### 3.1 Current Implementation Status

#### ✅ Implemented Components

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| **Web UI** | `src/jira_analyzer/app/streamlit.py` | ✅ Complete | Full Streamlit application |
| **CLI** | `src/jira_analyzer/app/cli.py` | ✅ Complete | Comprehensive argument parser |
| **Analyzer Engine** | `src/jira_analyzer/analyzer/engine.py` | ✅ Complete | Parallel workers implemented |
| **LLM Client** | `src/jira_analyzer/analyzer/core/llm/deepseek_client.py` | ✅ Complete | DeepSeek integration |
| **Prompt Builder** | `src/jira_analyzer/analyzer/core/llm/prompt_builder.py` | ✅ Complete | Template-based prompts |
| **Jira Client** | `src/jira_analyzer/tasktracker/jira/jira_client.py` | ✅ Complete | py-jira wrapper |
| **Jira Parser** | `src/jira_analyzer/tasktracker/jira/jira_parser.py` | ✅ Complete | JSON/Jira conversion |
| **Mock Jira** | `src/mock_jira/server.py` | ✅ Complete | REST mock server |
| **Output Handler** | `src/jira_analyzer/app/output_handler.py` | ✅ Complete | JSON/Markdown export |
| **Config** | `src/jira_analyzer/utils/config.py` | ✅ Complete | Environment-based config |

#### ❌ Missing/Incomplete Components

| Component | Proposed | Current | Gap |
|-----------|----------|---------|-----|
| **Controller** | ❌ Not explicitly defined | Integrated in CLI/Streamlit | Lack of request routing abstraction |
| **Analysis Service** | ⚠️ Formal service layer | Integrated in engine.py | Mixed concerns in engine |
| **Task Repository** | ⚠️ Repository abstraction | Direct file I/O | No persistence abstraction |
| **Database Client** | ❌ Database abstraction | None | No database integration |
| **Analysis Result Repository** | ❌ Result storage abstraction | Simple file output | No result archival |
| **Analysis Result Storage** | ❌ Persistent storage | JSON files | No structured database |

### 3.2 Architectural Differences (AS-IS vs TO-BE)

#### Current Architecture (AS-IS)

```
┌─── Web UI (Streamlit)
│
├─→ CLI (argparse)
│
└─→ Unified Entry Point
    │
    ├─→ Analyzer Engine
    │   ├─→ DeepSeek Client (Direct)
    │   └─→ LLM Prompts (Template)
    │
    ├─→ Jira Integration
    │   ├─→ Jira Client
    │   ├─→ Jira Parser
    │   └─→ Mock Jira Server
    │
    └─→ Output Handler
        └─→ File I/O (JSON/Markdown)
```

**Characteristics:**
- **Monolithic**: All logic in main package
- **Direct Integration**: No adapters or intermediaries
- **File-Based**: Output directly to files
- **Single Analyzer**: No formal service layer
- **Direct LLM Calls**: No abstraction over LLM provider

#### Proposed Architecture (TO-BE)

```
┌─── Web UI (Streamlit)
├─── CLI
│
└─→ Controller
    │
    ├─→ Analysis Service (Orchestrator)
    │   │
    │   ├─→ Analyzer (Algorithm)
    │   │   └─→ LLM Client ─→ DeepSeek
    │   │
    │   └─→ Task Tracker Adapter
    │       └─→ Jira Client ─→ Real/Mock Jira
    │
    ├─→ Analysis Result Repository
    │   └─→ Analysis Result Storage (Database)
    │
    └─→ Task Repository
        └─→ Database Client
```

**Characteristics:**
- **Layered**: Clear separation of concerns
- **Adapter Pattern**: Abstraction over external systems
- **Repository Pattern**: Abstraction over storage
- **Service Orchestration**: Formal service layer
- **Provider Agnostic**: LLM and storage pluggable

### 3.3 Mapping Current Code to Proposed Components

```python
# CURRENT → PROPOSED MAPPING

src/jira_analyzer/app/cli.py 
    → Controller (partial) + Web UI (partial)

src/jira_analyzer/app/streamlit.py
    → Web UI (complete)

src/jira_analyzer/analyzer/engine.py
    → Analyzer + Analysis Service (mixed)

src/jira_analyzer/analyzer/core/llm/deepseek_client.py
    → LLM Client (complete)

src/jira_analyzer/tasktracker/jira/jira_client.py
    → Jira Client (complete)

src/jira_analyzer/tasktracker/jira/jira_parser.py
    → Task Tracker Adapter (partial)

src/jira_analyzer/tasktracker/jira/issue_mapper.py
    → Task Tracker Adapter (partial)

src/jira_analyzer/app/output_handler.py
    → Analysis Result Repository (partial)

src/mock_jira/server.py
    → Mock Jira Service (complete)

# MISSING:
    → Analysis Result Storage (Database/Persistence)
    → Database Client (ORM/Query Layer)
    → Task Repository (Data abstraction)
    → Formal Controller (Request routing)
    → Analysis Service (Proper orchestration)
```

### 3.4 Key Structural Observations

**Positive:**
- ✅ Clean separation between CLI, Streamlit, and Analyzer
- ✅ Modular imports and package structure
- ✅ Mock Jira service for testing
- ✅ Configuration management via environment variables
- ✅ Output formatting abstraction (JSON/Markdown)

**Areas for Improvement:**
- ❌ `analyzer/engine.py` is doing too much (mixed Algorithm + Orchestration)
- ❌ No database layer or result persistence
- ❌ File I/O not abstracted (direct JSON output)
- ❌ No formal request/response model
- ❌ LLM client tightly coupled to DeepSeek

---

## 4. Specified Updates: AS-IS to TO-BE

### 4.1 Priority-Based Migration Plan

#### Phase 1: High Priority (Foundation)

**1. Extract Analysis Service Layer**
```
FILE: src/jira_analyzer/analyzer/service.py (NEW)

CHANGES:
- Extract orchestration logic from engine.py
- Create AnalysisService class
- Move configuration and workflow logic
- Keep pure analysis algorithm in engine.py

IMPACT: 
+ Cleaner separation of concerns
+ Easier to test
- Refactor existing code
```

**2. Create Analysis Result Repository**
```
FILE: src/jira_analyzer/storage/__init__.py (NEW)
FILE: src/jira_analyzer/storage/repository.py (NEW)
FILE: src/jira_analyzer/storage/memory_repository.py (NEW)
FILE: src/jira_analyzer/storage/file_repository.py (NEW)

CHANGES:
- Define IAnalysisRepository interface
- Create in-memory implementation
- Create file-based implementation
- Replace direct file I/O in output_handler.py

IMPACT:
+ Swappable storage backends
+ Better testability
- Additional abstraction layer
```

**3. Create LLM Provider Interface**
```
FILE: src/jira_analyzer/analyzer/core/llm/provider.py (NEW)

CHANGES:
- Define ILLMProvider interface
- Keep DeepSeek as concrete implementation
- Enable future provider implementations

IMPACT:
+ Provider-agnostic architecture
+ Easy to add OpenAI, Claude, etc.
- Light refactor of deepseek_client.py
```

#### Phase 2: Medium Priority (Abstraction)

**4. Create Task Repository Abstraction**
```
FILE: src/jira_analyzer/tasktracker/repository.py (NEW)

CHANGES:
- Define ITaskRepository interface
- Create implementation that wraps Jira client
- Support in-memory mock implementation

IMPACT:
+ Decouple from Jira specifics
+ Easier testing
- Additional service layer
```

**5. Formal Controller/Request Router**
```
FILE: src/jira_analyzer/app/controller.py (NEW)

CHANGES:
- Create unified request model
- Route Web UI and CLI requests to services
- Standardize response format

IMPACT:
+ Unified request/response model
+ DRY principle (no duplicate logic)
- Refactor CLI and Streamlit
```

**6. Database Client Abstraction**
```
FILE: src/jira_analyzer/storage/database.py (NEW)

CHANGES:
- Create IDatabase interface
- Support SQLite, PostgreSQL options
- Connection pooling and transactions

IMPACT:
+ Future database integration
+ Better performance
- Requires database schema design
```

#### Phase 3: Low Priority (Enhancement)

**7. Enhanced Caching Layer**
```
FILE: src/jira_analyzer/caching/cache.py (NEW)

CHANGES:
- Add Redis/in-memory cache option
- Cache LLM responses
- Cache Jira issue data

IMPACT:
+ Faster repeated analyses
+ Reduced API calls
- Cache invalidation complexity
```

**8. Error Handling & Resilience**
```
CHANGES:
- Add retry logic to Jira client
- Circuit breaker pattern
- Graceful degradation
- Better error reporting

IMPACT:
+ Better reliability
+ Better UX
- Additional complexity
```

### 4.2 Detailed File Changes

#### Change 1: Extract Analysis Service

```python
# BEFORE: src/jira_analyzer/analyzer/engine.py
# Single monolithic engine with mixed concerns

# AFTER: Split into two files

# src/jira_analyzer/analyzer/service.py (NEW)
class AnalysisService:
    """Orchestrates analysis workflow"""
    def __init__(self, prompt_config, worker_count):
        self.prompt_config = prompt_config
        self.worker_count = worker_count
    
    def analyze_issues(self, issues):
        """Coordinates analysis"""
        # Orchestration logic
        
# src/jira_analyzer/analyzer/engine.py (REFACTORED)
class AnalysisEngine:
    """Pure analysis algorithm"""
    @staticmethod
    def analyze_single_issue(issue, prompt_config):
        """Performs analysis on single issue"""
        # Algorithm only
```

**Files to Change:**
- [src/jira_analyzer/analyzer/engine.py](src/jira_analyzer/analyzer/engine.py) - REFACTOR
- [src/jira_analyzer/analyzer/service.py](src/jira_analyzer/analyzer/service.py) - CREATE

---

#### Change 2: Analysis Result Repository

```python
# BEFORE: src/jira_analyzer/app/output_handler.py
# Direct file I/O

# AFTER: New repository layer

# src/jira_analyzer/storage/repository.py (NEW)
from abc import ABC, abstractmethod

class IAnalysisRepository(ABC):
    @abstractmethod
    def save_results(self, results: List[Dict]) -> str:
        """Save analysis results, return result ID"""
    
    @abstractmethod
    def get_results(self, result_id: str) -> List[Dict]:
        """Retrieve saved results"""

class FileAnalysisRepository(IAnalysisRepository):
    """File-based implementation"""
    
class SQLAnalysisRepository(IAnalysisRepository):
    """Database-based implementation"""
```

**Files to Change:**
- [src/jira_analyzer/storage/__init__.py](src/jira_analyzer/storage/__init__.py) - CREATE
- [src/jira_analyzer/storage/repository.py](src/jira_analyzer/storage/repository.py) - CREATE
- [src/jira_analyzer/app/output_handler.py](src/jira_analyzer/app/output_handler.py) - REFACTOR

---

#### Change 3: LLM Provider Interface

```python
# BEFORE: src/jira_analyzer/analyzer/core/llm/deepseek_client.py
# Direct DeepSeek calls

# AFTER: Provider abstraction

# src/jira_analyzer/analyzer/core/llm/provider.py (NEW)
from abc import ABC, abstractmethod

class ILLMProvider(ABC):
    @abstractmethod
    def send_prompt(self, prompt: str, system_prompt: str) -> dict:
        """Send prompt and get response"""

# src/jira_analyzer/analyzer/core/llm/deepseek_client.py (REFACTOR)
class DeepSeekProvider(ILLMProvider):
    """DeepSeek implementation of LLM provider"""
```

**Files to Change:**
- [src/jira_analyzer/analyzer/core/llm/provider.py](src/jira_analyzer/analyzer/core/llm/provider.py) - CREATE
- [src/jira_analyzer/analyzer/core/llm/deepseek_client.py](src/jira_analyzer/analyzer/core/llm/deepseek_client.py) - REFACTOR

---

#### Change 4: Task Repository

```python
# src/jira_analyzer/tasktracker/repository.py (NEW)

from abc import ABC, abstractmethod

class ITaskRepository(ABC):
    @abstractmethod
    def fetch_issue(self, key: str) -> Dict:
        """Fetch single issue"""
    
    @abstractmethod
    def search_issues(self, query: str) -> List[Dict]:
        """Search issues by JQL or filter"""

class JiraTaskRepository(ITaskRepository):
    """Jira implementation"""
    def __init__(self, jira_client):
        self.client = jira_client

class MockTaskRepository(ITaskRepository):
    """Mock implementation for testing"""
```

**Files to Change:**
- [src/jira_analyzer/tasktracker/repository.py](src/jira_analyzer/tasktracker/repository.py) - CREATE
- [src/jira_analyzer/tasktracker/jira/jira_parser.py](src/jira_analyzer/tasktracker/jira/jira_parser.py) - REFACTOR

---

### 4.3 Implementation Roadmap with Estimated Effort

| Phase | Task | Files | Effort | Complexity |
|-------|------|-------|--------|-----------|
| 1 | Extract Analysis Service | 2 | 2-3 hrs | Medium |
| 1 | Create Result Repository | 3 | 2-3 hrs | Medium |
| 1 | Create LLM Provider Interface | 2 | 1-2 hrs | Low |
| 2 | Create Task Repository | 2 | 2-3 hrs | Medium |
| 2 | Create Controller | 3 | 3-4 hrs | High |
| 2 | Database Abstraction | 1 | 1-2 hrs | Low |
| 3 | Caching Layer | 2 | 3-4 hrs | Medium |
| 3 | Error Handling | Various | 2-3 hrs | Medium |
| **TOTAL** | | **18 files** | **18-26 hrs** | **Medium** |

### 4.4 Risk Assessment & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Breaking existing functionality | High | Medium | Comprehensive test coverage before refactor |
| Incomplete phase 1 creates bottleneck | High | Low | Complete phase 1 fully before phase 2 |
| Over-engineering with too abstractions | Medium | Medium | Start with minimal interfaces, expand as needed |
| Database schema mismatch | Medium | Low | Design schema before implementation |
| Performance degradation | Medium | Low | Profile before/after refactoring |

---

## 5. Summary & Recommendations

### 5.1 Overall Assessment

**Current State (AS-IS):** ⭐⭐⭐⭐
- Functional and feature-complete
- Good separation between UI layers
- Works well for current scope
- Lacks enterprise-grade architecture

**Proposed State (TO-BE):** ⭐⭐⭐⭐⭐
- Scalable and maintainable
- Provider-agnostic design
- Clear separation of concerns
- Production-ready architecture

### 5.2 Key Recommendations

1. **Phase 1 is Essential** (High ROI)
   - Extract analysis service immediately
   - Establish repository pattern
   - Create provider interface
   - Estimated time: 5-8 hours

2. **Phase 2 Enables Growth** (Medium ROI)
   - Build once Phase 1 stabilizes
   - Supports multi-backend deployment
   - Estimated time: 7-10 hours

3. **Phase 3 is Optional** (Lower ROI)
   - Implement based on performance needs
   - Not required for MVP
   - Estimated time: 5-8 hours

### 5.3 Success Criteria

After full migration to TO-BE:

- ✅ Each component has single responsibility
- ✅ Interfaces exist for all external integrations
- ✅ Storage backend is pluggable
- ✅ LLM provider is swappable
- ✅ >80% test coverage maintained
- ✅ Performance benchmarks met
- ✅ Zero breaking changes to user-facing APIs

---

## Appendix: Architecture Decision Records (ADRs)

### ADR-1: Repository Pattern for Data Access
**Decision:** Implement repository pattern for all data access
**Rationale:** Decouples business logic from persistence details
**Consequence:** Can swap storage backends without affecting application logic

### ADR-2: Service Layer for Orchestration
**Decision:** Create explicit service layer separate from algorithm
**Rationale:** Analyzer focuses on algorithm, Service handles workflow
**Consequence:** Better testability and clearer responsibilities

### ADR-3: Provider Abstraction for LLM
**Decision:** Create ILLMProvider interface
**Rationale:** Enables multi-provider support without code changes
**Consequence:** Minimal coupling to specific LLM vendors

### ADR-4: Adapter Pattern for Task Trackers
**Decision:** Use adapter pattern for Jira integration
**Rationale:** Future-proofs against task tracker changes
**Consequence:** Supports multiple task trackers transparently

---

**End of Architecture Analysis Report**
