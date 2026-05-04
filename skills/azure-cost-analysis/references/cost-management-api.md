# Azure Cost Management REST API

The `az costmanagement` CLI only supports exports, not queries. Use `az rest`
to call the Cost Management Query API directly.

## Endpoint

```
POST https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.CostManagement/query?api-version=2023-11-01
```

## Request Body

```json
{
  "type": "ActualCost",
  "timeframe": "Custom",
  "timePeriod": {
    "from": "2026-01-01",
    "to": "2026-03-31"
  },
  "dataset": {
    "granularity": "Monthly",
    "aggregation": {
      "totalCost": {
        "name": "Cost",
        "function": "Sum"
      }
    },
    "grouping": [
      {
        "type": "TagKey",
        "name": "worker-pool-id"
      }
    ]
  }
}
```

## Parameters

| Field | Values | Notes |
|-------|--------|-------|
| `type` | `ActualCost`, `AmortizedCost` | ActualCost for real spend |
| `timeframe` | `Custom`, `MonthToDate`, `BillingMonthToDate` | Custom requires `timePeriod` |
| `granularity` | `None`, `Daily`, `Monthly` | None = single aggregate |
| `grouping.type` | `Dimension`, `TagKey` | TagKey for custom tags like `worker-pool-id` |

## Response Format

```json
{
  "properties": {
    "columns": [
      {"name": "Cost", "type": "Number"},
      {"name": "BillingMonth", "type": "DateTime"},
      {"name": "TagKey", "type": "String"},
      {"name": "TagValue", "type": "String"},
      {"name": "Currency", "type": "String"}
    ],
    "rows": [
      [14926.67, "2026-03-01T00:00:00", "worker-pool-id", "gecko-t/win11-64-24h2-gpu", "USD"],
      ...
    ]
  }
}
```

When granularity is `Daily`, the second column is an integer date
(e.g., `20260301`) instead of a datetime string.

## Row Limits

The API may return up to ~1000 rows per response. For daily granularity across
many pools over multiple months, query each month separately to avoid hitting
the limit.

## Listing Cost Exports

```bash
az costmanagement export list --scope "subscriptions/{subscriptionId}" --output table
az costmanagement export show --name fxci_daily_actual --scope "subscriptions/{subscriptionId}"
```

The export `deliveryInfo.destination` shows the storage account, container, and
root folder where CSV snapshots are written. These CSVs are large (200MB+ per
snapshot) and split across multiple files — prefer the query API for analysis.

## Subscription IDs

| Subscription | ID |
|---|---|
| FXCI Azure DevTest | `108d46d5-fe9b-4850-9a7d-8c914aa6c1f0` |
| Taskcluster Engineering DevTest | `8a205152-b25a-417f-a676-80465535a6c9` |
| Trusted FXCI Azure DevTest | `a30e97ab-734a-4f3b-a0e4-c51c0bff0701` |
| Mozilla Infrastructure Security | `9b9774fb-67f1-45b7-830f-aafe07a94396` |
| Firefox Non-CI DevTest | `0a420ff9-bc77-4475-befc-a05071fc92ec` |
| Mozilla 0DIN | `e1cb04e4-3788-471a-881f-385e66ad80ab` |

Only FXCI Azure DevTest has cost exports configured.

See `multi-subscription.md` for which subscriptions to use for CI cost analysis (the first 3) and which to exclude.
