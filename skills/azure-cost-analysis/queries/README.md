# Standalone Queries

Copy-paste-ready SQL for BigQuery via Redash. Each file has a header comment with purpose, inputs, and a link to the relevant reference doc for context.

| File | Purpose |
|---|---|
| `azure-task-counts.sql` | Azure-only task volumes by branch and pool (from `taskclusteretl.derived_task_summary`) |
| `spot-evictions.sql` | Spot eviction (`worker-shutdown`) and queue starvation (`claim-expired`) counts by pool and region (from `fxci.task_runs`) |
| `retry-rate.sql` | Task retry rate by pool by month (multiple-run_id analysis from `fxci.tasks` + `fxci.task_runs`) |
| `schema-sample.sql` | Quick schema check template for any BigQuery table |

## How to use

1. Open the .sql file
2. Replace `YYYY-MM-DD` placeholders with your date range
3. Adjust the `IN (...)` lists for pools of interest where applicable
4. Paste into Redash, run against the BigQuery data source

For Treeherder (PostgreSQL) push count queries — out of scope for this skill since they live in a different database. See your organization's Treeherder Redash for that data.

For the Cost Management REST API JSON request body — see `../references/cost-management-api.md` (not SQL).
