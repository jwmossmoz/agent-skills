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

## macOS Version × Architecture Distribution (Firefox Desktop)

Client count broken down by macOS version and Firefox build architecture (aarch64 vs x86-64) over the last 28 days. Useful for understanding Apple Silicon vs Intel adoption across OS versions.

```bash
uv run scripts/query_redash.py --format table --sql "
SELECT
  CASE
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 25 THEN 'macOS 16'
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 24 THEN 'macOS 15 Sequoia'
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 23 THEN 'macOS 14 Sonoma'
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 22 THEN 'macOS 13 Ventura'
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 21 THEN 'macOS 12 Monterey'
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 20 THEN 'macOS 11 Big Sur'
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 19 THEN 'macOS 10.15 Catalina'
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 18 THEN 'macOS 10.14 Mojave'
    WHEN CAST(SPLIT(os_version, '.')[OFFSET(0)] AS INT64) = 17 THEN 'macOS 10.13 High Sierra'
    ELSE CONCAT('Darwin ', SPLIT(os_version, '.')[OFFSET(0)])
  END AS macos_version,
  env_build_arch AS arch,
  COUNT(DISTINCT client_id) AS client_count
FROM \`moz-fx-data-shared-prod.telemetry.clients_daily\`
WHERE submission_date > DATE_SUB(CURRENT_DATE, INTERVAL 28 DAY)
  AND os = 'Darwin'
  AND env_build_arch IN ('aarch64', 'x86-64')
GROUP BY macos_version, arch
ORDER BY macos_version, arch
"
```

**Caveats:**
- `env_build_arch` reflects the Firefox *build* architecture — Intel builds running under Rosetta 2 on Apple Silicon show as `x86-64`, so true Apple Silicon hardware share is higher than the aarch64 count alone
- Darwin kernel version is used to derive macOS version name; update the `CASE` statement as new macOS releases ship

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
