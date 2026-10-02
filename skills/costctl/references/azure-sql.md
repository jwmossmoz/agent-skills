# Azure SQL Notes (`azure_cost`)

`azure_cost` holds every imported Azure actual-cost export row (all months, all configured exports).
Column names follow the export schema; check with `costctl lake sql "DESCRIBE azure_cost"`.

Common columns: `date`, `SubscriptionName`, `ResourceGroup`, `ResourceId`, `meterCategory`,
`meterSubCategory`, `meterName`, `pricingModel` (`Spot`/`OnDemand`), `resourceLocation`, `quantity`,
`costInUsd`, `costInBillingCurrency`, `tags`, `additionalInfo` (`$.ServiceType` = VM SKU).

## worker_pool_id

Derived from tags. Azure tags a pool two ways: Taskcluster-created VMs use `worker-pool-id`,
Terraform-managed infra (dedicated hosts etc.) uses `worker_pool_id`. The column coalesces both,
so `GROUP BY worker_pool_id` sees every resource. NULL = untagged (often disks, NICs, network).
Older pools may be tagged without the provisioner prefix (`win11-64-24h2` vs `gecko-t/win11-64-24h2`).

## Examples

```sql
-- Monthly cost by meter category
SELECT date_trunc('month', date) AS month, meterCategory, round(sum(costInUsd)) AS usd
FROM azure_cost GROUP BY ALL ORDER BY month, usd DESC;

-- Top resources
SELECT ResourceId, meterCategory, round(sum(costInUsd), 2) AS usd
FROM azure_cost GROUP BY ALL ORDER BY usd DESC LIMIT 50;

-- Another tag key, JSON-guarded
SELECT CASE WHEN json_valid(tags) THEN json_extract_string(tags, '$."created-by"') END AS created_by,
       round(sum(costInUsd)) AS usd
FROM azure_cost GROUP BY 1 ORDER BY usd DESC;

-- Export a result
COPY (SELECT worker_pool_id, sum(costInUsd) AS usd FROM azure_cost GROUP BY 1)
TO '/tmp/azure-by-pool.csv' (HEADER);
```
