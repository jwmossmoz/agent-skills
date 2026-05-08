# Azure Cost Analysis

Analyze FXCI Azure subscription costs across multiple dimensions, then correlate cost changes with Taskcluster task volume. Investigate cost increases — distinguish volume-driven changes from rate changes, identify pricing/SKU/region/eviction effects.

## Prerequisites

1. **Azure CLI** authenticated (`az login`)
2. **Python 3.10+**
3. **uv** for running scripts
4. **Redash access** for `taskclusteretl.derived_task_summary` queries (BigQuery)

## Standalone queries

For copy-paste-ready BigQuery SQL (task counts, eviction rates, retry rates, schema samples), see the `../queries/` directory. Each .sql file has inline documentation linking back to the relevant reference below.

## Reference docs

Read these in priority order when investigating a cost anomaly:

| Reference | Read when |
|---|---|
| `user-inputs.md` | **Read before starting.** What the user needs to provide depending on access level and investigation scope. |
| `methodology.md` | **Read first when analyzing.** Daily cost vs cost/task signals, baseline selection, common pitfalls. |
| `cost-exports.md` | **Use first for FXCI DevTest.** Scheduled export paths, snapshot rules, and API fallback criteria. |
| `cost-dimensions.md` | You need to slice by SKU, region, or service in addition to worker-pool-id. |
| `multi-subscription.md` | Investigating cost change across all 3 CI subs (FXCI DevTest, Trusted FXCI, TC Engineering). |
| `cost-management-api.md` | API fallback reference for the query endpoint. |
| `taskcluster-task-counting.md` | Counting tasks per pool — TC API for one push, BigQuery for batch analysis. |
| `fxci-config-lookup.md` | Verifying VM SKU/region/weight for a pool, checking git history for cost-relevant changes. |
| `taskcluster-service-changes.md` | Checking TC service code (worker-manager, worker-scanner) for bugs/changes affecting cost. |
| `azure-spot-pricing.md` | Investigating whether spot price changes contributed to a cost increase. |
| `spot-evictions.md` | Investigating whether spot eviction rate changes contributed (broad cost/task increases). |

## Quick start

```bash
# API fallback: monthly breakdown by worker pool, FXCI Azure DevTest only
uv run scripts/query_costs.py --start 2026-01-01 --end 2026-03-31 --granularity monthly --compare-months

# API fallback: daily breakdown for one month
uv run scripts/query_costs.py --start 2026-03-01 --end 2026-03-31 --granularity daily

# Compare task counts between two push dates (TC API, single push)
uv run scripts/count_push_tasks.py --date 2026.01.15
uv run scripts/count_push_tasks.py --date 2026.03.30
```

## Scope

This skill covers **Azure** CI cost analysis. The scope spans all 3 CI subscriptions, multiple cost dimensions (worker-pool-id tag, SKU/Meter, Resource Location, Service), and correlation with task data from Taskcluster.

Out of scope:
- GCP costs (separate analysis path via `fxci.worker_costs` and `fxci.task_run_costs` in BigQuery)
- Subscriptions outside CI (Mozilla Infrastructure Security, Firefox Non-CI DevTest, etc.)

## Where Cost Data Lives

### Cost exports

| Export | Subscription | Type | Storage |
|--------|------|------|---------|
| `fxci_daily_actual` | FXCI Azure DevTest | ActualCost | `safinopsdata` / `cost-management` / `fxci_daily/` |
| `fxci_daily_amortized` | FXCI Azure DevTest | AmortizedCost | same storage account |

Use these scheduled exports first for FXCI DevTest cost analysis. They are daily month-to-date snapshots; select the latest run for the target month/current month and do not sum multiple runs from the same month. See `cost-exports.md`.

The `Trusted FXCI Azure DevTest` and `Taskcluster Engineering DevTest` subscriptions have **no cost exports configured** as of 2026-05-08. For those subscriptions, use the Cost Management REST API or the Azure Portal Cost Analysis "Download" button.

To list exports across subscriptions:

```bash
for sub in "108d46d5-fe9b-4850-9a7d-8c914aa6c1f0" \
           "8a205152-b25a-417f-a676-80465535a6c9" \
           "a30e97ab-734a-4f3b-a0e4-c51c0bff0701"; do
  az costmanagement export list --scope "subscriptions/$sub" --output table
done
```

## Key Concepts

### worker-pool-id Tag

Azure VMs provisioned by Taskcluster's worker-manager are tagged with `worker-pool-id` (e.g., `gecko-t/win11-64-24h2`). This tag is the primary dimension for attributing CI costs to specific workloads.

The tag value matches `provisionerId/workerType` in Taskcluster — this is the join key for correlating Azure cost data with TC task data.

Common pool patterns:
- `gecko-t/win11-64-24h2` — Windows 11 24H2 test workers (Standard_F8s_v2)
- `gecko-t/win11-64-24h2-gpu` — GPU-enabled variant (Standard_NV12s_v3)
- `gecko-t/win11-64-25h2` — Windows 11 25H2 test workers (Standard_F8s_v2 — same SKU as 24h2)
- `gecko-t/win11-64-25h2-gpu` — 25H2 GPU variant (Standard_NV12ads_A10_v5 — different SKU than 24h2-gpu)
- `gecko-1/b-win2022` — Windows level-1 build workers (Standard_D32ads_v5)
- `gecko-3/b-win2022` — Windows level-3 build workers (Standard_D32ads_v5)
- `comm-t/win11-64-24h2` — Thunderbird test workers
- `enterprise-t/win11-64-24h2` — Enterprise test workers
- `(untagged)` — resources without the tag (storage, networking, etc.)

Verify SKU and region assignments via `mozilla-releng/fxci-config/worker-pools.yml` — see `fxci-config-lookup.md`.

### Cost Drivers

Azure VM costs scale with multiple factors. When investigating an increase, enumerate which apply:

1. **Number of tasks** — more tasks = more VMs provisioned (volume)
2. **Task duration** — longer tasks keep VMs alive longer
3. **VM SKU** — SKU pricing varies (GPU > general-purpose > burstable)
4. **Spot price** — for spot VMs, hourly rate fluctuates with Azure capacity demand
5. **Spot eviction rate** — evicted VMs bill for time used but produce no completed task — increases cost-per-task without rate change
6. **VM lifecycle overhead** — provisioning, idle (queueInactivityTimeout), teardown all count
7. **maxCapacity ceiling** — higher allows more concurrent VMs, potentially more idle billing
8. **New pools** — additive spend when new pools come online before old ones wind down
9. **Region pricing** — same SKU costs differ by region; spot prices especially vary

Different mechanisms produce different cost-vs-task patterns. Use `methodology.md` to choose which signal to look at.
