# Jira AI Analyzer Use Cases

## Actors

- **User**: interacts with the Streamlit UI to configure analysis, select issue sources, and review/export results.
- **Analysis Service**: orchestrates issue loading, AI analysis, and persistence.
- **LLM Provider**: performs AI inference, either in fake mode or via an OpenAI-compatible API.
- **Jira / Mock Jira**: provides issue data for analysis.
- **Storage**: SQLite repository that saves analysis runs, task states, and results.

## Primary use cases

### 1. Configure analysis

- Set LLM provider type and credentials.
- Set Jira server URL, username, and API token.
- Edit or import/export prompt configuration.
- Define evaluation criteria and scoring systems.
- Choose whether to include an overall conclusion.
- Enable split-by-criterion analysis mode.
- Choose worker count for concurrent analysis.

### 2. Select issue source

- Upload a local Jira JSON dataset.
- Use sample input data from `data/input.json`.
- Analyze a single Jira issue by key.
- Search Jira using JQL and analyze matching issues.
- Use a local mock Jira instance for offline development.

### 3. Load and normalize issues

- Fetch a Jira issue by key from Jira or mock Jira.
- Search Jira by JQL and retrieve issue list.
- Load issue list from local JSON data.
- Convert Jira issue fields into the internal analysis input format.

### 4. Run AI analysis

- Build prompts from configured system prompt, general prompt, and criteria.
- Call the selected LLM provider for each issue.
- Support fake LLM responses for testing.
- Support real OpenAI-compatible API calls.
- Optionally split analysis into separate requests per criterion.
- Perform analysis in parallel using worker threads.

### 5. Persist analysis state

- Save pending tasks to SQLite before analysis begins.
- Update task state to processing while analysis runs.
- Save completed analysis results.
- Save failed results and error details.
- Store analysis run metadata and criteria definitions.

### 6. View results

- Display analysis results in the Streamlit UI.
- Show issue details, criteria breakdown, verdict, and recommendations.
- Filter and search analysis results in the UI.
- Switch between analysis and results pages.

### 7. Export output

- Export results as JSON.
- Generate a Markdown report from analysis results.
- Save results into a SQLite database file.

## Supporting capabilities

- Orchestrate issue acquisition, AI calls, and persistence in the `AnalysisService`.
- Provide default prompt configuration and custom prompt templates.
- Detect and optionally exclude closed issues from analysis.
- Support local development and deterministic experiments with fake provider mode.
- Enable Docker Compose and mock Jira workflows for easy local setup.
