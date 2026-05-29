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

Prefer Cost and usage details in FOCUS format when you want a stable FinOps
shape that combines actual and amortized concepts. Use actual or amortized
exports when you need an Azure-native schema matching existing reports.

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
  --destination ~/moz_artifacts/azure-cost/raw \
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

Monthly export folders can contain multiple run snapshots. Use
`sync --latest-run` when the prefix points at a month directory so the helper
downloads only the latest run and avoids double-counting old snapshots.

The latest current-month snapshot can still be incomplete for the current day.
Use the max usage date from the local query and the export run timestamp when
describing month-to-date results.

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
