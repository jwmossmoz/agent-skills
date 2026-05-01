# Spot Eviction Investigation

Azure Spot VMs are preemptible. Azure can evict them with ~30 seconds notice when capacity is needed. Each eviction has a real cost mechanism: VMs are billed for the time they were running, but the task they were executing has to retry on a new VM. Higher eviction rate = more cost per completed task without any change in VM SKU, region, or per-hour rate.

This is a leading hypothesis to consider when:
- Cost/task rises uniformly across regions (Azure capacity issues are usually broad)
- Daily $/day stays similar but completed tasks per VM-hour drops
- Volume/task counts didn't change to explain it
- VM SKU and config are unchanged

## How eviction inflates cost-per-task

A simplified mental model:

```
Without eviction:
  VM provisions → runs Task A for 10min → runs Task B for 10min → ...
  Tasks/VM-hour ≈ 6 (overhead aside)
  Cost/task = (VM $/hour) / 6

With high eviction rate:
  VM provisions → runs Task A for 5min → EVICTED (5 min billed, 0 tasks completed)
  New VM provisions → retries Task A for 10min → ...
  Tasks/VM-hour ≈ 3-4 (eviction wastes ~half the time)
  Cost/task ≈ doubles
```

The cost numbers can stay constant while completed tasks drop, producing a perfect "rate increase" pattern in cost-per-task.

## Where eviction telemetry lives

### Note on ephemeral OS disks

If your worker pools use **ephemeral OS disks** (cheaper than managed disks but disposable), the VM's local storage is gone the moment the VM stops or is evicted. This means:

**Not available with ephemeral disks:**
- VM-internal logs (Windows event logs, worker logs written to local disk)
- Preemption notification handler output from inside the VM
- Worker diagnostics at time of eviction

**Still available with ephemeral disks:**
- Azure Activity Log (cloud-level, captured outside the VM)
- TC worker-manager logs (TC service-level)
- `fxci.task_runs.reason_resolved` — externally captured by TC
- Azure billing/usage data

For ephemeral-disk environments, `task_runs.reason_resolved` is often the most accessible eviction signal — see source #3 below.

### 1. fxci.task_runs (BigQuery via Redash) — recommended starting point

This is the most accessible eviction signal because it's externally captured by Taskcluster. When a VM is evicted mid-task, the task's claim expires and TC marks the run with `reason_resolved = 'worker-shutdown'`. Counting these per day per pool gives a daily eviction rate.

```sql
SELECT
    tr.submission_date,
    tr.reason_resolved,
    tr.worker_group AS azure_region,
    SPLIT(t.task_queue_id, '/')[SAFE_OFFSET(0)] AS provisioner_id,
    SPLIT(t.task_queue_id, '/')[SAFE_OFFSET(1)] AS worker_type,
    count(*) AS run_count
FROM fxci.task_runs AS tr
INNER JOIN fxci.tasks AS t
    ON tr.task_id = t.task_id AND tr.submission_date = t.submission_date
WHERE
    tr.state = 'exception'
    AND tr.reason_resolved IN ('claim-expired', 'worker-shutdown')
    AND tr.submission_date >= 'YYYY-MM-DD'
    AND t.submission_date >= 'YYYY-MM-DD'
    AND tr.worker_group NOT LIKE 'us-%'
    AND tr.worker_group NOT LIKE 'europe-%'
    AND tr.worker_group NOT LIKE 'northamerica-%'
GROUP BY tr.submission_date, tr.reason_resolved, tr.worker_group, provisioner_id, worker_type
ORDER BY tr.submission_date DESC, tr.reason_resolved ASC, run_count DESC
```

The `worker_group NOT LIKE` filters exclude GCP zones (which follow `region-cardinal-letter` patterns). Azure regions are reported as names like `eastus2`, `northcentralus`, `centralindia`.

**Reason codes:**
- `worker-shutdown` — the VM went away unexpectedly. **Primary spot eviction signal.**
- `claim-expired` — task waited too long for any worker to pick it up. Indicates queue starvation, often during/after capacity events.
- Other codes (`internal-error`, `intermittent-task`, etc.) are not eviction signals.

### 2. Azure Activity Log
Azure logs `ServiceHealth` and `ResourceHealth` events when spot VMs are evicted. Filter for:
- Operation: `Microsoft.Compute/virtualMachines/preempted/action` (or similar — name varies by API version)
- Resource type: `Microsoft.Compute/virtualMachines`

```bash
az monitor activity-log list \
  --start-time YYYY-MM-DD \
  --end-time YYYY-MM-DD \
  --resource-type "Microsoft.Compute/virtualMachines" \
  --query "[?contains(operationName.value, 'preempt')]"
```

This is independent confirmation of evictions at the Azure infrastructure layer. Useful to cross-check against the TC-level `task_runs` data.

### 3. TC worker-manager preemption events
The Taskcluster worker-manager logs preemption events when it observes a worker exit unexpectedly. Look for log entries with reasons like `worker-shutdown`, `claim-expired`, or `internal-error` paired with short uptime.

The `taskcluster_workerlog` table or the worker-manager service logs are the right starting points. The TC engineering team can pull preemption rates per pool per day.

### 4. Multiple runs per task as a retry-rate proxy
When a VM is evicted mid-task, the task may retry on a new VM, producing multiple `run_id` values for the same `task_id`. Counting tasks with multiple runs per month is a coarser proxy for "how often did tasks need to retry due to worker loss" — useful as a secondary check.

```sql
SELECT
    DATE_TRUNC(t.submission_date, MONTH) AS month,
    SPLIT(t.task_queue_id, '/')[SAFE_OFFSET(0)] AS provisioner_id,
    SPLIT(t.task_queue_id, '/')[SAFE_OFFSET(1)] AS worker_type,
    COUNT(DISTINCT t.task_id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN tr.run_id > 0 THEN t.task_id END) AS retried_tasks,
    SAFE_DIVIDE(
      COUNT(DISTINCT CASE WHEN tr.run_id > 0 THEN t.task_id END),
      COUNT(DISTINCT t.task_id)
    ) * 100 AS retry_rate_pct,
    SUM(CASE WHEN tr.run_id > 0 THEN 1 ELSE 0 END) AS total_retry_runs
FROM fxci.tasks AS t
INNER JOIN fxci.task_runs AS tr
    ON t.task_id = tr.task_id AND t.submission_date = tr.submission_date
WHERE
    t.submission_date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'
    AND tr.submission_date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'
    AND SPLIT(t.task_queue_id, '/')[SAFE_OFFSET(1)] IN (
        'win11-64-24h2', 'win11-64-25h2', 'win11-64-24h2-gpu', 'win11-64-25h2-gpu',
        'b-win2022', 'win10-64-2009'
    )
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
```

**Important interpretation note:** retry rate alone does not explain large cost-per-task increases. A retry rate going from 4% to 6% means roughly 2% more total VM-runs per completed task — small in cost terms. If cost-per-task rose far more than retry rate would suggest, the dominant mechanism is something other than retries (e.g., more billed VM-time per VM lifecycle: provisioning overhead, idle time at queueInactivityTimeout, or wasted partial-task time on evicted VMs).

## Investigation workflow

1. **Pull eviction events** from Azure Activity Log for your investigation window plus a buffer of at least 1-2 weeks before. Break out by region and VM SKU.
2. **Pull TC preemption events** for the same window.
3. **Compute daily eviction rate** = evictions / (active VMs ⋅ active hours), or simpler: evictions per day per pool.
4. **Plot the rate alongside daily cost/task** for the same window.
5. **Look for correlation** — does eviction rate inflect on the same date that cost/task starts rising?

If the eviction rate curve aligns with the cost/task curve, eviction is confirmed as the driver.

## What evictions can't explain alone

Some things only line up if you combine eviction overhead with other factors:
- A specific date inflection — needs a triggering capacity event
- Single-region effects — Azure capacity is usually broad
- Specific SKU effects — though some SKUs are more eviction-prone than others

## Mitigations to consider once confirmed

- Switch to non-spot for a subset of pools (more expensive baseline rate but no eviction)
- Reduce maxCapacity to lower concurrent VM count and reduce eviction collisions
- Use multiple SKU families per pool (Azure Spot Priority Mix) so evictions on one SKU don't kill all VMs
- Increase region diversity (eviction is often regional)

## Note on detection lag

Cost data lags by 1-2 days. Eviction events are real-time in Activity Log. If the eviction rate started rising on a specific day, expect cost/task changes to appear in billing 1-2 days later. The timing should look like:

```
Day N:    Eviction rate spikes
Day N+1:  Today's daily billing reflects partial-day eviction overhead
Day N+2:  First full day of elevated billing visible
```

When pulling telemetry, start at least a week before the cost-change date to capture the onset and the baseline rate.
