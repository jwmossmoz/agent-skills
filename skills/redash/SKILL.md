---
name: redash
description: >
  Use when running Mozilla Redash saved queries or ad hoc SQL for shareable
  telemetry, visualizations, and FXCI queue analysis. DO NOT USE FOR direct bq
  CLI work.
metadata:
  version: "1.1"
---

# Redash

Use the helper to fetch cached saved-query results or run fresh SQL through
Mozilla Redash.

## Prerequisites

Set `REDASH_API_KEY` from the Redash profile page. Install `uv`.

## Usage

```bash
REDASH=~/.claude/skills/redash/scripts/query_redash.py

# Fetch the latest cached result stored for a saved query.
uv run "$REDASH" --query-id 65967 --format json

# Run fresh SQL and save the result.
uv run "$REDASH" --sql 'SELECT ...' \
  --output ~/moz_artifacts/redash-result.json
```

Run `uv run "$REDASH" --help` for output formats and limits. Read
[common-queries.md](references/common-queries.md) for maintained query IDs and
FXCI examples. Read [fxci-schema.md](references/fxci-schema.md) for FXCI tables
or [README.md](references/README.md) for telemetry tables.

## Gotchas

- `--query-id` returns the saved query's cached result. Use `--sql` when the
  result must be fresh or the parameters differ.
- Do not create a saved query for a one-time analysis. Run inline SQL to avoid
  stale shared objects.
- If a maintained query ID is missing, use its SQL from
  [common-queries.md](references/common-queries.md).

## Related Skills

- Use **bigquery** for direct `bq` access, dry runs, and scripted raw SQL.
