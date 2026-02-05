---
name: redash
description: >
  Query Mozilla's Redash (sql.telemetry.mozilla.org) for telemetry data from BigQuery.
  Use when querying Firefox user telemetry, Windows build distribution, or running
  custom SQL against Mozilla's data warehouse.
---

# Redash Query Tool

Query Mozilla's Redash (sql.telemetry.mozilla.org) for telemetry data. Redash is the front-end to BigQuery telemetry data.

## Prerequisites

- `REDASH_API_KEY` environment variable set
- `uv` for running the script

## Quick Start

```bash
uv run skills/redash/scripts/query_redash.py --query windows_10_build_distribution
uv run skills/redash/scripts/query_redash.py --query windows_10_aggregate --output ~/moz_artifacts/aggregate.json
```

## Usage

See [references/README.md](references/README.md) for full documentation.
