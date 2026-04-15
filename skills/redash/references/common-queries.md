# Common Queries

## Provisioner Results as Percentage of Total Tasks

Shows task outcome breakdown (completed, failed, deadline-exceeded, canceled, etc.) as percentages for each provisioner/workerType/platform combination. Useful for identifying worker pools with high failure or deadline-exceeded rates.

Source: [Redash Query 91202](https://sql.telemetry.mozilla.org/queries/91202/)

```bash
uv run scripts/query_redash.py --sql "
WITH SumData as (
    SELECT CONCAT(provisionerId, '/', workerType, '/', platform) AS provisioner,
           SUM(IF(result = 'completed', 1, 0)) as completed,
           SUM(IF(result = 'failed', 1, 0)) as failed,
           SUM(IF(result = 'deadline-exceeded', 1, 0)) as deadline_exceeded,
           SUM(IF(result = 'canceled', 1, 0)) as canceled,
           SUM(IF(result = 'intermittent-task', 1, 0)) as intermittent_task,
           SUM(IF(result = 'claim-expired', 1, 0)) as claim_expired,
           SUM(IF(result = 'worker-shutdown', 1, 0)) as worker_shutdown,
           SUM(IF(result = 'malformed-payload', 1, 0)) as malformed_payload,
           SUM(IF(result = 'resource-unavailable', 1, 0)) as resource_unavailable,
           SUM(IF(result = 'internal-error', 1, 0)) as internal_error,
           count(*) AS total
    FROM taskclusteretl.derived_task_summary
    WHERE created BETWEEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY) AND CURRENT_TIMESTAMP()
      {provisioner_filter}
    GROUP BY provisioner
)
SELECT provisioner,
    total,
    completed/total*100 as completed,
    failed/total*100 as failed,
    deadline_exceeded/total*100 as deadline_exceeded,
    canceled/total*100 as canceled,
    intermittent_task/total*100 as intermittent_task,
    claim_expired/total*100 as claim_expired,
    worker_shutdown/total*100 as worker_shutdown,
    malformed_payload/total*100 as malformed_payload,
    resource_unavailable/total*100 as resource_unavailable,
    internal_error/total*100 as internal_error
FROM SumData
ORDER BY total desc
LIMIT {limit}
"
```

**Parameters:**
| Parameter | Example | Description |
|-----------|---------|-------------|
| `{days}` | `30` | Number of days to look back |
| `{limit}` | `10` | Max number of provisioner rows to return |
| `{provisioner_filter}` | (see below) | Optional filter for platform type |

**Provisioner filter values:**
| Platform | Filter |
|----------|--------|
| All | *(leave empty)* |
| Windows | `AND platform LIKE 'windows%'` |
| Linux | `AND platform LIKE 'linux%'` |
| macOS | `AND platform LIKE 'macosx%'` |
| Android | `AND platform LIKE 'android%'` |

## Windows Version Distribution (Firefox Desktop)

Client count by Windows version over the last 28 days. Returns `build_group` (e.g., `Win11 25H2`) and `observations` (raw client count).

Source: [Redash Query 65967](https://sql.telemetry.mozilla.org/queries/65967/)

```bash
uv run scripts/query_redash.py --query-id 65967 --format table
```

**Caveats:**
- Uses `sample_id = 42` (1% sample) — multiply `observations` by ~100 for population estimates
- Only includes Firefox >= 47
- Cached results are up to 48 hours old (query runs every 2 days)
- `Win11 25H2` covers build numbers 26101–26200 only; builds > 26200 (e.g., cumulative updates 26220, 26300) are bucketed as `Win11 Insider`

## macOS Version DAU + Architecture Breakdown (Firefox Desktop)

Two complementary queries: DAU by macOS version from `active_users_aggregates`, and client count by version × architecture from `baseline_clients_daily`. Use together since arch data is only available in the Glean dataset.

### DAU by macOS version

Source: [Redash Query 114866](https://sql.telemetry.mozilla.org/queries/114866/)

```bash
uv run scripts/query_redash.py --query-id 114866 --format table
```

### Client count by macOS version × architecture (aarch64 vs x86_64)

Source: [Redash Query 114867](https://sql.telemetry.mozilla.org/queries/114867/)

```bash
uv run scripts/query_redash.py --query-id 114867 --format table
```

**Caveats:**
- `active_users_aggregates` has no architecture column — DAU and arch breakdown require separate queries against different tables
- `architecture` in `baseline_clients_daily` is CPU/hardware arch — Intel Firefox under Rosetta 2 reports `aarch64`
- Cached results are up to 24 hours old

## Linux Distro Distribution (Daily)

Client count by Firefox distribution channel for Linux users, grouped by `distribution_id` (who packaged Firefox). Useful for seeing which Linux distros are represented in the user population.

```sql
SELECT
  distribution_id,
  COUNT(DISTINCT client_id) AS user_count
FROM `moz-fx-data-shared-prod.telemetry.clients_daily`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND os = 'Linux'
GROUP BY distribution_id
ORDER BY user_count DESC
```

**Caveats:**
- `distribution_id` reflects how Firefox was packaged, not the OS directly — users who downloaded Firefox from mozilla.org appear as empty/null regardless of distro
- To isolate a single distro, add `AND distribution_id = '<value>'` (e.g. `'nixos'`, `'canonical'`, `'fedora'`)

## NixOS Firefox Users (Daily)

Count of Firefox clients on NixOS (identified via `distribution_id = 'nixos'`).

```sql
SELECT
  COUNT(DISTINCT client_id) AS user_count
FROM `moz-fx-data-shared-prod.telemetry.clients_daily`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND os = 'Linux'
  AND distribution_id = 'nixos'
```

**Caveats:**
- Counts Firefox installed via nixpkgs — effectively the same as NixOS users in practice
- `normalized_os_version` (kernel version) cannot identify NixOS; `distribution_id` is the only reliable signal in aggregated tables

## EOL OS Firefox Users (Daily)

Client count grouped by EOL operating system: Windows 7, Windows 8.1, and macOS 10.12–10.14.

```sql
SELECT
  CASE
    WHEN os = 'Windows_NT' AND os_version = '6.1'         THEN 'Windows 7'
    WHEN os = 'Windows_NT' AND os_version = '6.3'         THEN 'Windows 8.1'
    WHEN os = 'Darwin' AND STARTS_WITH(os_version, '16.') THEN 'macOS 10.12 Sierra'
    WHEN os = 'Darwin' AND STARTS_WITH(os_version, '17.') THEN 'macOS 10.13 High Sierra'
    WHEN os = 'Darwin' AND STARTS_WITH(os_version, '18.') THEN 'macOS 10.14 Mojave'
  END AS os_label,
  COUNT(DISTINCT client_id) AS user_count
FROM `moz-fx-data-shared-prod.telemetry.clients_daily`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND (
    (os = 'Windows_NT' AND os_version IN ('6.1', '6.3'))
    OR
    (os = 'Darwin' AND (
      STARTS_WITH(os_version, '16.')
      OR STARTS_WITH(os_version, '17.')
      OR STARTS_WITH(os_version, '18.')
    ))
  )
GROUP BY os_label
ORDER BY os_label
```

**Notes:**
- macOS `os_version` is the Darwin kernel version — 16.x = 10.12 Sierra, 17.x = 10.13 High Sierra, 18.x = 10.14 Mojave
- Windows `os_version` is the NT version — 6.1 = Windows 7, 6.3 = Windows 8.1
- Use `LIKE` instead of `STARTS_WITH` if running outside of BigQuery

## EOL OS Firefox Users on ESR 115 (Daily)

Same as above but filtered to clients running Firefox ESR 115. Useful for tracking users on EOL platforms who are still on the ESR 115 extended support release.

```sql
SELECT
  CASE
    WHEN os = 'Windows_NT' AND os_version = '6.1'         THEN 'Windows 7'
    WHEN os = 'Windows_NT' AND os_version = '6.3'         THEN 'Windows 8.1'
    WHEN os = 'Darwin' AND STARTS_WITH(os_version, '16.') THEN 'macOS 10.12 Sierra'
    WHEN os = 'Darwin' AND STARTS_WITH(os_version, '17.') THEN 'macOS 10.13 High Sierra'
    WHEN os = 'Darwin' AND STARTS_WITH(os_version, '18.') THEN 'macOS 10.14 Mojave'
  END AS os_label,
  COUNT(DISTINCT client_id) AS user_count
FROM `moz-fx-data-shared-prod.telemetry.clients_daily`
WHERE submission_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  AND normalized_channel = 'esr'
  AND STARTS_WITH(app_version, '115.')
  AND (
    (os = 'Windows_NT' AND os_version IN ('6.1', '6.3'))
    OR
    (os = 'Darwin' AND (
      STARTS_WITH(os_version, '16.')
      OR STARTS_WITH(os_version, '17.')
      OR STARTS_WITH(os_version, '18.')
    ))
  )
GROUP BY os_label
ORDER BY os_label
```

## Task Group Cost by Pusher

Cost breakdown per task group for a specific user. Replace `{start_date}` and `{user_email}` with actual values.

```bash
uv run scripts/query_redash.py --sql "
SELECT tags.created_for_user AS pusher,
       task_group_id,
       SUM(run_cost) AS cost
FROM fxci.tasks
JOIN fxci.task_run_costs
  ON tasks.task_id = task_run_costs.task_id
WHERE tasks.submission_date >= '{start_date}'
  AND task_run_costs.submission_date >= '{start_date}'
  AND tags.created_for_user = '{user_email}'
GROUP BY tags.created_for_user,
         task_group_id
"
```

**Parameters:**
| Parameter | Example | Description |
|-----------|---------|-------------|
| `{start_date}` | `2026-02-01` | Filter tasks submitted on or after this date |
| `{user_email}` | `jdoe@mozilla.com` | The pusher's email address |

## FXCI Worker Pool Queue Time (Historical)

Historical queue-time summary for a specific Taskcluster worker pool using FXCI task data in BigQuery. This is the right query shape for questions about why a worker pool is showing high queue time or queue time max.

```bash
uv run scripts/query_redash.py --sql "
WITH base AS (
  SELECT
    tr.task_id,
    tr.run_id,
    tr.state,
    tr.reason_resolved,
    tr.scheduled,
    tr.started,
    tr.resolved,
    tr.worker_group,
    tr.worker_id,
    t.task_queue_id,
    t.tags.project AS project,
    t.tags.created_for_user AS created_for_user,
    t.tags.label AS label
  FROM \`moz-fx-data-shared-prod.fxci.task_runs\` tr
  JOIN \`moz-fx-data-shared-prod.fxci.tasks\` t USING (task_id)
  WHERE tr.submission_date BETWEEN DATE '{start_date}' - 1 AND DATE '{end_date}' + 1
    AND t.submission_date BETWEEN DATE '{start_date}' - 1 AND DATE '{end_date}' + 1
    AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
    AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
    AND t.task_queue_id = '{task_queue_id}'
)
SELECT
  COUNT(*) AS total_rows,
  COUNTIF(started IS NOT NULL) AS started_rows,
  APPROX_QUANTILES(
    IF(started IS NOT NULL, TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(50)] AS median_queue_ms,
  APPROX_QUANTILES(
    IF(started IS NOT NULL, TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(90)] AS p90_queue_ms,
  MAX(IF(started IS NOT NULL, TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL)) AS max_queue_ms,
  COUNTIF(state = 'exception' AND reason_resolved = 'deadline-exceeded') AS expired_rows
FROM base
"
```

**Parameters:**
| Parameter | Example | Description |
|-----------|---------|-------------|
| `{start_date}` | `2026-04-14` | Inclusive UTC day start |
| `{end_date}` | `2026-04-15` | Exclusive UTC day end |
| `{task_queue_id}` | `provisioner/worker-type` | Full Taskcluster queue ID |

**Notes:**
- `queue time` is `started - scheduled` for tasks that actually started.
- `queue time max` is the max of that same value within the selected UTC scheduled window.
- Use a wider `submission_date` partition filter than the UTC window. Filtering only on a single `submission_date` can undercount runs near day boundaries.
- This query is for historical analysis. For current pending/claimed counts, running/stopping workers, and provisioning errors, use the Taskcluster skill instead of Redash.

## FXCI Worker Pool Queue Time by Project or Task Group

Use this when the summary says queue time is high and you need to identify whether the backlog is coming from `try`, `autoland`, or a few large task groups.

```bash
uv run scripts/query_redash.py --sql "
WITH base AS (
  SELECT
    tr.task_id,
    tr.run_id,
    tr.scheduled,
    tr.started,
    t.task_queue_id,
    t.task_group_id,
    t.tags.project AS project,
    t.tags.created_for_user AS created_for_user,
    t.tags.label AS label
  FROM \`moz-fx-data-shared-prod.fxci.task_runs\` tr
  JOIN \`moz-fx-data-shared-prod.fxci.tasks\` t USING (task_id)
  WHERE tr.submission_date BETWEEN DATE '{start_date}' - 1 AND DATE '{end_date}' + 1
    AND t.submission_date BETWEEN DATE '{start_date}' - 1 AND DATE '{end_date}' + 1
    AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
    AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
    AND tr.started IS NOT NULL
    AND t.task_queue_id = '{task_queue_id}'
)
SELECT
  project,
  task_group_id,
  created_for_user,
  COUNT(*) AS started_rows,
  APPROX_QUANTILES(TIMESTAMP_DIFF(started, scheduled, MILLISECOND), 100)[OFFSET(50)] AS median_queue_ms,
  APPROX_QUANTILES(TIMESTAMP_DIFF(started, scheduled, MILLISECOND), 100)[OFFSET(90)] AS p90_queue_ms,
  MAX(TIMESTAMP_DIFF(started, scheduled, MILLISECOND)) AS max_queue_ms
FROM base
GROUP BY 1, 2, 3
ORDER BY max_queue_ms DESC, started_rows DESC
LIMIT 50
"
```

**Interpretation tips:**
- A few large `try` task groups with very high queue times usually mean bursty low-priority demand.
- High `autoland` queue times point to broader pool pressure that can affect production traffic.
- If many groups are bad at once and Taskcluster shows lots of `stopping` workers or provisioning errors, the problem is likely capacity churn rather than a single push.
