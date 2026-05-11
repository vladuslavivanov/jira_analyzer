# Jira AI Analyzer

Tool for automatic data collection and analysis of Jira task tracker with AI-driven quality estimation.

## Installation

1. Clone the repository.
2. Install dependencies using [uv](https://github.com/astral-sh/uv):
   ```bash
   uv sync
   ```
3. Create a `.env` file in the `jira_analyzer` directory and add your DeepSeek API key:
   ```env
   DEEPSEEK_API_KEY=your_api_key_here
   ```

## Usage

The project uses a unified entry point via `python -m jira_analyzer`.

### Web User Interface (Streamlit)
Launch the interactive browser-based UI:

```bash
# as project script:
uv run jira-analyzer

# or as python module:
python -m jira_analyzer

# or directly with streamlit:
streamlit run src/jira_analyzer/app/streamlit.py
```

Optional command line interface (CLI):
```bash
uv run python src/jira_analyzer/app/cli.py --input data/input.json --output data/output.json
```

Analyze a single Jira issue from the CLI:

```bash
uv run jira-analyzer --jira-server http://127.0.0.1:8081 --jira-issue YA-1 --jira-no-verify
```

Analyze Jira issues by JQL and export a Markdown report:
```bash
uv run jira-analyzer --jira-server http://127.0.0.1:8081 --jql "project = YA" --jira-no-verify --markdown-output data/report.md
```

Run analysis with multiple parallel workers:
```bash
uv run jira-analyzer --jira-server http://127.0.0.1:8081 --jql "project = YA" --jira-no-verify --workers 2
```

The Streamlit UI also supports Jira issue lookup in the sidebar.
It can fetch either a single issue key or a JQL query, edit the LLM prompt before
analysis, configure the number of parallel analysis workers, preview the
Markdown report, and download JSON or Markdown results.


### Local Mock Jira
Launch a Jira-compatible mock REST API service:

```bash
# as project script:
uv run mock-jira

# or as python module:
python -m mock_jira
```

The server starts at `http://127.0.0.1:8081` and supports issue lookup by key:

Mock issues live in `data/mock_jira_issues.json`. The default data contains `YA-1` and `YA-2` in this format:
```json
[
  {
    "key": "YA-1",
    "element type": "Risk",
    "description": "Risk description"
  }
]
```


## Project Structure

- `src/`
  - jira_analyzer/`: Core package logic.
    - `analyzer/`: AI analysis engine and prompt templates.
    - `tasktracker/`: Jira data parsing and extraction.
    - `app/`: Analyzer application.
      - `streamlit.py`: Streamlit web application.
      - `cli.py`: Command-line interface logic.
  - `mock_jira/`: Local Jira REST API mock for development.
- `data/`: Sample input and output JSON files.
- `tests/`: Quality assurance suite.
