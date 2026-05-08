# What the User Needs to Provide

This skill operates on Azure cost data and Taskcluster task data. Most of it can be fetched programmatically, but some pieces require user-provided inputs depending on the access level available.

## Required for any analysis

- **Authenticated Azure CLI** (`az login`) with read access to the subscription(s) being analyzed
- **Which CI subscription(s) to analyze** — IDs and scope listed in `multi-subscription.md`
- **The time window** — start and end dates for the analysis

## Required for cost-by-tag analysis

For `FXCI Azure DevTest`, use the scheduled Cost Management exports first:
- Access to `safinopsdata` / `cost-management` / `fxci_daily/`
- Either `Storage Blob Data Reader` for `--auth-mode login`, or permission for Azure CLI to query the storage account key with `--auth-mode key`
- The relevant month/time window, so the latest month-to-date snapshot can be selected correctly

If using the Cost Management REST API directly:
- The user must have **Cost Management Reader** role on the subscription
- Use API only as fallback for missing/stale/inaccessible exports, non-exported subscriptions, forecasts, or ad-hoc grouped queries

If using portal CSV exports:
- **Cost Analysis CSV export** for the time period of interest, downloaded from the Azure Portal
- Recommended grouping: by Meter, by Resource Location, or by Tag (`worker-pool-id`)
- Daily granularity is preferred for diagnostic work; monthly for routine trend reviews

## Required for SKU-level / region-level analysis

- **Daily cost export grouped by Meter** (for SKU breakdown)
- **Daily cost export grouped by Resource Location** (for regional analysis)
- The Azure Portal Cost Analysis UI only supports one group-by at a time — for combinations, filter on one dimension and group by the other (e.g., Filter Meter = "F8s v2 Spot", Group by Resource Location)

## Required for cost ↔ task correlation

If correlating Azure cost with Taskcluster task volume:
- **Redash access** to query `taskclusteretl.derived_task_summary` (BigQuery-backed)
- The Azure-only `workerGroup NOT LIKE` filter (see `taskcluster-task-counting.md`)
- Or a CSV export of that query for the relevant time window

## Required for spot pricing investigation

- No special access required — uses the public Azure Retail Prices API
- The user does NOT need to provide pricing data; the skill can fetch current prices

## Required for spot eviction investigation

- **Azure Activity Log access** (Reader role on the subscription is usually sufficient)
- OR a separately collected eviction event log — by date, region, and SKU
- AND/OR access to **TC worker-manager preemption logs** — typically requires asking the TC engineering team

## Required for fxci-config verification

- No special access — `mozilla-releng/fxci-config` is a public repository
- The user does NOT need to provide pool config; the skill fetches `worker-pools.yml` directly

## Required for diagnostic investigations

In addition to the above:
- A clean **baseline period** that pre-dates the change being investigated (typically the month before any anomalous events)
- The user should indicate **what changed** (if known) — load surge, config change, suspected events — so the analysis can be scoped
- Approximate **dates of any known config changes**, releases, or incidents in the window

## Optional but valuable

- **VM-level Azure Cost Details export** — only available with Billing Reader role on the subscription. This is the most detailed cost view (per-instance hourly billing) and would conclusively answer many diagnostic questions. Often unavailable to engineering staff — may require a request through finance/admin.
- **Microsoft account team / FastTrack engineer contact** — for historical spot price data not available via the Retail Prices API
- **Looker dashboard access** — if the org has a dashboard for total cloud costs (different orgs vary)

## What the skill does NOT need

- The skill does NOT need credentials for individual VMs.
- The skill does NOT need access to Mozilla-internal billing dashboards beyond what's listed above.
