# Azure Cost Analysis

Analyze FXCI Azure DevTest subscription costs by worker-pool-id tag, then
correlate cost changes with Taskcluster task volume.

## Prerequisites

1. **Azure CLI** authenticated (`az login`)
2. **Python 3.10+**
3. **uv** for running scripts

## Quick Start

```bash
# Monthly breakdown by worker pool
uv run scripts/query_costs.py --start 2026-01-01 --end 2026-03-31 --granularity monthly --compare-months

# Daily breakdown for one month
uv run scripts/query_costs.py --start 2026-03-01 --end 2026-03-31 --granularity daily

# Compare task counts between two push dates
uv run scripts/count_push_tasks.py --date 2026.01.15
uv run scripts/count_push_tasks.py --date 2026.03.30
```

## Where Cost Data Lives

Cost exports for the FXCI Azure DevTest subscription are configured as:

| Export | Type | Storage |
|--------|------|---------|
| `fxci_daily_actual` | ActualCost | `safinopsdata` / `cost-management` / `fxci_daily/` |
| `fxci_daily_amortized` | AmortizedCost | same storage account |

The exports produce large CSV files (200MB+ per day snapshot, split across
multiple parts). For analysis, querying the Cost Management REST API directly
is far more practical — it aggregates server-side.

Other subscriptions in the tenant (Taskcluster Engineering DevTest, Trusted
FXCI, Mozilla Infrastructure Security, Firefox Non-CI DevTest, Mozilla 0DIN)
have **no cost exports configured**.

To list exports across subscriptions:

```bash
for sub in "108d46d5-..." "8a205152-..." "a30e97ab-..."; do
  az costmanagement export list --scope "subscriptions/$sub" --output table
done
```

## Key Concepts

### worker-pool-id Tag

Azure VMs provisioned by Taskcluster's worker-manager are tagged with
`worker-pool-id` (e.g., `gecko-t/win11-64-24h2`). This tag is the primary
dimension for attributing CI costs to specific workloads.

Common pool patterns:
- `gecko-t/win11-64-24h2` — Windows 11 24H2 test workers
- `gecko-t/win11-64-24h2-gpu` — GPU-enabled variant
- `gecko-t/win11-64-25h2` — Windows 11 25H2 test workers (newer)
- `gecko-1/b-win2022` — Windows build workers
- `comm-t/win11-64-24h2` — Thunderbird test workers
- `enterprise-t/win11-64-24h2` — Enterprise test workers
- `(untagged)` — resources without the tag (storage, networking, etc.)

### Cost Drivers

Azure VM costs scale with:
1. **Number of tasks** — more tasks = more VMs provisioned
2. **Task duration** — longer tasks keep VMs alive longer
3. **VM SKU** — GPU SKUs cost more than standard compute
4. **New pools** — additive spend when new pools come online before old ones wind down
