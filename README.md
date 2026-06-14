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
   LLM_PROVIDER_TYPE=openai-compatible
   LLM_BASE_URL=https://api.example.com/v1
   LLM_MODEL=your-model-name
   LLM_API_KEY=your_api_key

   JIRA_SERVER_URL=https://jira.example.com
   JIRA_USERNAME=your-user
   JIRA_API_TOKEN=your-token # or password
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

Start both analyzer and mock Jira services:

```bash
docker compose up --build
```

The setup uses environment variables to configure the LLM provider and Jira connection. By default:
- **LLM provider**: `openai-compatible` (requires `LLM_API_KEY`)
- **LLM base URL**: `https://api.deepseek.com/v1`
- **LLM model**: `deepseek-chat`
- **Jira server**: `http://mock-jira:8081` (internal Docker network)

#### Using with OpenAI-compatible LLM

Create a `.env` file to provide the API key:

```env
LLM_API_KEY=your_api_key_here
```

Then start:

```bash
docker compose up --build
```

Or set the key via shell environment:

```bash
LLM_API_KEY=your_api_key_here docker compose up --build
```

#### Using with fake LLM for testing

Override the provider to fake mode:

```bash
LLM_PROVIDER_TYPE=fake docker compose up --build
```

Open the UI at `http://localhost:8501`.


## Environment variables

### LLM Provider

- `LLM_PROVIDER_TYPE`: `fake` or `openai-compatible` (default: `fake`)
- `LLM_API_KEY`: API key for OpenAI-compatible providers
- `LLM_BASE_URL`: API endpoint for OpenAI-compatible providers (default: `http://localhost:8000/v1`)
- `LLM_MODEL`: model name for LLM requests (default: `default-model`)
- `LLM_REASONING_EFFORT`: reasoning/thinking mode — `none`, `low`, `medium`, `high` (default: `none`)
  - `none` — no thinking tokens. Sends `think: false` (Ollama native, harmlessly ignored by others).
  - `low`/`medium`/`high` — sends `reasoning_effort` parameter (OpenAI o-series, LLama, etc.).
- `LLM_FAKE_SCENARIO`: scenario name for fake provider responses — `default`, `reset`, `risk`, `task` (default: `default`)

### Retry & Error Handling

The OpenAI-compatible provider automatically retries transient API errors:
- **Rate limits** (HTTP 429), **timeouts**, **connection drops**, and **server errors** (5xx) are retried up to **3 times** with exponential backoff (1s → 2s → 4s).
- **Authentication failures**, **bad requests**, and **permission errors** are reported immediately without retry.
- All errors are wrapped in descriptive, actionable messages and surfaced in the UI.

### Logging

- `LOG_LLM_PROMPTS`: set to `true` to log full LLM request/response payloads (default: `false`)

### Jira

- `JIRA_SERVER_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`: Jira credentials

## Project structure

- `src/jira_analyzer/`: core application logic
- `src/mock_jira/`: local Jira-compatible mock service
- `data/`: sample JSON and output files
- `docs/`: architecture and design notes
- `tests/`: automated tests

## Docs

See `docs/architecture.md` and `docs/sequence_diagram.md` for system design details.
