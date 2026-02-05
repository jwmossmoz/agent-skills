# Redash Query Tool

Query Mozilla's Redash (sql.telemetry.mozilla.org) for telemetry data. Redash is the front-end to BigQuery telemetry data.

## Prerequisites

1. **API Key** - Set `REDASH_API_KEY` environment variable
2. **uv** - For running the script (uses only standard library, no dependencies)

## Quick Start

```bash
export REDASH_API_KEY="your-api-key-here"

# Get Windows build distribution summary
uv run skills/redash/scripts/query_redash.py --query windows_10_build_distribution

# Save detailed aggregate data to file
uv run skills/redash/scripts/query_redash.py --query windows_10_aggregate --output ~/moz_artifacts/aggregate.json
```

## Usage

```bash
# List available pre-defined queries
uv run skills/redash/scripts/query_redash.py --list-queries

# Run a pre-defined query (table format)
uv run skills/redash/scripts/query_redash.py --query windows_10_build_distribution

# Save results to file
uv run skills/redash/scripts/query_redash.py --query windows_10_aggregate --output ~/moz_artifacts/aggregate.json

# Run custom SQL
uv run skills/redash/scripts/query_redash.py --sql "SELECT * FROM \`moz-fx-data-shared-prod.telemetry.windows_10_build_distribution\` LIMIT 10"

# Fetch cached results from existing Redash query by ID
# (e.g., from https://sql.telemetry.mozilla.org/queries/65967)
uv run skills/redash/scripts/query_redash.py --query-id 65967

# Output as JSON or CSV
uv run skills/redash/scripts/query_redash.py --query windows_10_build_distribution --format json
uv run skills/redash/scripts/query_redash.py --query windows_10_build_distribution --format csv

# Limit displayed rows (still saves all to file)
uv run skills/redash/scripts/query_redash.py --query windows_10_aggregate --limit 20
```

## Pre-defined Queries

| Query Name | Description |
|------------|-------------|
| `windows_10_build_distribution` | Aggregated counts by Windows build group (Win10 22H2, Win11 24H2, etc.) |
| `windows_10_aggregate` | Detailed breakdown with UBR patch level and Firefox version |
| `windows_10_patch_adoption` | Patch-level adoption by build number and UBR |
| `list_windows_tables` | List all Windows-related tables in the telemetry dataset |

## Available Tables

Tables in `moz-fx-data-shared-prod.telemetry` related to Windows:

| Table | Description |
|-------|-------------|
| `windows_10_build_distribution` | Summary by build group |
| `windows_10_aggregate` | Detailed: build_number, ubr, ff_version, channel, count |
| `windows_10_patch_adoption` | Patch adoption frequency by UBR |
| `fx_health_ind_windows_versions_mau_per_os` | Daily MAU/DAU by Windows version |

## Windows Build Number Reference

| Build | Version |
|-------|---------|
| 19045 | Win10 22H2 |
| 19044 | Win10 21H2 |
| 19043 | Win10 21H1 |
| 19042 | Win10 20H2 |
| 19041 | Win10 2004 |
| 18363 | Win10 1909 |
| 18362 | Win10 1903 |
| 17763 | Win10 1809 |
| 22000 | Win11 21H2 |
| 22621 | Win11 22H2 |
| 22631 | Win11 23H2 |
| 26100 | Win11 24H2 |
| 26200 | Win11 25H2 |

## API Reference

- Base URL: `https://sql.telemetry.mozilla.org`
- Data Source ID: `63` (Telemetry BigQuery)
- BigQuery Project: `moz-fx-data-shared-prod`

### Endpoints Used

- `POST /api/query_results` - Execute a query (returns job ID)
- `GET /api/jobs/{job_id}` - Poll for job completion
- `GET /api/query_results/{result_id}` - Fetch results
- `GET /api/queries/{query_id}` - Get query metadata (for cached results)

## Dashboard Reference

The Windows 10 Client Distributions dashboard:
https://sql.telemetry.mozilla.org/dashboard/windows-10-client-distributions
