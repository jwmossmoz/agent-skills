# Multi-Subscription Analysis

CI costs span multiple Azure subscriptions. Don't analyze just one — the relative behavior across subscriptions is itself diagnostic.

## The 3 CI subscriptions

| Subscription | ID | What it contains | Trust level |
|---|---|---|---|
| FXCI Azure DevTest | `108d46d5-fe9b-4850-9a7d-8c914aa6c1f0` | Test workers + level-1 (try, untrusted) build workers | Level 1 |
| Trusted FXCI Azure DevTest | `a30e97ab-734a-4f3b-a0e4-c51c0bff0701` | Level-3 build workers (autoland, beta, ESR, release) | Level 3 |
| Taskcluster Engineering DevTest | `8a205152-b25a-417f-a676-80465535a6c9` | TC infra/engineering VMs, not CI worker pools | Engineering |

## Trust level mapping

The same trust split exists on both Azure and GCP infrastructure:
- **Level 1** = try/untrusted ↔ `FXCI Azure DevTest` ↔ `fxci-production-level1-workers` (GCP)
- **Level 3** = production binaries (autoland/beta/ESR/release) ↔ `Trusted FXCI Azure DevTest` ↔ `fxci-production-level3-workers` (GCP)

On both clouds, level-1 (test/try) typically costs more in absolute terms than level-3 (production builds) — the design principle is "we test more than we build."

## Why use TC Engineering as a control variable

`Taskcluster Engineering DevTest` runs in the same Azure tenant but on different infrastructure (no CI worker pools). This makes it a useful **control** for ruling out Azure-wide changes.

If a cost increase appears in the CI subscriptions but TC Engineering's costs are stable, that **rules out** a general Azure pricing event — if Azure had raised prices subscription-wide, TC Engineering would also show large growth.

Conversely, if both CI subs and TC Engineering rise together, the cause is likely Azure-wide and external rather than CI-specific.

## Relative scale of the 3 subscriptions

When CI is running normally, the rough ranking is:
- **FXCI DevTest** is the largest (test workers dominate volume and therefore cost)
- **Trusted FXCI** is much smaller (only production binary builds — beta, ESR, release, autoland)
- **TC Engineering** is smallest (infra VMs, not CI worker pools)

Watch for shifts in the relative split: if Trusted FXCI grows as a share of total CI cost, level-3 build activity (release/beta cycles) is busy. If TC Engineering grows in absolute terms, that suggests platform/infra changes rather than CI workload.

## Querying across all 3 subscriptions

### Export-first rule
Use scheduled exports first for `FXCI Azure DevTest`. They are already written to `safinopsdata/cost-management/fxci_daily`, and they avoid Cost Management API throttling. Select the latest month-to-date snapshot for each requested month; do not sum all daily snapshots within a month. See `cost-exports.md`.

As of 2026-05-08, `Trusted FXCI Azure DevTest` and `Taskcluster Engineering DevTest` have no scheduled Cost Management exports configured, so use the API or user-provided portal CSVs for those two subscriptions.

### Cost Management API
Use the query API as the fallback path. It doesn't aggregate across subscriptions in one call. Make one call per non-exported subscription and sum:

```python
SUBS = {
    'FXCI DevTest':    '108d46d5-fe9b-4850-9a7d-8c914aa6c1f0',
    'Trusted FXCI':    'a30e97ab-734a-4f3b-a0e4-c51c0bff0701',
    'TC Engineering':  '8a205152-b25a-417f-a676-80465535a6c9',
}

for label, sub_id in SUBS.items():
    run_query(sub_id, ...)
```

Use the `--subscription` flag on `query_costs.py` to override. Pace calls because Cost Management rate limits per scope and tenant.

### Cost exports
Only `FXCI Azure DevTest` has scheduled cost exports configured. The other two subs require ad-hoc exports from the Azure Portal Cost Analysis or API fallback.

### CSV exports from the portal
For diagnostic work, the portal can export per-subscription daily SKU breakdowns:
- Cost Analysis → Group by Meter → Set time range → Download
- Repeat for each subscription

## What to compare

### Same SKU across subscriptions
Be careful comparing different SKUs across subs. F8s v2 Spot is used by gecko-t test pools (FXCI DevTest). D32ads v5 Spot is used by gecko-3/b-win2022 build workers (Trusted FXCI). Different SKUs have different cost profiles — compare like-for-like.

### Cost trend by subscription
A change appearing only in one sub points to something pool-specific or workload-specific. A change appearing in all three points to Azure-wide or TC-platform-wide.

### Cost spread proportion
If Trusted FXCI grows from ~7% to ~15% of total CI cost, level-3 (production) work has surged or level-1 has dropped. Trace which.

## Excluded from CI scope

Other Azure subscriptions in the tenant should NOT be aggregated for CI cost analysis:
- Mozilla Infrastructure Security
- Firefox Non-CI DevTest (despite the name, no longer CI)
- Mozilla 0DIN

These run unrelated workloads. Their small contribution would dilute any analysis.
