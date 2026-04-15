---
name: redash
description: >
  Query Mozilla's Redash (sql.telemetry.mozilla.org) for telemetry data from BigQuery.
  Use when querying Firefox user telemetry, OS distribution, architecture breakdown, FXCI
  task data, or running custom SQL against Mozilla's data warehouse. Triggers on "redash",
  "telemetry query", "sql.telemetry", "BigQuery query", "Firefox data", "client counts",
  "user population", "DAU", "MAU", "macOS version", "macOS distribution", "Apple Silicon",
  "aarch64", "x86_64", "architecture distribution", "Windows version", "Windows distribution",
  "how many users", "what share of users", "what percentage of Firefox users", "worker pool",
  "queue time", "Taskcluster queue", "FXCI task data".
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
