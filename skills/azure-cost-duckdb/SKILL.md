---
name: azure-cost-duckdb
description: >
  Download Azure Cost Management exports and query local Parquet/CSV in
  DuckDB. Use when refreshing local Azure cost caches or writing DuckDB SQL
  over exports. DO NOT USE FOR live Cost Management API diagnosis; use
  azure-cost-analysis.
metadata:
  version: "1.0"
---

# Azure Cost DuckDB

Download Azure Cost Management exports from Blob Storage and query them locally with DuckDB.

## Prerequisites

- Cost exports (Parquet/CSV) in Blob Storage
- Azure CLI with Blob data access
- `uv` (installs DuckDB)

## Usage

Copy `scripts/config.toml.example`, then run:

```bash
AZC=~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py
uv run "$AZC" sync --config ~/.config/azure-cost-duckdb.toml
uv run "$AZC" query --config ~/.config/azure-cost-duckdb.toml --sql "SELECT 1"
```

See [usage.md](references/usage.md).

## Examples

- "Refresh May cost exports and show top worker pools."

## Gotchas And Troubleshooting

- `sync --dry-run` first; `--pattern` matches container paths.
- `sync --latest-run` for month folders with snapshots.
- `validate` after large CSV downloads; row counts should match manifests.
- Overwrite a bad partition: `sync --pattern <file>.csv`; `--no-overwrite`
  won't resume.
- `schema` first; export column names vary.
- Group by the derived `worker_pool_id` (both tag spellings); absent-from-data
  may be unbilled, not free — see
  [duckdb-queries.md](references/duckdb-queries.md),
  [azure-exports.md](references/azure-exports.md).
- Current periods can be rerated; refresh the current month.
- DuckDB locks a `.duckdb` file per process.
- Do not commit `raw/`, `.duckdb`, keys, tokens, or real config.

## References

- [usage.md](references/usage.md) — Commands.
- [azure-exports.md](references/azure-exports.md) — Export behavior.
- [duckdb-queries.md](references/duckdb-queries.md) — SQL patterns.
