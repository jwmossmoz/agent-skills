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

Use this skill to download Azure Cost Management exports from Blob Storage and query local files with DuckDB. Keep exports and credentials outside this directory.

## Prerequisites

- Cost exports writing Parquet/CSV to Blob Storage
- Azure CLI authenticated with Blob data access
- `uv`; the helper installs DuckDB

## Usage

Create config from `scripts/config.toml.example`, then run:

```bash
AZC=~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py
uv run "$AZC" sync --config ~/.config/azure-cost-duckdb.toml --dry-run
uv run "$AZC" query --config ~/.config/azure-cost-duckdb.toml \
  --sql "SELECT count(*) AS rows FROM azure_cost"
```

See [usage.md](references/usage.md) for all commands.

## Examples

- "Refresh May cost exports and show top worker pools."
- "Validate my local Azure cost CSV cache."

## Gotchas And Troubleshooting

- Run `sync --dry-run` first; `--pattern` matches container paths.
- Use `sync --latest-run` for month folders with snapshots.
- Run `validate` after large CSV downloads; row counts should match manifests.
- If interrupted, overwrite suspect partitions with `sync --pattern <file>.csv`;
  Azure CLI `--no-overwrite` does not resume.
- Run `schema` first; export column names vary.
- Current periods can be rerated; refresh current month data.
- DuckDB locks a `.duckdb` file per process.
- Do not commit `raw/`, `.duckdb`, keys, tokens, or real config.

## References

- [usage.md](references/usage.md) — Commands.
- [azure-exports.md](references/azure-exports.md) — Export behavior.
- [duckdb-queries.md](references/duckdb-queries.md) — SQL patterns.
