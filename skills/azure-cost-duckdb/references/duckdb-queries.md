# DuckDB Query Patterns

The helper creates two views:

```sql
azure_cost       -- all local Parquet rows
azure_cost_files -- row counts by source filename
```

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

Top tagged worker pools when `Tags` is a JSON-like string:

```sql
SELECT
  coalesce(json_extract_string(Tags, '$."worker-pool-id"'), '(untagged)')
    AS worker_pool_id,
  round(sum(CostInBillingCurrency), 2) AS cost
FROM azure_cost
GROUP BY 1
ORDER BY cost DESC
LIMIT 50;
```

If a malformed CSV diagnostic run leaves non-JSON tag text in the view, guard
the extraction:

```sql
CASE
  WHEN Tags IS NULL OR Tags = '' THEN '(untagged)'
  WHEN json_valid(Tags) THEN coalesce(json_extract_string(Tags, '$."worker-pool-id"'), '(untagged)')
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
