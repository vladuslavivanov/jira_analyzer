# Database Schema

The application uses a **SQLite** database to persist analysis runs, configurations, and results. The schema is designed to separate **configuration** (prompts, criteria, reasoning settings) from **analysis sessions** (runs), so identical configurations are stored once regardless of how many times they are used.

---

## Tables

### `analysis_runs` — one row per analysis session

| Column | Type | Description |
|---|---|---|
| `run_id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Unique session identifier |
| `run_name` | `TEXT` | Human-readable label, defaults to the current datetime (e.g. `2026-06-10 12:01:45`) |
| `created_at` | `TEXT` | ISO-8601 timestamp when the run was created |
| `config_id` | `INTEGER` | Foreign key referencing `analysis_configs(config_id)`. `NULL` for runs created before the config‑based schema. |

Indexes:
- `idx_analysis_results_run_id` on `analysis_results(run_id)` — speeds up lookups of results by run.
- `idx_analysis_results_task_id` on `analysis_results(task_id)` — speeds up lookups by task across runs.

### `analysis_configs` — one row per unique configuration

| Column | Type | Description |
|---|---|---|
| `config_id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Unique configuration identifier |
| `config_hash` | `TEXT UNIQUE` | SHA-256 fingerprint of the canonical `config_json` content. Used for deduplication: two runs that use identical prompts, criteria and settings share the same `config_id`. |
| `config_json` | `TEXT NOT NULL` | Full configuration serialized as JSON (see [structure](#config_json-structure) below). |
| `created_at` | `TEXT` | ISO-8601 timestamp when this configuration was first seen. |

Indexes:
- `idx_analysis_configs_hash` on `config_hash` — fast lookup for config deduplication.

### `analysis_results` — one row per analyzed task within a run

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Surrogate primary key for row-level operations |
| `task_id` | `TEXT NOT NULL` | Issue key, e.g. `YA-1` |
| `run_id` | `INTEGER` | Foreign key referencing `analysis_runs(run_id)`. Together with `task_id` forms a unique constraint — the same task can appear in different runs. |
| `title` | `TEXT` | Issue title / summary |
| `description` | `TEXT` | Issue description |
| `status` | `TEXT` | Jira status (e.g. `In Progress`) |
| `assignee` | `TEXT` | Assignee display name |
| `created_at` | `TEXT` | Issue creation timestamp |
| `updated_at` | `TEXT` | Issue last-updated timestamp |
| `state` | `TEXT` | Analysis state: `PENDING`, `PROCESSING`, `COMPLETED`, or `FAILED` |
| `summary` | `TEXT` | Overall conclusion (JSON) |
| `recommendations` | `TEXT` | List of recommendations (JSON) |
| `raw_response` | `TEXT` | Full LLM response (JSON) |
| `analyzed_at` | `TEXT` | Timestamp when analysis completed |

**Unique constraint:** `UNIQUE(task_id, run_id)` — the same task can be analyzed in multiple runs, producing separate result rows per run.

Indexes:
- `idx_analysis_results_run_id` on `run_id` — speeds up lookups of results by run.
- `idx_analysis_results_task_id` on `task_id` — speeds up lookups by task across runs.

---

## Relationships

```
analysis_configs (1) ──→ (many) analysis_runs       via config_id
analysis_runs    (1) ──→ (many) analysis_results    via run_id
```

- **One config** can be referenced by **many runs** — this is where deduplication happens.
- **One run** can contain **many analyzed tasks** (results).

---

## `config_json` structure

The `config_json` column in `analysis_configs` stores the full analysis configuration as a JSON object matching the `AnalysisConfig` dataclass:

```json
{
  "criteria": [
    {
      "description": "Code quality",
      "include_review": false,
      "key": "quality",
      "scoring_system": "percent",
      "title": "Quality"
    },
    {
      "description": "Security review",
      "include_review": true,
      "key": "security",
      "scoring_system": "binary",
      "title": "Security"
    }
  ],
  "default_scoring_system": "percent",
  "general_prompt": "Analyze the following.",
  "include_overall_conclusion": true,
  "reasoning_enabled": true,
  "reasoning_effort": "high",
  "split_by_criterion": false,
  "system_prompt": "You are a code reviewer.",
  "version": 1
}
```

> Fields are alphabetically sorted (`sort_keys=True`) to produce a deterministic hash for deduplication.

### Top‑level fields

| Field | Type | Description |
|---|---|---|
| `version` | `integer` | Schema version (currently `1`) |
| `system_prompt` | `string` | System-level instruction for the LLM |
| `general_prompt` | `string` | General instruction prepended to every analysis prompt |
| `include_overall_conclusion` | `boolean` | Whether to request an overall conclusion in the response |
| `default_scoring_system` | `string` | Default scoring for new criteria: `"percent"`, `"binary"`, or `"five"` |
| `split_by_criterion` | `boolean` | If `true`, each criterion is sent as a separate LLM request |
| `reasoning_enabled` | `boolean` | Whether reasoning/thinking tokens are enabled |
| `reasoning_effort` | `string` | `"none"`, `"low"`, `"medium"`, or `"high"` |
| `criteria` | `array` | List of criterion definitions (see below) |

### Criterion object

| Field | Type | Description |
|---|---|---|
| `title` | `string` | Display name |
| `description` | `string` | Detailed description of what this criterion evaluates |
| `scoring_system` | `string` | `"percent"` (0–100%), `"binary"` (0/1), or `"five"` (0–5) |
| `include_review` | `boolean` | If `true`, the LLM is asked to provide a written review alongside the score |
| `key` | `string` | Machine‑readable key used for cross‑referencing scores in results |

---

## Config deduplication logic

1. When an analysis run is created, the service builds a canonical JSON dict of the full configuration (including sorted criteria) and serialises it with `json.dumps(…, sort_keys=True)`.
2. A **SHA-256 hash** is computed from that JSON string.
3. The repository looks for an existing row in `analysis_configs` with the same `config_hash`.
   - If found → reuses its `config_id`.
   - If not found → inserts a new `analysis_configs` row.
4. A new `analysis_runs` row is always created (each run is an independent session), referencing the `config_id`.

This means running the same prompts and criteria 10 times produces **1 row** in `analysis_configs` and **10 rows** in `analysis_runs`.

---

## Query patterns (reference)

### Get the latest result per task (default "All Runs" view)

```sql
SELECT * FROM analysis_results
WHERE id IN (
    SELECT MAX(id)
    FROM analysis_results
    GROUP BY task_id
)
ORDER BY COALESCE(analyzed_at, created_at) DESC;
```

### Get all results for a specific run

```sql
SELECT * FROM analysis_results
WHERE run_id = ?
ORDER BY COALESCE(analyzed_at, created_at) DESC;
```

### Get a run with its merged config data

```sql
SELECT r.run_id, r.run_name, r.created_at, r.config_id,
       c.config_json
FROM analysis_runs r
LEFT JOIN analysis_configs c ON r.config_id = c.config_id
WHERE r.run_id = ?;
```

The application code merges fields from `config_json` into the result dict so callers see `system_prompt`, `general_prompt`, etc. as top‑level keys.

### Get criteria for a run

```sql
SELECT c.config_json
FROM analysis_runs r
JOIN analysis_configs c ON r.config_id = c.config_id
WHERE r.run_id = ?;
```

Criteria are parsed from the `criteria` array inside `config_json`.

### Get all runs ordered by most recent

```sql
SELECT r.run_id, r.run_name, r.created_at, r.config_id
FROM analysis_runs r
ORDER BY r.created_at DESC;
```

---

## Migration

Schema migrations are performed automatically inside `_initialize_database()` on every application start.

### `analysis_configs`/`config_id` migration

For databases created before the config‑based schema was introduced, the `config_id` column is added to `analysis_runs`:

```sql
ALTER TABLE analysis_runs ADD COLUMN config_id INTEGER;
```

This is **idempotent** (the `PRAGMA table_info` check prevents duplicate attempts).

### `analysis_results` composite key migration

For databases created with the old `task_id TEXT PRIMARY KEY` schema, the `analysis_results` table is dropped and recreated with the new composite-key schema (`id INTEGER PRIMARY KEY AUTOINCREMENT` + `UNIQUE(task_id, run_id)`). The migration is triggered when the `id` column is not found.

Since the old schema could only store one result per task (the last run would overwrite earlier data), no data is lost — the new table starts empty and will be populated by subsequent analysis runs.

---

## Schema version history

| Version | Changes |
|---|---|
| 1 (original) | `analysis_runs` with inline config columns (`system_prompt`, `general_prompt`, etc.), separate `criteria` table |
| 2 | `analysis_configs` table added, config columns removed from `analysis_runs`, `criteria` table removed. Config stored as JSON in `analysis_configs.config_json`, deduplicated by SHA-256 hash. |
| **3 (current)** | `analysis_results` changed from `task_id TEXT PRIMARY KEY` to `id INTEGER PRIMARY KEY AUTOINCREMENT` + `UNIQUE(task_id, run_id)`. The same task can now be analyzed in multiple runs with different configurations, with each result preserved independently. The **Results Viewer** defaults to showing the latest result per task ("All Runs") but can be filtered to a specific run to compare across sessions. |
