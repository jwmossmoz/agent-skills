---
name: redash
description: >
  Query Mozilla's Redash (sql.telemetry.mozilla.org) for telemetry data from BigQuery.
  Use when querying Firefox user telemetry, Windows build distribution, or running
  custom SQL against Mozilla's data warehouse. Triggers on "redash", "telemetry query",
  "sql.telemetry", "BigQuery query", "Firefox data", "client counts", "user population".
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

## Common Queries
@references/common-queries.md
