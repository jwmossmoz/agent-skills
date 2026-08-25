---
name: bigquery
description: >
  Use when running ad hoc SQL, dry-run cost checks, or scripted analysis
  against Mozilla BigQuery telemetry. DO NOT USE FOR saved, shared, or
  visualized Redash queries.
metadata:
  version: "1.1"
---

# BigQuery

Use this skill for raw SQL, dry-run cost checks, and scripted telemetry
analysis. Prefer aggregate tables before raw pings.

## Prerequisites

```bash
brew install google-cloud-sdk
gcloud auth login
gcloud config set project mozdata
```

The account needs `bigquery.jobs.create` on the billing project.

## Usage

```bash
# Check bytes before execution.
bq query --project_id=mozdata --use_legacy_sql=false --dry_run 'SELECT ...'

# Run GoogleSQL and return structured output.
bq query --project_id=mozdata --use_legacy_sql=false --format=json 'SELECT ...'
```

Read [tables.md](references/tables.md) before you choose a table. Read
[os-versions.md](references/os-versions.md) for operating-system distribution
queries.

## Query rules

- Use an aggregate table when it can answer the question.
- Add a partition filter such as `submission_date`.
- Use `sample_id = 0` for development when the table supports it.
- Use `events_stream`, not raw `events_v1`.
- Use `baseline_clients_last_seen` for MAU and WAU.
- Do not join products by `client_id`; each product has a separate namespace.
- Describe `client_id` counts as clients, not people.

## Gotchas

- Always set `--project_id=mozdata` and `--use_legacy_sql=false`.
- An access error often means that the billing project cannot create query
  jobs. It does not necessarily mean that the source table is private.

## Related Skills

- Use **redash** for saved query IDs, shared results, and visualizations.
- Use the Mozilla data-discovery skills to identify a Glean metric or ping.
