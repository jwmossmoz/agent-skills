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

1. **1Password CLI** - API key is retrieved automatically from 1Password
   - Item name: `Sql Telemetry Mozilla API`
   - Ensure you're signed in: `op signin`

2. **uv** - For running the script (uses only standard library, no dependencies)

## Quick Start

```bash
cd skills/redash/scripts

# Get Windows build distribution summary
uv run query_redash.py --query windows_10_build_distribution

# Save detailed aggregate data to file
uv run query_redash.py --query windows_10_aggregate --output ~/moz_artifacts/aggregate.json
```

## Usage

See [references/README.md](references/README.md) for full documentation.
