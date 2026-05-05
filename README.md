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

### Command Line Interface (CLI)
Run the analysis on a JSON file and save the results:
```bash
uv run python src/jira_analyzer --input data/input.json --output data/output.json
```

### Web User Interface (Streamlit)
Launch the interactive browser-based UI:
```bash
uv run python src/jira_analyzer --streamlit
```

### Local Mock Jira
Launch a Jira-compatible mock REST API:
```bash
uv run mock-jira
```

The server starts at `http://127.0.0.1:8081` and supports issue lookup by key:
```python
from jira import JIRA

jira = JIRA(server="http://127.0.0.1:8081", options={"verify": False})
issue = jira.issue("YA-1")

print(issue.key)
print(issue.fields.summary)
```

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

Analyze a single Jira issue from the CLI:
```bash
uv run jira-analyzer --jira-server http://127.0.0.1:8081 --jira-issue YA-1 --jira-no-verify
```

The Streamlit UI also supports Jira issue lookup in the sidebar.

## Project Structure

- `src/jira_analyzer/`: Core package logic.
  - `analyzer/`: AI analysis engine and prompt templates.
  - `mock_jira/`: Local Jira REST API mock for development.
  - `tasktracker/`: Jira data parsing and extraction.
  - `ui.py`: Streamlit web application.
  - `cli.py`: Command-line interface logic.
- `data/`: Sample input and output JSON files.
- `tests/`: Quality assurance suite.
