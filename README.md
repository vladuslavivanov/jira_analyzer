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

## Project Structure

- `src/jira_analyzer/`: Core package logic.
  - `analyzer/`: AI analysis engine and prompt templates.
  - `tasktracker/`: Jira data parsing and extraction.
  - `ui.py`: Streamlit web application.
  - `cli.py`: Command-line interface logic.
- `data/`: Sample input and output JSON files.
- `tests/`: Quality assurance suite.
