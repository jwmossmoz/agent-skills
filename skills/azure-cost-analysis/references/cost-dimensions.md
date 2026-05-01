# Azure Cost Dimensions

Azure Cost Management lets you slice costs by multiple dimensions. Each dimension answers a different question. Use the right one for the investigation.

## Available grouping dimensions

| Dimension | What you see | Best for |
|---|---|---|
| `TagKey` (worker-pool-id) | Cost per TC worker pool | Branch/workload attribution |
| `Meter` (or `MeterName`) | Cost per VM SKU / line-item | "What kind of VM is being billed?" |
| `ResourceLocation` | Cost per Azure region | Spot pricing investigations, regional shifts |
| `ServiceFamily` | Compute / Networking / Storage | Big-picture infrastructure breakdown |
| `ServiceName` | Virtual Machines / Storage / Cloud Monitoring | Filtering compute vs non-compute |
| `ResourceId` | Per individual VM instance | VM lifecycle investigation (limited rows) |
| `ChargeType` | Usage / Purchase / Refund | Distinguishing usage from RIs/savings plans |

## Cost Management API — multiple dimensions

The REST API groups by one or two dimensions per query. Combine grouping with filters:

```json
{
  "type": "ActualCost",
  "timeframe": "Custom",
  "timePeriod": {"from": "2026-04-01", "to": "2026-04-30"},
  "dataset": {
    "granularity": "Daily",
    "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
    "grouping": [
      {"type": "Dimension", "name": "Meter"},
      {"type": "Dimension", "name": "ResourceLocation"}
    ]
  }
}
```

## Azure Portal limitation: one group-by at a time

The Cost Analysis UI only supports one group-by dimension. To combine, use **filter + group-by**:

- "Cost for SKU X by region" → Filter `Meter = "F8s v2 Spot"`, Group by `Resource location`
- "Costs in region Y by SKU" → Filter `Resource location = "EU North"`, Group by `Meter`

## When to use which dimension

### worker-pool-id tag
**Question:** Which workload (branch, pool group) drove the cost change?
- Maps directly to TC pool: `provisionerId/workerType` (e.g., `gecko-t/win11-64-24h2`)
- Some pools share VM SKUs (e.g., 24h2 and 25h2 regular pools both use F8s_v2) — tag attribution differs from SKU attribution
- Required for branch-level cost attribution
- Aggregates well across subscriptions

### Meter (SKU)
**Question:** Are we paying for different/more expensive VMs?
- Examples: `F8s v2 Spot`, `D32ads v5 Spot`, `NV12s v3 Spot`, `Standard IPv4 Static Public IP`, `D64s v4`
- Catches SKU swaps that don't change worker-pool-id (e.g., a pool being reassigned to a different VM SKU)
- Catches non-VM costs being captured under the same tag (storage, IPs)
- Best for SKU-level rate analysis

### ResourceLocation (region)
**Question:** Did spot prices change in a region? Did traffic shift between regions?
- Region names look like `eu north`, `us east 2`, `centralindia` (note: portal display formats vary slightly from `armRegionName`)
- Use to investigate Azure spot pricing changes (Retail Prices API gives effective dates per region)
- Use to detect traffic shifts after `initialWeight` reorders in `worker-pools.yml`
- Common regions for FXCI workers include `centralindia`, `southindia`, `northcentralus`, `centralus`, `eastus`, `eastus2`, `westus`, `westus2`, `westus3`, `canadacentral`, `northeurope`, `uksouth`

### ServiceFamily / ServiceName
**Question:** Are non-compute costs growing?
- `Compute > Virtual Machines` is usually the dominant share of CI cost
- `Networking > Virtual Network` — IP costs, egress
- `Storage > Storage Accounts` — disks, snapshots, blob storage
- Use to confirm compute is the issue (vs e.g. networking)

### ResourceId
**Question:** What is an individual VM costing?
- Returns thousands of rows for a busy CI subscription
- Useful for investigating outlier VMs or stuck instances
- Pair with VM lifecycle metrics (state durations) when available

## Common cross-dimensional analyses

### "Daily cost for one SKU by region"
Filter `Meter = <SKU> Spot`, Group by `Resource location`, daily granularity.
Reveals whether a single region drove spot cost increases.

### "Daily cost by Meter"
No filter, Group by `Meter`, daily granularity.
Shows which SKUs are growing fastest. Catches new SKU rollouts.

### "All non-VM costs"
Filter `ServiceFamily != Compute`, Group by `Meter`, monthly.
Useful for finding hidden costs (Snapshots, Static IPs, Networking).

## Specific investigation: cost increase on stable VM SKU

Recipe:
1. Group by `Meter`, identify the meter that grew most
2. Confirm the SKU didn't change for the affected pools (verify in `worker-pools.yml`)
3. Filter that meter, group by `Resource location` → did regions shift?
4. Filter that meter, group by `ChargeType` → only `Usage` (not reservations)?
5. If region/SKU/charge-type stable but cost rose: investigate evictions, idle billing, or spot price changes (see `spot-evictions.md` and `azure-spot-pricing.md`)
