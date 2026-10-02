# Azure Cost Export Notes

Use this reference when setting up or troubleshooting the Azure side of the
local cache. Keep real export data and credentials outside the skill.

## Export Shape

Azure Cost Management exports write files to Blob Storage under a hierarchy
like:

```text
<container>/<storage-directory>/<export-name>/<YYYYMMDD-YYYYMMDD>/<run-id>/
```

Each run includes partition files and a manifest. Query all partition files
for the period. Do not hardcode a partition file name.

For CSV exports, compare the manifest `dataRowCount` with local validation
after download. Interrupted transfers can leave a file with the right byte
length but bad contents, such as NUL bytes replacing rows. Re-download any
partition whose physical row count does not match its manifest entry.

## Preferred Dataset

`costctl lake` supports Azure-native **actual cost** exports only. `azure_cost`, the saved
questions, and the documented SQL use that schema (`date`, `meterCategory`, `costInUsd`, `tags`).
Adding a FOCUS or amortized export to `[azure].exports` would mix schemas in one view.

## Preferred File Format

Prefer:

```text
Format: Parquet
Compression: Snappy
Partitioning: enabled
```

Cost and usage details exports support Parquet and Snappy compression. DuckDB
can query Parquet directly. Older or already-configured exports may be CSV;
the helper supports `*.csv` and `*.csv.gz` with Azure's common `%m/%d/%Y`
date format.

## Download Auth

Use Microsoft Entra auth when possible:

```bash
az login
az storage blob download-batch \
  --account-name <storage-account> \
  --source <container> \
  --destination /tmp/azure-export-raw \
  --auth-mode login \
  --pattern '<export-prefix>/*.parquet' \
  --overwrite true
```

Avoid storage keys and SAS tokens unless needed. If they are needed, keep them
in environment variables or a private config file outside git.

## Refresh Semantics

Current billing-period charges can change until the invoice closes. Daily
exports commonly overwrite the latest current-period run. Refresh current
month data before analysis, and treat closed months as the more stable
baseline.

`costctl lake sync` already handles this: per export and month it resolves the
latest run, downloads only that run, replaces the month's Parquet file, and
skips months whose latest run is already imported (`parquet/azure_cost/_runs.json`).
The rest of this section applies to manual `costctl lake azure sync` runs.

Monthly export folders can contain multiple run snapshots. Use
`sync --latest-run` when the prefix points at a month directory so the helper
downloads only the latest run and avoids double-counting old snapshots.

`--latest-run` is prefix-depth sensitive. Point `--prefix` at a single
date-range directory (`<export-name>/<YYYYMMDD-YYYYMMDD>`) so it resolves to
that month's latest run. A shallower prefix (`<export-name>` alone) resolves to
the export root and pulls *every* run of *every* month — a large, duplicated
download.

Double-counting happens at the query layer, not just on download: the DuckDB
view globs every `*.csv*` under `data_root` and UNIONs them. Each daily export
run is a *full* month-to-date snapshot, so two snapshots in one `data_root`
double the rows. Keep each full-month snapshot in its own clean `data_root`
(e.g. a per-month folder via `--data-root`/`--database`). `--latest-run` only
avoids doubling if the destination does not already hold an older run; if it
does, clear the old run directory first or sync into a fresh folder.

The latest current-month snapshot can still be incomplete for the current day.
Use the max usage date from the local query and the export run timestamp when
describing month-to-date results.

## Reconciling Unbilled Resources

The cache can only show what Azure rated. A resource can be deployed and
running yet produce no cost row, so it is absent from the export entirely — not
present at $0. Treating "absent from the cache" as "free" is wrong.

The cause seen in practice: a SKU is deployable in a region but Azure has no
price meter for it there. A `NVadsA10v5_Type1` dedicated host in `westus3`
provisioned fine, but Azure publishes that Dedicated Host meter only in
`eastus2`, `westus2`, `germanywestcentral`, and `japaneast` (≈$7.17/hour), not
`westus3`. With no regional meter the consumption pipeline emits nothing, so
the host shows no rows at any Cost Management scope (actual and amortized) while
the rest of the subscription bills normally and stays current.

Before reporting that a known resource has zero cost, reconcile across three
sources:

1. Confirm the resource exists and is allocated:
   `az vm host show -g <rg> --host-group <hg> --name <host>` (or
   `az resource list -g <rg>`).
2. Confirm Cost Management has no row at the resource scope, not just the cache:
   query the `ResourceId` at subscription scope with `ActualCost` and
   `AmortizedCost`. Empty rows plus fresh data for other resources means Azure
   rated nothing, not that the cost is zero.
3. Confirm whether a price meter even exists for that SKU and region with the
   Retail Prices API:

   ```bash
   curl -s "https://prices.azure.com/api/retail/prices?\$filter=contains(productName,'NVadsA10v5')%20and%20contains(productName,'Dedicated')" \
     | python3 -c "import sys,json;[print(i['armRegionName'],i['retailPrice'],i['type']) for i in json.load(sys.stdin)['Items']]"
   ```

   A SKU present in some regions but missing the target region is the tell. An
   unbilled resource can be back-rated later if Azure publishes the meter, so
   flag it rather than recording it as free.

## Historical Backfill

The Azure portal supports limited historical export reruns. For older history,
use the Cost Management Exports REST API to execute export jobs for historical
periods, then sync the resulting Blob Storage files locally.

## Source Docs

- Cost Management exports:
  https://learn.microsoft.com/azure/cost-management-billing/costs/tutorial-improved-exports
- Cost details ingestion:
  https://learn.microsoft.com/azure/cost-management-billing/automate/usage-details-best-practices
- Blob downloads with Azure CLI:
  https://learn.microsoft.com/cli/azure/storage/blob
- Azure CLI Blob auth:
  https://learn.microsoft.com/azure/storage/blobs/authorize-data-operations-cli
