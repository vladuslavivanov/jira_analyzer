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
| `task_id` | `TEXT PRIMARY KEY` | Issue key, e.g. `YA-1` |
| `run_id` | `INTEGER` | Foreign key referencing `analysis_runs(run_id)`. |
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

The `config_json` column in `analysis_configs` stores the full analysis configuration as a JSON object:

```json
{
  "system_prompt": "You are a code reviewer.",
  "general_prompt": "Analyze the following.",
  "include_overall_conclusion": true,
  "split_by_criterion": false,
  "reasoning_enabled": true,
  "reasoning_effort": "high",
  "criteria": [
    {
      "title": "Quality",
      "description": "Code quality",
      "scoring_system": "percent",
      "include_review": false,
      "key": "quality"
    },
    {
      "title": "Security",
      "description": "Security review",
      "scoring_system": "binary",
      "include_review": true,
      "key": "security"
    }
  ]
}
```

### Top‑level fields

| Field | Type | Description |
|---|---|---|
| `system_prompt` | `string` | System-level instruction for the LLM |
| `general_prompt` | `string` | General instruction prepended to every analysis prompt |
| `include_overall_conclusion` | `boolean` | Whether to request an overall conclusion in the response |
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

The only schema migration performed automatically is adding the `config_id` column to `analysis_runs` if it is missing (for databases created before the config‑based schema was introduced). This is done via:

```sql
ALTER TABLE analysis_runs ADD COLUMN config_id INTEGER;
```

The migration runs inside `_initialize_database()` on every application start and is **idempotent** (the `PRAGMA table_info` check prevents duplicate attempts).

---

## Schema version history

| Version | Changes |
|---|---|
| 1 (original) | `analysis_runs` with inline config columns (`system_prompt`, `general_prompt`, etc.), separate `criteria` table |
| 2 (current) | `analysis_configs` table added, config columns removed from `analysis_runs`, `criteria` table removed. Config stored as JSON in `analysis_configs.config_json`, deduplicated by SHA-256 hash. |
