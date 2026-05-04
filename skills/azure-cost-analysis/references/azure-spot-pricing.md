# Azure Spot Pricing Investigation

CI workers run on Azure Spot VMs. Spot prices fluctuate by region and SKU based on Azure's spare capacity. Sudden cost increases can be (in part) spot price changes — but verifying this is harder than it should be.

## What's available

### Azure Retail Prices API
- Public, no auth required
- Returns **current** published prices
- Has an `effectiveStartDate` field
- Does **NOT** return historical prices

### Azure Cost Management
- Shows **what you actually paid** historically (your billing data)
- For spot VMs, the effective hourly rate fluctuates day-by-day with the spot market
- Most useful in Cost Analysis with `Group by: Meter` + `Filter: Resource location`

### Microsoft account team / FastTrack engineer
- Can pull historical spot price data on request
- Best route for true historical price comparison

## Querying current prices via Retail Prices API

Endpoint:
```
https://prices.azure.com/api/retail/prices
```

Filter syntax (OData):
```bash
curl -sL "https://prices.azure.com/api/retail/prices?\$filter=skuName%20eq%20'F8s%20v2%20Spot'%20and%20serviceName%20eq%20'Virtual%20Machines'" -o prices.json
```

Important filter values:
- `serviceName eq 'Virtual Machines'` — filter to compute VMs
- `skuName eq 'F8s v2 Spot'` — specific SKU (note the space, "v2 Spot" not "v2_Spot")
- `armRegionName eq 'eastus2'` — specific region (no spaces, lowercase)
- `type eq 'Consumption'` — exclude reservations
- `unitOfMeasure eq '1 Hour'` — hourly billing units

## Interpreting `effectiveStartDate`

This field tells you **when the current published price became effective**. It does NOT tell you:
- Whether the price went up or down
- What the price was before
- Whether prices changed multiple times in the past year (only the most recent change is visible)

**This is a significant limitation.** A region with `effectiveStartDate = 2026-04-01` may have had a price increase, decrease, or just a publish-time refresh on that date. You can't tell from the API alone.

## How to determine direction (increase vs decrease)

You need to combine the API data with your billing data:

1. Pull current prices via Retail API for SKUs and regions of interest. Save the JSON. Note any `effectiveStartDate` falling within the cost-change window.
2. From your billing data, compute daily $/day in those regions before vs after the effective date.
3. **If daily cost dropped after the effective date** → price went down → rules out price increase as cause.
4. **If daily cost rose AND the effective date is in the cost-change window** → price increase is a candidate.
5. **If daily cost rose but no effective-date change** → spot price may have varied within the existing range, or it's not pricing.

## Workflow for "did spot prices drive the cost increase?"

1. Identify SKUs and regions where cost grew significantly
2. Query Retail Prices API for current prices and effective dates
3. Cross-reference effective dates with the cost-change window in your billing data
4. Apply the direction-determination logic above
5. If pricing is ruled out, investigate other rate-change mechanisms (eviction overhead, VM lifecycle — see `spot-evictions.md`)

## Limitations

- The Retail Prices API doesn't expose historical prices.
- Cost Management shows what you paid but doesn't expose "the listed price was X" — it shows "you paid X for Y hours."
- Spot prices can vary day-to-day even within a "stable" period — the effective date is when the published rate band changed, not necessarily the actual market rate.
- Different sub-regions or instance generations within the same SKU family may have different prices.
- For deeper analysis (true historical price comparison), you'll need to engage your Microsoft account team or FastTrack engineer.

## When spot pricing is NOT the cause

If cost-per-task rises broadly across many regions including ones with no recent `effectiveStartDate`, spot pricing alone can't explain it. Other regions matching the same pattern means the cause is region-agnostic — likely eviction rate, VM lifecycle overhead, or per-VM idle time. See `spot-evictions.md`.
