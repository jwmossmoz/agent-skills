# Redash Query Tool

Query Mozilla's Redash (sql.telemetry.mozilla.org) for telemetry data. Redash is the front-end to BigQuery telemetry data.

## Prerequisites

1. **API Key** - Set `REDASH_API_KEY` environment variable
2. **uv** - For running the script (uses only standard library, no dependencies)

## Quick Start

```bash
export REDASH_API_KEY="your-api-key-here"

# Run a SQL query
uv run scripts/query_redash.py --sql "SELECT build_group, SUM(count) as observations FROM \`moz-fx-data-shared-prod.telemetry.windows_10_build_distribution\` GROUP BY 1 ORDER BY 1"

# Fetch cached results from an existing Redash query
uv run scripts/query_redash.py --query-id 65967

# Save results to file
uv run scripts/query_redash.py --sql "SELECT 1" --output data.json
```

## Usage

Either `--sql` or `--query-id` is required.

```bash
# Run custom SQL (table format by default)
uv run scripts/query_redash.py --sql "SELECT * FROM \`moz-fx-data-shared-prod.telemetry.windows_10_build_distribution\` LIMIT 10"

# Fetch cached results from existing Redash query by ID
# (e.g., from https://sql.telemetry.mozilla.org/queries/65967)
uv run scripts/query_redash.py --query-id 65967

# Output as JSON or CSV
uv run scripts/query_redash.py --sql "SELECT 1" --format json
uv run scripts/query_redash.py --sql "SELECT 1" --format csv

# Limit displayed rows (still saves all to file)
uv run scripts/query_redash.py --sql "SELECT 1" --limit 20
```

| Flag | Description |
|------|-------------|
| `--sql` | SQL query to execute against BigQuery via Redash |
| `--query-id` | Fetch cached results from an existing Redash query ID |
| `--output`, `-o` | Save results to JSON file |
| `--format`, `-f` | Output format: `json`, `csv`, `table` (default: `table`) |
| `--limit` | Limit number of rows displayed |

## Available Tables

Tables in `moz-fx-data-shared-prod.telemetry` related to Windows:

| Table | Description |
|-------|-------------|
| `windows_10_build_distribution` | Summary by build group |
| `windows_10_aggregate` | Detailed: build_number, ubr, ff_version, channel, count |
| `windows_10_patch_adoption` | Patch adoption frequency by UBR |
| `fx_health_ind_windows_versions_mau_per_os` | Daily MAU/DAU by Windows version |

### Endpoints Used

- `POST /api/query_results` - Execute a query (returns job ID)
- `GET /api/jobs/{job_id}` - Poll for job completion
- `GET /api/query_results/{result_id}` - Fetch results
- `GET /api/queries/{query_id}` - Get query metadata (for cached results)

## Dashboard Reference

The Windows 10 Client Distributions dashboard:
https://sql.telemetry.mozilla.org/dashboard/windows-10-client-distributions
