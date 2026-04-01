# Taskcluster Task Counting

When cost increases on a worker pool, the likely explanation is more tasks
running on that pool. Use the Taskcluster API to count tasks per push and
identify which test suites are responsible.

## Approach

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
