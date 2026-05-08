# Cost Exports — Export-First Workflow

Use scheduled Cost Management exports before querying the API when analyzing `FXCI Azure DevTest`. The exports already exist, avoid Cost Management API throttling, and provide a stable audit trail.

## Current scheduled exports

| Export | Subscription | Type | Storage |
|---|---|---|---|
| `fxci_daily_actual` | FXCI Azure DevTest (`108d46d5-fe9b-4850-9a7d-8c914aa6c1f0`) | ActualCost | `safinopsdata` / `cost-management` / `fxci_daily/` |
| `fxci_daily_amortized` | FXCI Azure DevTest (`108d46d5-fe9b-4850-9a7d-8c914aa6c1f0`) | AmortizedCost | same storage account |

As of 2026-05-08, `Trusted FXCI Azure DevTest` and `Taskcluster Engineering DevTest` do not have scheduled Cost Management exports configured. Use the Cost Management API or a user-provided portal CSV export for those subscriptions.

## Important snapshot rule

These exports are daily **month-to-date snapshots**. Each run folder contains the cumulative month-to-date data as of that run.

Do **not** sum every run under a month prefix. That double counts the same month repeatedly.

Instead:
- For a completed month, select the latest run under `YYYYMM01-YYYYMMDD/`.
- For the current month, select the latest available run under the current month prefix.
- Download the CSV part files listed by that run's `_manifest.json`.
- Compare equivalent snapshot types: `ActualCost` vs `ActualCost`, or `AmortizedCost` vs `AmortizedCost`.

Example layout:

```text
fxci_daily/fxci_daily_actual/20260501-20260531/202605071631/<run-id>/
  000001.csv
  000002.csv
  ...
  _manifest.json
```

## Listing exports and snapshots

List configured exports:

```bash
for sub in "108d46d5-fe9b-4850-9a7d-8c914aa6c1f0" \
           "8a205152-b25a-417f-a676-80465535a6c9" \
           "a30e97ab-734a-4f3b-a0e4-c51c0bff0701"; do
  az costmanagement export list --scope "subscriptions/$sub" --output table
done
```

List snapshots for a month:

```bash
az storage blob list \
  --account-name safinopsdata \
  --container-name cost-management \
  --prefix fxci_daily/fxci_daily_actual/20260501-20260531/ \
  --auth-mode key \
  --query '[].name' \
  --output tsv
```

`--auth-mode login` may fail without `Storage Blob Data Reader`. `--auth-mode key` can work when the user has permission to list the storage account keys. Do not print, persist, or copy the key; let Azure CLI handle it.

## Downloading the selected run

After selecting the latest run prefix, download only that run:

```bash
RUN_PREFIX="fxci_daily/fxci_daily_actual/20260501-20260531/202605071631/<run-id>"
DEST="$HOME/moz_artifacts/azure-cost/202605-fxci-actual"

az storage blob download-batch \
  --account-name safinopsdata \
  --destination "$DEST" \
  --source cost-management \
  --pattern "$RUN_PREFIX/*" \
  --auth-mode key
```

Use `_manifest.json` as the audit source for which CSV parts belong to the snapshot. If the month has not completed, record the run timestamp in the report so readers know the current-month cutoff.

## When to fall back to API

Use the Cost Management REST API when:

- The requested subscription has no scheduled export (`Trusted FXCI`, `TC Engineering`).
- The export is missing, stale, or incomplete for the requested period.
- Storage access is unavailable and the user does not provide downloaded CSVs.
- You need Azure forecast data. Forecast is API-only and cannot group by worker pool.
- You need a quick ad-hoc grouping and API throttling risk is acceptable.

When using the API fallback, include the `ClientType: GitHubCopilotForAzure` header and pace calls per subscription because Cost Management throttles aggressively.

## Analysis notes

- Prefer `ActualCost` for spend comparisons and forecasts.
- Use `AmortizedCost` only when explicitly analyzing reservations/savings-plan allocation.
- The export includes richer raw columns than the grouped query API; use structured CSV parsing and group locally by `worker-pool-id`, `Meter`, `ResourceLocation`, `ServiceName`, or `ResourceId`.
- Save downloaded manifests, raw CSVs or derived summaries, and the final report under `~/moz_artifacts/` for auditability.
