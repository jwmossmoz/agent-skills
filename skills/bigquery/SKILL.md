---
name: bigquery
description: >
  Run ad-hoc SQL against Mozilla telemetry tables using the bq CLI. Use when
  the task needs raw BigQuery access — dry-run cost checks, custom SQL,
  pulling DAU/MAU/Windows-distribution/Glean-metric data into a script. DO
  NOT USE FOR saved/shared queries with visualizations (use redash) or
  finding which probe to query (use mozdata:probe-discovery).
metadata:
  version: "1.0"
---

# BigQuery

Query Mozilla telemetry data directly using the `bq` CLI.

## Prerequisites

- `gcloud` and `bq` CLI installed (`brew install google-cloud-sdk`)
- Authenticated: `gcloud auth login` with a Mozilla account
- Billing project set: queries run against a project you have `bigquery.jobs.create` on
- (Optional but highly recommended) [mozdata-claude-plugin](https://github.com/akkomar/mozdata-claude-plugin) — provides Glean Dictionary MCP for metric/ping discovery, making it much easier to find the right tables and columns

## Authentication

```bash
# Check current account
gcloud config get-value account

# Re-authenticate if needed
gcloud auth login

# List available projects
gcloud projects list --format="table(projectId,name)"

# Set billing project (mozdata is the standard choice)
gcloud config set project mozdata
```

If queries fail with "Access Denied", the billing project likely lacks permissions. Try `--project_id=mozdata`.

## Running Queries

```bash
# Basic query
bq query --project_id=mozdata --use_legacy_sql=false --format=pretty "SELECT ..."

# Dry run (check cost before executing)
bq query --project_id=mozdata --use_legacy_sql=false --dry_run "SELECT ..."
```

Always use `--project_id=mozdata` and `--use_legacy_sql=false`.

## Table Selection

Choose the right table — this is the most important optimization:

| Query Type | Table | Why |
|------------|-------|-----|
| Windows version distribution | `telemetry.windows_10_aggregate` | Pre-aggregated, instant |
| DAU/MAU by standard dimensions | `firefox_desktop_derived.active_users_aggregates_v3` | Pre-computed, 100x faster |
| DAU with custom dimensions | `firefox_desktop.baseline_clients_daily` | One row per client per day |
| MAU/WAU/retention | `firefox_desktop.baseline_clients_last_seen` | Bit patterns, scan 1 day not 28 |
| Event analysis | `firefox_desktop.events_stream` | Pre-unnested, clustered |
| Mobile search | `search.mobile_search_clients_daily_v2` | Pre-aggregated |
| Specific Glean metric | `firefox_desktop.metrics` | Raw metrics ping |

All tables are in the `moz-fx-data-shared-prod` project. Fully qualify as `` `moz-fx-data-shared-prod.{dataset}.{table}` ``.

## Critical Rules

- **Always use aggregate tables first** — raw tables are 10-100x more expensive
- **Always include partition filter** — `submission_date` or `DATE(submission_timestamp)`
- **Use `sample_id = 0`** for development (1% sample) — remove for production
- **Say "clients" not "users"** — BigQuery tracks `client_id`, not actual humans
- **Never join across products by client_id** — each product has its own namespace
- **Use `events_stream` for events** — never raw `events_v1` (requires UNNEST)
- **Use `baseline_clients_last_seen` for MAU** — bit patterns, scan 1 day not 28

## Gotchas

- "Access Denied" almost always means the billing project lacks `bigquery.jobs.create`. Switch with `gcloud config set project mozdata` or pass `--project_id=mozdata` per-query.
- `bq` defaults to legacy SQL. Always pass `--use_legacy_sql=false` — leaving it off silently changes the dialect mid-script.
- Aggregate tables are 10-100× cheaper than raw. Never query `events_v1` directly; use `events_stream`. Never join across products by `client_id` — each product has its own namespace.
- For MAU/WAU, use `baseline_clients_last_seen` bit patterns (1-day scan), not 28 days of `baseline_clients_daily` aggregates.
- `client_id` is not a person. Say "clients" in user-facing text, not "users".

## References

- `references/tables.md` — Detailed table schemas and common query patterns
- `references/os-versions.md` — Windows, macOS, and Linux version distribution queries with build number, Darwin, and kernel version mappings

## Related Skills

- **redash** — Web UI frontend to BigQuery with visualizations and sharing
- **mozdata:query-writing** — Guided query writing with Glean Dictionary MCP
- **mozdata:probe-discovery** — Find Glean metrics and telemetry probes
