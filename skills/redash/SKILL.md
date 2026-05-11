---
name: redash
description: >
  Query Mozilla's Redash (sql.telemetry.mozilla.org) for telemetry from
  BigQuery via saved query IDs or ad-hoc SQL. Use when the task references
  a saved query, needs FXCI worker-pool queue-time data, or wants results
  that can be shared and visualized. DO NOT USE FOR raw bq CLI work without
  a saved query (use bigquery).
metadata:
  version: "1.0"
---

# Redash Query Tool

Query Mozilla's Redash (sql.telemetry.mozilla.org) for telemetry data. Redash is the front-end to BigQuery telemetry data.

## Knowledge References
@references/README.md
@references/fxci-schema.md

## Prerequisites

- `REDASH_API_KEY` environment variable set
- `uv` for running the script

## Quick Start

```bash
# Run custom SQL
uv run scripts/query_redash.py --sql "SELECT * FROM telemetry.main LIMIT 10"

# Fetch cached results from an existing Redash query
uv run scripts/query_redash.py --query-id 65967

# Save results to file
uv run scripts/query_redash.py --sql "SELECT 1" --output ~/moz_artifacts/data.json
```

## Usage

Either `--sql` or `--query-id` is required.

| Flag | Description |
|------|-------------|
| `--sql` | SQL query to execute against BigQuery via Redash |
| `--query-id` | Fetch cached results from an existing Redash query ID |
| `--output`, `-o` | Save results to JSON file |
| `--format`, `-f` | Output format: `json`, `csv`, `table` (default: `table`) |
| `--limit` | Limit number of rows displayed |

## Example Prompts

These natural language prompts map to queries in `references/common-queries.md`:

| Prompt | Query used |
|--------|------------|
| "What's the DAU breakdown by macOS version?" | `--query-id 114866` (macOS Version DAU) |
| "Show me macOS version × architecture distribution" | `--query-id 114867` (macOS version × arch) |
| "What share of macOS users are on Apple Silicon?" | `--query-id 114867`, compare aarch64 vs x86_64 |
| "Pull the macOS DAU and arch breakdown for the last 28 days" | `--query-id 114866` and `--query-id 114867` |
| "What Windows versions are Firefox Desktop users on?" | `--query-id 65967` (Windows Version Distribution) |
| "How many Firefox users are on Windows 11?" | `--query-id 65967` |
| "What does the macOS adoption curve look like over time?" | `--query-id 114866`, look at darwin_version |
| "Why is a worker pool showing high queue time?" | Use the FXCI worker-pool queue-time query in `references/common-queries.md` |
| "What task groups are driving queue time for a worker pool?" | Use the FXCI worker-pool queue-time queries in `references/common-queries.md` |

For questions not covered by a documented query, write SQL on the fly using the table references in `references/README.md`.

## Common Queries
@references/common-queries.md

## Gotchas

- `--query-id N` returns *cached* results from the saved query's last run. Pass `--sql` if you need fresh data or different parameters.
- Required env: `REDASH_API_KEY` (get one from your Redash profile). Without it the script fails before hitting the API.
- For one-off analyses, write `--sql` inline rather than creating a saved query — saved queries proliferate, get stale, and clutter the UI for everyone.
- Redash query IDs in this skill (`65967`, `114866`, `114867`) are stable; if a query disappears, check `references/common-queries.md` for the SQL and re-create.
