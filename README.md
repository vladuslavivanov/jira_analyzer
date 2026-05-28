# Jira AI Analyzer

A compact AI-powered Jira issue quality linter with a Streamlit browser interface.

## What it does

- Analyze Jira issues or sample JSON for quality, verdicts, and recommendations.
- Use a single issue key, JQL query, or local `data/input.json`.
- Run in browser with Streamlit.
- Export results as JSON and optional Markdown.
- Support fake LLM responses for local testing or OpenAI-compatible providers for real analysis.

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```
2. Create a `.env` file in the repository root for provider and Jira settings:
   ```env
   LLM_PROVIDER_TYPE=fake
   LLM_API_KEY=your_openai_api_key
   LLM_BASE_URL=http://localhost:8000/v1
   LLM_MODEL=your-model-name
   JIRA_SERVER_URL=https://jira.example.com
   JIRA_USERNAME=your-user
   JIRA_API_TOKEN=your-token
   ```
3. For local tests, use the sample input file: `data/input.json`.

### Install with pip

Install project dependencies with pip and editable mode:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r requirements.txt
```

## Run

### Streamlit UI

```bash
uv run jira-analyzer
```

Or, without uv:

```bash
python -m streamlit run src/jira_analyzer/app/streamlit.py
```

Or directly launch the package:

```bash
python -m jira_analyzer
```

### Mock Jira

```bash
uv run mock-jira
```

Then point the UI to `http://127.0.0.1:8081`.

### Docker Compose

```bash
docker compose up --build
```

Open the UI at `http://localhost:8501`.

## Environment variables

- `LLM_PROVIDER_TYPE`: `fake` or `openai-compatible` (default: `fake`)
- `LLM_API_KEY`: key for OpenAI-compatible providers
- `LLM_BASE_URL`: API endpoint for OpenAI-compatible providers
- `LLM_MODEL`: model name for LLM requests
- `JIRA_SERVER_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`: Jira credentials

## Project structure

- `src/jira_analyzer/`: core application logic
- `src/mock_jira/`: local Jira-compatible mock service
- `data/`: sample JSON and output files
- `docs/`: architecture and design notes
- `tests/`: automated tests

## Docs

See `docs/architecture.md` and `docs/sequence_diagram.md` for system design details.
