---
name: azure-cost-analysis
description: >
  Analyze FXCI Azure CI costs across the 3 CI subscriptions (FXCI DevTest,
  Trusted FXCI, TC Engineering). Investigate cost increases by worker pool,
  SKU, region, or service. Distinguish volume-driven changes from rate
  changes (spot pricing, eviction overhead, VM lifecycle). Correlate with
  Taskcluster task volume from BigQuery and check fxci-config for cost-
  relevant changes. Triggers on "azure cost", "cost increase", "cost
  analysis", "worker pool cost", "FXCI spend", "cloud spend", "cost trend",
  "why did cost go up", "cost by worker pool", "cost per task", "spot
  eviction", "spot pricing", "cost diagnostic".
---

# Azure Cost Analysis

Diagnostic toolkit for FXCI Azure CI cost investigations. Covers all 3 CI subscriptions and multiple cost dimensions (pool, SKU, region, service). Designed for both routine cost trend analysis and deep diagnostic investigations.

## Knowledge References

**Read first:**
@references/README.md
@references/user-inputs.md
@references/methodology.md

**Multi-dimensional and multi-subscription:**
@references/cost-exports.md
@references/cost-dimensions.md
@references/multi-subscription.md

**API fallback and task correlation:**
@references/cost-management-api.md
@references/taskcluster-task-counting.md

**For deep diagnostics:**
@references/fxci-config-lookup.md
@references/taskcluster-service-changes.md
@references/azure-spot-pricing.md
@references/spot-evictions.md

**Standalone SQL queries** (copy-paste-ready, one file per query):
- `queries/azure-task-counts.sql`
- `queries/spot-evictions.sql`
- `queries/retry-rate.sql`
- `queries/schema-sample.sql`

## Prerequisites

- Azure CLI (`az`) authenticated, with read access to the 3 CI subscriptions
- Python 3.10+
- `curl` (for Taskcluster API queries)
- Redash access (for `taskclusteretl.derived_task_summary` queries when correlating cost with tasks)

## Quick Start

### Routine: monthly cost trend
Use scheduled Cost Management exports first for `FXCI Azure DevTest`. They are already written to `safinopsdata` and avoid API throttling. See `references/cost-exports.md` for the exact storage paths, snapshot-selection rules, and download commands.

Use the Cost Management REST API only as a fallback: missing/stale/inaccessible exports, non-exported subscriptions, forecast calls, or quick ad-hoc grouped queries.

```bash
# API fallback: monthly costs by worker-pool-id, FXCI Azure DevTest
uv run scripts/query_costs.py --start 2026-01-01 --end 2026-03-31 --granularity monthly

# API fallback: compare two periods side by side
uv run scripts/query_costs.py --start 2026-01-01 --end 2026-03-31 --granularity monthly --compare-months

# API fallback: different subscription
uv run scripts/query_costs.py --start 2026-03-01 --end 2026-03-31 --subscription a30e97ab-734a-4f3b-a0e4-c51c0bff0701
```

### Diagnostic: investigating a cost increase

1. **Read methodology.md first** — picks daily-cost vs cost/task as your primary signal
2. **Use scheduled exports for FXCI DevTest** — select the latest export snapshot for each month/current month; do not sum multiple snapshots from the same month
3. **Fallback to `query_costs.py`/Cost Management API** for Trusted FXCI, TC Engineering, forecasts, or any export gap
4. **Check TC Engineering DevTest** as a control — if it didn't grow, rule out general Azure pricing event
5. **Group by Meter** in the export data, API, or Azure Portal Cost Analysis to see SKU-level breakdown
6. **Group by Resource location** if you suspect regional spot pricing changes — pair with `azure-spot-pricing.md` for the Retail Prices API
7. **Pull `derived_task_summary`** task data from Redash for the same window — see `taskcluster-task-counting.md` BigQuery section
8. **Verify pool config** via `fxci-config-lookup.md` — SKU, regions, maxCapacity, initialWeight haven't changed
9. **Check git history** of `worker-pools.yml` for cost-relevant changes during the window
10. **Check TC services repo** for cost-relevant changes — `taskcluster-service-changes.md`. Bugs in worker-manager/worker-scanner can drive cost in ways fxci-config can't explain.
11. **Check the TC issues tracker** for any bug reports filed around the cost-anomaly window — engineering may have observed symptoms before you did
12. **If pattern is broad cost/task increase across regions/pools** — investigate spot eviction (`spot-evictions.md`)
13. **If queue starvation observed alongside available capacity** — likely a TC service-level state issue; cross-check `taskcluster-service-changes.md`

### Comparing task counts for a specific push (chunk count investigations)
```bash
uv run scripts/count_push_tasks.py --date 2026.03.30
```

## Usage

### query_costs.py

Fallback tool that queries the Azure Cost Management REST API for actual costs grouped by `worker-pool-id`. Prefer scheduled exports for FXCI DevTest when they cover the requested period.

| Flag | Description |
|------|-------------|
| `--start` | Start date (YYYY-MM-DD), required |
| `--end` | End date (YYYY-MM-DD), required |
| `--granularity` | `monthly` or `daily` (default: `monthly`) |
| `--compare-months` | Show month-over-month deltas and identify top movers |
| `--top` | Number of top pools to display (default: 25) |
| `--output`, `-o` | Save raw API response as JSON |
| `--subscription` | Override subscription ID (default: FXCI Azure DevTest). Use Trusted FXCI: `a30e97ab-734a-4f3b-a0e4-c51c0bff0701`, TC Engineering: `8a205152-b25a-417f-a676-80465535a6c9` |

### count_push_tasks.py

Counts tasks per worker pool and test suite in a mozilla-central push task group. Use this for drilling into a single push (e.g. chunk count investigations). For batch analysis across many pushes/days, use the BigQuery approach in `taskcluster-task-counting.md`.

| Flag | Description |
|------|-------------|
| `--date` | Push date in TC index format: `YYYY.MM.DD` |
| `--push-index` | Which push on that date to analyze (default: 0 = first) |
| `--pool-filter` | Only show tasks matching this pool substring |

## Example Prompts

| Prompt | Action |
|--------|--------|
| "Why did Azure costs go up this month?" | Read `methodology.md`. Use scheduled exports for FXCI DevTest; use API fallback for non-exported subscriptions. Check TC Engineering as control. Group by Meter to identify SKU drivers. |
| "Show me daily costs for March" | Use the latest `fxci_daily_actual` snapshot for March if analyzing FXCI DevTest; otherwise use API fallback. |
| "Did per-task billing rate change?" | Compute volume-weighted cost/task by week using F8s v2 cost ÷ F8s v2 pool tasks. Read `methodology.md` for the cost/task amortization caveat. |
| "Which worker pools are most expensive?" | Use scheduled exports or API grouped by `worker-pool-id`, sorted by total spend. |
| "Are there new worker pools driving cost?" | Compare latest monthly export snapshots, or API fallback with `--compare-months`. |
| "Did test task volume increase?" | Pull `taskclusteretl.derived_task_summary` task counts via Redash for the period. See `taskcluster-task-counting.md`. |
| "Did spot prices change in our regions?" | Query Azure Retail Prices API for current SKU prices and effective dates. See `azure-spot-pricing.md`. |
| "Are spot evictions causing the cost rise?" | Pull eviction events from Azure Activity Log + worker-manager preemption events. See `spot-evictions.md`. |
| "Which test suites are running more on win11-64-24h2?" | `count_push_tasks.py --pool-filter win11-64-24h2` for two dates, compare suite counts. |
| "Did the VM SKU for this pool change?" | Check `worker-pools.yml` directly + git log via GitHub API. See `fxci-config-lookup.md`. |
| "Is the cost increase Azure-wide or CI-specific?" | Compare cost growth in TC Engineering DevTest vs CI subs. If TC Engineering is flat, it's CI-specific. |

## Workflow: Monthly Cost Review

1. **Query monthly costs** for the period of interest with `--compare-months`, all 3 subscriptions
   - Use scheduled exports first for FXCI DevTest
   - Use API fallback for Trusted FXCI, TC Engineering, forecasts, or export gaps
2. **Identify top movers** — pools with the largest absolute increase
3. **Check for new pools** — pools that didn't exist in the prior period
4. **Compute cost/task** for stable-volume pools to detect rate vs volume changes
5. **Correlate with task volume** — use `count_push_tasks.py` for spot checks, BigQuery for batch
6. **Drill into test suites** — if a pool's cost grew, check which test suites gained the most tasks
7. **Save report** to `~/moz_artifacts/` with findings

## Workflow: Diagnostic Investigation

For deeper cost investigations (cost rising more than volume can explain):

1. Establish a clean baseline (a normal pre-anomaly month — see `methodology.md`)
2. Compute volume-weighted daily cost/task; find the inflection date
3. Rule out, with evidence: general Azure pricing event (TC Engineering control), single-region spot spike, OS/SKU migration, regional traffic shifts, volume alone
4. Check **fxci-config** git history for changes in the inflection window
5. Check **taskcluster/taskcluster** git history for service-level changes (worker-manager, worker-scanner) in the window
6. Check the **taskcluster/taskcluster issues tracker** for bug reports filed around the window
7. Pull spot price effective dates from Retail Prices API
8. If pattern is broad cost/task increase across pools/regions: pull spot eviction telemetry from `fxci.task_runs`
9. If queue starvation observed alongside available capacity: investigate TC service state-tracking bugs
10. If structural changes (maxCapacity, initialWeight) candidate: design a rollback experiment
