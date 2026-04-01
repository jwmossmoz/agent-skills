---
name: azure-cost-analysis
description: >
  Analyze FXCI Azure cost trends by worker-pool-id tag using the Azure Cost
  Management REST API. Use when investigating Azure spend increases, comparing
  monthly costs across worker pools, identifying new or growing pools, or
  correlating cost changes with Taskcluster task volume. Triggers on "azure
  cost", "cost increase", "cost analysis", "worker pool cost", "FXCI spend",
  "cloud spend", "cost trend", "why did cost go up", "cost by worker pool".
---

# Azure Cost Analysis

Analyze FXCI Azure DevTest subscription costs grouped by the `worker-pool-id`
tag. Correlate cost changes with Taskcluster task volume per worker pool.

## Knowledge References
@references/README.md
@references/cost-management-api.md
@references/taskcluster-task-counting.md

## Prerequisites

- Azure CLI (`az`) authenticated with access to the FXCI Azure DevTest subscription
- Python 3.10+
- `curl` (for Taskcluster API queries)

## Quick Start

```bash
# Monthly costs by worker-pool-id for a date range
uv run scripts/query_costs.py --start 2026-01-01 --end 2026-03-31 --granularity monthly

# Daily costs for a single month
uv run scripts/query_costs.py --start 2026-03-01 --end 2026-03-31 --granularity daily

# Compare two periods side by side
uv run scripts/query_costs.py --start 2026-01-01 --end 2026-03-31 --granularity monthly --compare-months

# Save raw JSON for further analysis
uv run scripts/query_costs.py --start 2026-03-01 --end 2026-03-31 --granularity daily --output ~/moz_artifacts/march-costs.json

# Count tasks per worker pool for a specific push (to explain cost changes)
uv run scripts/count_push_tasks.py --date 2026.03.30
```

## Usage

### query_costs.py

Queries the Azure Cost Management REST API for actual costs grouped by `worker-pool-id`.

| Flag | Description |
|------|-------------|
| `--start` | Start date (YYYY-MM-DD), required |
| `--end` | End date (YYYY-MM-DD), required |
| `--granularity` | `monthly` or `daily` (default: `monthly`) |
| `--compare-months` | Show month-over-month deltas and identify top movers |
| `--top` | Number of top pools to display (default: 25) |
| `--output`, `-o` | Save raw API response as JSON |
| `--subscription` | Override subscription ID (default: FXCI Azure DevTest) |

### count_push_tasks.py

Counts tasks per worker pool and test suite in a mozilla-central push task group.

| Flag | Description |
|------|-------------|
| `--date` | Push date in TC index format: `YYYY.MM.DD` |
| `--push-index` | Which push on that date to analyze (default: 0 = first) |
| `--pool-filter` | Only show tasks matching this pool substring |

## Example Prompts

| Prompt | Action |
|--------|--------|
| "Why did Azure costs go up this month?" | Run `query_costs.py` comparing current month to prior month with `--compare-months` |
| "Show me daily costs for March" | `query_costs.py --start 2026-03-01 --end 2026-03-31 --granularity daily` |
| "Which worker pools are most expensive?" | `query_costs.py` for the current month, sorted by total spend |
| "Are there new worker pools driving cost?" | `query_costs.py --compare-months`, look at the "new pools" section |
| "Did test task volume increase?" | `count_push_tasks.py` for a recent date vs an older date, compare task counts per pool |
| "Which test suites are running more on win11-64-24h2?" | `count_push_tasks.py --pool-filter win11-64-24h2` for two dates, compare suite counts |

## Workflow: Monthly Cost Review

1. **Query monthly costs** for the period of interest with `--compare-months`
2. **Identify top movers** — pools with the largest absolute increase
3. **Check for new pools** — pools that didn't exist in the prior period
4. **Correlate with task volume** — use `count_push_tasks.py` to compare task counts per push for high-cost pools
5. **Drill into test suites** — if a pool's cost grew, check which test suites gained the most tasks
6. **Save report** to `~/moz_artifacts/` with findings

## API Reference
@references/cost-management-api.md

## Taskcluster Task Counting
@references/taskcluster-task-counting.md
