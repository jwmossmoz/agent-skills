# Methodology — Lessons from Cost Investigations

Practical lessons for analyzing Azure CI cost trends. Read this first when investigating a cost anomaly — it prevents common mistakes.

## Daily cost vs cost-per-task: different signals

These are not the same thing. Pick the right one for the question you're asking.

### Use **daily cost** (raw $/day) when:
- Investigating overall spending changes
- Comparing periods where volume changed significantly
- Looking for inflection points in spending
- Comparing across regions/pools where volume is also changing

### Use **cost-per-task** when:
- Volume is stable across the comparison periods
- Investigating whether per-unit billing rates changed
- Looking for VM-overhead or eviction effects
- The pool/SKU is the same across both periods

### Why this matters: amortization artifacts

When a pool's task volume drops sharply but its fixed overhead (image prep, monitoring, idle warming, scaling reactions) stays similar, cost-per-task rises **purely from the math**, not from any real rate change.

**Illustrative example:** suppose pool A's task count falls 80% as traffic shifts to a replacement pool. Cost-per-task on pool A may rise significantly just from amortizing roughly stable VM overhead over fewer tasks. The daily cost on pool A may have actually fallen — the per-task rate looks worse, but spending is down.

**Cleaner test:** find a pool with stable volume across the comparison and check its cost/task. If a pool's volume is unchanged and same SKU, a cost/task rise is a real rate signal.

## Volume-weighted vs daily-rate averaging

When summarizing a period, use **volume-weighted averages**, not the average of daily rates.

```
WRONG: avg(daily $/task) for each day
RIGHT: sum(period cost) / sum(period tasks)
```

Daily rates can have high variance on weekends/low-volume days that distorts unweighted averages.

## Baseline selection

When picking a "before" period for comparison:
- **Don't use a recent month with known anomalies as a baseline** — if the prior month had a load surge, config changes, or new pools coming online, it's tainted.
- **Use the most recent fully normal month** as the pre-anomaly baseline.
- A "month-over-month" comparison can be misleading if the prior month was already anomalous — use a longer-term reference instead.

## Common math errors

### Don't divide one SKU's cost by ALL Azure tasks
A single SKU's cost (e.g., `F8s v2 Spot`) is a **subset** of total Azure cost. To compute cost-per-task for that SKU, divide by tasks on **pools that use that SKU only**. Including tasks from other pools in the denominator artificially deflates the rate.

### Account for month length differences
Feb=28d, Mar=31d, Apr=30d. A month-over-month comparison without per-day normalization understates or overstates the daily rate by ~7-10%.

### Don't compare partial-month totals to full-month totals
If you're analyzing mid-month, today's total is partial. Either wait, normalize to daily averages, or scale appropriately.

## Transition timing detection

To find precisely when a cost rate changed:

1. Compute volume-weighted **daily** cost/task for the relevant SKU
2. Establish a baseline mean and standard deviation from the normal period
3. Walk forward day-by-day flagging any day >+25% above baseline
4. The first sustained run of flagged days = onset
5. The peak daily value = peak

Be precise about onset dates. Off-by-a-week framing can lead engineers to pull telemetry from the wrong window and miss the cause.

## What's signal, what's noise

| Pattern | Likely signal |
|---|---|
| Cost/task up on stable-volume pool | Real rate change |
| Cost/task up on pool with traffic shift | Probably amortization artifact |
| Daily cost up with proportional task increase | Volume — not a rate change |
| Daily cost up with flat tasks | Real rate change |
| Sudden weekend cost spike | Probably batch/release event, not pricing |
| Multiple pools all rising similarly | Subscription-wide or Azure-wide cause |
| Single pool rising uniquely | Pool-specific config or event |

## When to ask "what didn't change"

Cost increases get the attention. But "what didn't change" is sometimes the diagnostic:
- A subscription with similar SKUs that didn't grow rules out general Azure pricing events
- A pool with the same SKU and stable volume that didn't show the increase rules out the SKU as the cause
- A region with no recent spot price effective-date change that still shows the increase rules out that price change as the dominant factor

A control case that didn't move points the investigation away from causes that would have moved it.

## Don't pre-commit to a hypothesis

Easy to fall into: pick a theory, then build a story around it.

Better: enumerate plausible mechanisms, design a test for each, run the test, write down what you ruled in or out. Keep theories labeled as theories until you have direct evidence (eviction logs, billing detail, etc.).

## Don't conflate "daily cost step change" with "cost/task rate change"

These can happen at different times and have different causes. A common mistake:
- Notice a sharp daily-cost rise on a specific date
- Conclude the "cost rate increased" on that date
- Investigate accordingly

But the daily-cost rise might be entirely explained by volume (more tasks = more cost). The actual cost-per-task rate may have changed earlier, later, or not at all. Compute both signals separately and check which inflected when.
