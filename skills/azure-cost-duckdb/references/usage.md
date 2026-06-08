# Usage Reference

All commands use:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py
```

## Config

Copy the placeholder config and fill in private values outside git:

```bash
cp ~/.claude/skills/azure-cost-duckdb/scripts/config.toml.example \
  ~/.config/azure-cost-duckdb.toml
```

The default local cache is `~/moz_artifacts/azure-cost/raw`; the default DuckDB file is `~/moz_artifacts/azure-cost/azure_cost.duckdb`.

## Commands

Check prerequisites:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  doctor --config ~/.config/azure-cost-duckdb.toml --azure-account
```

Preview and then download:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  sync --config ~/.config/azure-cost-duckdb.toml --latest-run --dry-run
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  sync --config ~/.config/azure-cost-duckdb.toml --latest-run
```

Inspect schema and stats:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  schema --config ~/.config/azure-cost-duckdb.toml
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  stats --config ~/.config/azure-cost-duckdb.toml --count-rows
```

Validate downloaded CSV partitions:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  validate --config ~/.config/azure-cost-duckdb.toml
```

Run SQL:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  query --config ~/.config/azure-cost-duckdb.toml \
  --sql "SELECT count(*) AS rows FROM azure_cost"
```

Print SQL for the DuckDB CLI:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  init-sql --config ~/.config/azure-cost-duckdb.toml > /tmp/azure-cost-init.sql
duckdb ~/moz_artifacts/azure-cost/azure_cost.duckdb -init /tmp/azure-cost-init.sql
```

## Direct Args Instead Of Config

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py sync \
  --account-name <storage-account> \
  --container <container> \
  --prefix <export-name>/<YYYYMMDD-YYYYMMDD> \
  --latest-run \
  --data-root ~/moz_artifacts/azure-cost/<month>/raw \
  --database ~/moz_artifacts/azure-cost/<month>/azure_cost.duckdb
```

Scope `--prefix` to one date-range directory so `--latest-run` resolves to that
month's latest snapshot. A shallower prefix (`<export-name>` alone) pulls every
run of every month. Give each month its own `--data-root`/`--database`: the
view UNIONs every CSV under `data_root`, so mixing two full-month snapshots in
one folder double-counts. See `references/azure-exports.md`.

## Output Formats

`query` and `schema` support `--format table`, `--format json`, and `--format csv`.

## CSV Exports

The helper auto-selects Parquet when present and otherwise reads `*.csv` / `*.csv.gz` files. Azure actual-cost CSV exports commonly use `MM/DD/YYYY` dates, so the default CSV date format is `%m/%d/%Y`. Override with `--csv-dateformat` if a different export schema needs it.

Azure tag columns can make long CSV rows. The helper sets DuckDB
`max_line_size` to 8 MiB by default; override with `--csv-max-line-size` if
needed.

Use `validate` after large CSV downloads. It reports physical CSV row counts,
NUL bytes, the largest line, and files that exceed the configured line-size
limit. Compare `csv_data_rows_by_lines` with `_manifest.json`'s `dataRowCount`.

If a download is interrupted and `validate` finds NUL bytes or a manifest row
count mismatch, rerun `sync` with overwrite for the suspect partition:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py sync \
  --config ~/.config/azure-cost-duckdb.toml \
  --latest-run \
  --pattern 000013.csv
```

Do not rely on `--no-overwrite` for resume semantics; Azure CLI errors when
the destination file already exists. Narrow `--pattern` to the missing or
suspect partition and overwrite it.

`--csv-relaxed` adds DuckDB `strict_mode=false` and `ignore_errors=true`. Use
it only while diagnosing malformed source files, then validate row counts
before trusting aggregates.

## Auth Modes

The default storage auth mode is `login`. If Azure CLI reports that the account lacks Blob Data Reader/Contributor/Owner, rerun with `--auth-mode key` only when your account is allowed to query the storage account key.
