# Taskcluster Task Counting

When cost increases on a worker pool, the likely explanation is more tasks running on that pool. Two approaches:

1. **Per-push via TC API** — use this for drilling into a specific push's task list, including chunk counts and test suites. Detailed below.
2. **Cross-month batch via BigQuery** — use this for monthly/weekly cost analysis. See "BigQuery via Redash" section at the bottom.

## Per-push via TC API approach

1. Use the TC **index API** to find pushes on a given date
2. Look up an indexed task from the push to get its `taskGroupId`
3. Paginate through the **task group** listing all tasks
4. Count tasks by `taskQueueId` (worker pool) and `tags.test-suite`

## API Endpoints

### List push timestamps for a date

```
GET https://firefox-ci-tc.services.mozilla.com/api/index/v1/namespaces/gecko.v2.mozilla-central.pushdate.{YYYY}.{MM}.{DD}
```

Returns namespaces like `20260115051035`, `20260115092108`, etc.

### Get an indexed task from a push

```
GET https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/gecko.v2.mozilla-central.pushdate.{YYYY}.{MM}.{DD}.{push_time}.firefox.linux64-opt
```

Returns `{"taskId": "..."}`. Use any indexed artifact (linux64-opt works reliably).

### Get task metadata (for taskGroupId)

```
GET https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/{taskId}
```

The `taskGroupId` field identifies the push's task group.

### List tasks in a task group

```
GET https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task-group/{taskGroupId}/list?limit=1000
```

Paginate via `continuationToken`. Each task includes:

```json
{
  "task": {
    "taskQueueId": "gecko-t/win11-64-24h2",
    "metadata": {"name": "test-windows11-64-24h2/opt-mochitest-browser-chrome-15"},
    "tags": {
      "kind": "test",
      "test-platform": "windows11-64-24h2/opt",
      "test-suite": "mochitest-browser-chrome",
      "test-type": "mochitest"
    }
  }
}
```

### Get pending task count (current snapshot)

```
GET https://firefox-ci-tc.services.mozilla.com/api/queue/v1/pending/{provisionerId}/{workerType}
```

## Useful Tag Fields

| Tag | Purpose |
|-----|---------|
| `test-suite` | Test suite name (mochitest-browser-chrome, web-platform-tests, etc.) |
| `test-type` | Broader category (mochitest, reftest, xpcshell, etc.) |
| `test-platform` | Full platform string (windows11-64-24h2/opt, etc.) |
| `kind` | Task kind (test, build, mochitest, etc.) |

## Interpreting Results

When comparing two push dates:

- **More tasks on a pool** = higher VM costs (more VMs provisioned)
- **Check chunk counts** — test suites are split into chunks, each chunk is a
  separate task on a separate VM. If `mochitest-browser-chrome` went from 105
  to 279 tasks, someone likely increased the chunk count in
  `taskcluster/kinds/test/mochitest.yml`
- **New pools** appearing = additive spend if old pools haven't wound down
- **Task duration** matters too but isn't captured in task counts — check
  Treeherder for job durations if counts alone don't explain the cost change

## Where Chunk Counts Are Configured

In the Firefox repository:

| Suite | Config file |
|-------|-------------|
| mochitest-* | `taskcluster/kinds/test/mochitest.yml` |
| web-platform-tests | `taskcluster/kinds/web-platform-tests/kind.yml` |
| reftest | `taskcluster/kinds/test/reftest.yml` |
| xpcshell | `taskcluster/kinds/test/xpcshell.yml` |
| talos/raptor | `taskcluster/kinds/test/talos.yml`, `taskcluster/kinds/browsertime/desktop.yml` |

Look for `chunks:` values under the relevant platform key (e.g., `windows11-64-24h2`).

---

## BigQuery via Redash — for cross-month analysis

For analyzing task volumes across a month or comparing months, the TC API approach (push-by-push) is too slow and doesn't aggregate well. Use `taskclusteretl.derived_task_summary` via Redash instead.

### Why this table is useful for cost analysis
- Pre-aggregated, full task history
- Includes `provisionerId` + `workerType` (combine for full pool ID matching Azure tags)
- Includes `project` (branch), `kind`, `platform`, `workerGroup` (region), `execution` (minutes)
- One row per task run

### Azure-only filter (essential)
GCP and Azure workers are mixed in this table. Filter to Azure by excluding GCP zone names:

```sql
WHERE workerGroup NOT LIKE 'us-%'         -- excludes us-central1-*, us-east1-*, etc.
  AND workerGroup NOT LIKE 'europe-%'      -- excludes europe-west1-*
  AND workerGroup NOT LIKE 'northamerica-%' -- excludes northamerica-northeast1-*
```

Azure regions follow names like `eastus2`, `northcentralus`, `centralindia` (no hyphenated zones). GCP zones follow `<region>-<cardinal><number>` like `us-central1-b`. The exclusion filter is more reliable than trying to enumerate all Azure regions.

A small number of non-Azure rows can slip through (releng-hardware at `mdc1`, scriptworker-k8s) — they won't match any Azure pool_id during cost attribution and are silently ignored.

### Standard Azure-only task volume query

```sql
SELECT
    DATE(created) AS date,
    project,
    provisionerId,
    workerType,
    kind,
    platform,
    workerGroup,
    COUNT(*) AS task_count,
    AVG(execution) AS avg_exec_minutes
FROM taskclusteretl.derived_task_summary
WHERE created >= '2026-04-01'
  AND created < '2026-05-01'
  AND workerGroup NOT LIKE 'us-%'
  AND workerGroup NOT LIKE 'europe-%'
  AND workerGroup NOT LIKE 'northamerica-%'
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY 1, 2, 3, 4
```

### Joining to Azure cost data

The Azure `worker-pool-id` tag is `provisionerId/workerType`. Use this as the join key when correlating Azure cost (from Cost Management) with task counts (from this BigQuery table).

```python
pool_id = f"{row['provisionerId']}/{row['workerType']}"
# matches Azure cost CSV's TagValue
```

### Caveats

- `created` is the task creation timestamp; use it for "tasks created on this date"
- `execution` is in minutes per task; `AVG(execution)` can be skewed by deadline-exceeded tasks (~24h/1440min outliers). Use median or filter `execution < 1440` if outliers distort the analysis.
- A single task can have multiple `runId` values (retries). The query above counts all rows; if you only want unique tasks, filter `runId = 0`.
