# DuckDB Query Patterns

The helper creates two views:

```sql
azure_cost       -- all local Parquet rows
azure_cost_files -- row counts by source filename
```

When the export has a tag column, `azure_cost` also exposes a derived
`worker_pool_id` column. Azure tags the same FXCI worker pool two ways:
Taskcluster-created VMs use `worker-pool-id` (hyphens) and Terraform-managed
infra (for example dedicated hosts) uses `worker_pool_id` (underscores). The
derived column coalesces both, so `GROUP BY worker_pool_id` surfaces every
resource for a pool. Filtering by the raw hyphen tag alone drops the
underscore-tagged resources into `(untagged)`.

The `azure_cost` view is backed by:

```sql
read_parquet(
  '<data-root>/**/*.parquet',
  hive_partitioning = true,
  union_by_name = true,
  filename = true
)
```

For CSV exports, the helper uses `read_csv(..., union_by_name = true,
filename = true, dateformat = '%m/%d/%Y', max_line_size = 8388608)`.

Run `schema` first because Azure export column names vary by dataset and
schema version:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  schema --config ~/.config/azure-cost-duckdb.toml
```

## Cache Sanity

Rows by source file:

```sql
SELECT *
FROM azure_cost_files
ORDER BY filename;
```

Available date-like columns:

```sql
DESCRIBE azure_cost;
```

## FOCUS Examples

Monthly effective cost:

```sql
SELECT
  date_trunc('month', ChargePeriodStart) AS month,
  round(sum(EffectiveCost), 2) AS effective_cost
FROM azure_cost
GROUP BY 1
ORDER BY 1;
```

Top services:

```sql
SELECT
  ServiceName,
  round(sum(EffectiveCost), 2) AS effective_cost
FROM azure_cost
GROUP BY 1
ORDER BY effective_cost DESC
LIMIT 25;
```

Daily cost for one subaccount or subscription:

```sql
SELECT
  CAST(ChargePeriodStart AS DATE) AS usage_day,
  round(sum(EffectiveCost), 2) AS effective_cost
FROM azure_cost
WHERE SubAccountId = '<subscription-id>'
GROUP BY 1
ORDER BY 1;
```

Top resources:

```sql
SELECT
  ResourceId,
  ResourceName,
  ServiceName,
  round(sum(EffectiveCost), 2) AS effective_cost
FROM azure_cost
GROUP BY 1, 2, 3
ORDER BY effective_cost DESC
LIMIT 50;
```

## Azure-Native Cost Detail Examples

Monthly cost, common actual/amortized export columns:

```sql
SELECT
  date_trunc('month', CAST(UsageDate AS DATE)) AS month,
  round(sum(CostInBillingCurrency), 2) AS cost
FROM azure_cost
GROUP BY 1
ORDER BY 1;
```

Top meter categories:

```sql
SELECT
  MeterCategory,
  ResourceLocation,
  round(sum(CostInBillingCurrency), 2) AS cost
FROM azure_cost
GROUP BY 1, 2
ORDER BY cost DESC
LIMIT 50;
```

Top worker pools using the derived column (covers both tag spellings):

```sql
SELECT
  coalesce(worker_pool_id, '(untagged)') AS worker_pool_id,
  round(sum(CostInBillingCurrency), 2) AS cost
FROM azure_cost
GROUP BY 1
ORDER BY cost DESC
LIMIT 50;
```

The derived column already JSON-guards the tag value, so malformed CSV
diagnostic rows return `NULL` rather than raising. If you need to extract a
different tag key by hand, coalesce both spellings and guard the JSON:

```sql
CASE
  WHEN tags IS NULL OR tags = '' THEN '(untagged)'
  WHEN json_valid(tags) THEN coalesce(
    json_extract_string(tags, '$."worker-pool-id"'),
    json_extract_string(tags, '$."worker_pool_id"'),
    '(untagged)')
  ELSE '(malformed tags)'
END
```

## Exporting Results

The helper can write CSV directly:

```bash
uv run ~/.claude/skills/azure-cost-duckdb/scripts/azure_cost_duckdb.py \
  query --config ~/.config/azure-cost-duckdb.toml --format csv \
  --sql "SELECT ServiceName, sum(EffectiveCost) AS cost FROM azure_cost GROUP BY 1" \
  > ~/moz_artifacts/azure-cost/service-costs.csv
```

For larger derived datasets, use DuckDB `COPY`:

```sql
COPY (
  SELECT ServiceName, sum(EffectiveCost) AS cost
  FROM azure_cost
  GROUP BY 1
) TO '~/moz_artifacts/azure-cost/service-costs.parquet' (FORMAT parquet);
```
