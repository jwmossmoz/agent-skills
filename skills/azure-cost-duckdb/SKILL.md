---
name: azure-cost-duckdb
description: >
  Download Azure Cost Management export blobs with Azure CLI and query
  local Parquet in DuckDB. Use when refreshing local Azure cost caches or
  writing DuckDB SQL over exports. DO NOT USE FOR live Cost Management API
  diagnosis; use azure-cost-analysis.
metadata:
  version: "1.0"
---

# Azure Cost DuckDB

Download Azure Cost Management exports from Blob Storage and query them locally with DuckDB. Keep exports and credentials outside this directory.

## Prerequisites

- Cost exports writing Parquet/CSV to Blob Storage
- Azure CLI authenticated for Blob data access
- `uv` (the helper installs DuckDB)

## Usage

Create config from `scripts/config.toml.example`, then run:

```bash
AZC=~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py
uv run "$AZC" sync --config ~/.config/azure-cost-duckdb.toml --dry-run
uv run "$AZC" query --config ~/.config/azure-cost-duckdb.toml --sql "SELECT 1"
```

See [usage.md](references/usage.md) for all commands.

## Examples

- "Refresh May cost exports and show top worker pools."
- "Validate my local Azure cost CSV cache."

## Gotchas And Troubleshooting

- `sync --dry-run` first; `--pattern` matches container paths.
- `sync --latest-run` for month folders with snapshots.
- `validate` after large CSV downloads; row counts should match manifests.
- Resume an interrupted download by overwriting the partition with
  `sync --pattern <file>.csv`; `--no-overwrite` does not resume.
- `schema` first; export column names vary.
- Group by the derived `worker_pool_id`, not the raw tag: Azure uses both
  `worker-pool-id` (VMs) and `worker_pool_id` (infra), so the hyphen tag alone
  buries the rest in `(untagged)`.
- Absent from cost data ≠ free: a SKU with no regional price meter emits no
  row. Reconcile against the Cost Management and Retail Prices APIs before
  reporting zero — see [azure-exports.md](references/azure-exports.md).
- Current periods can be rerated; refresh current month data.
- DuckDB locks a `.duckdb` file per process.
- Do not commit `raw/`, `.duckdb`, keys, tokens, or real config.

## References

- [usage.md](references/usage.md) — Commands.
- [azure-exports.md](references/azure-exports.md) — Export behavior.
- [duckdb-queries.md](references/duckdb-queries.md) — SQL patterns.
