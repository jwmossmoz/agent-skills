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

```bash
uv run scripts/query_redash.py --format table --sql "
SELECT
  os_version_major AS darwin_version,
  SUM(dau) AS total_dau
FROM \`mozdata.telemetry.active_users_aggregates\`
WHERE app_name = 'Firefox Desktop'
  AND submission_date > DATE_SUB(CURRENT_DATE, INTERVAL 28 DAY)
  AND submission_date < CURRENT_DATE
  AND os = 'Darwin'
GROUP BY darwin_version
ORDER BY total_dau DESC
"
```

### Client count by macOS version × architecture (aarch64 vs x86_64)

```bash
uv run scripts/query_redash.py --format table --sql "
SELECT
  CASE
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 25 THEN 'macOS 16'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 24 THEN 'macOS 15 Sequoia'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 23 THEN 'macOS 14 Sonoma'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 22 THEN 'macOS 13 Ventura'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 21 THEN 'macOS 12 Monterey'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 20 THEN 'macOS 11 Big Sur'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 19 THEN 'macOS 10.15 Catalina'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 18 THEN 'macOS 10.14 Mojave'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 17 THEN 'macOS 10.13 High Sierra'
    WHEN SAFE_CAST(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)] AS INT64) = 16 THEN 'macOS 10.12 Sierra'
    ELSE CONCAT('Darwin ', COALESCE(SPLIT(normalized_os_version, '.')[SAFE_OFFSET(0)], 'unknown'))
  END AS macos_version,
  architecture AS arch,
  COUNT(DISTINCT client_id) AS client_count
FROM \`moz-fx-data-shared-prod.firefox_desktop.baseline_clients_daily\`
WHERE submission_date > DATE_SUB(CURRENT_DATE, INTERVAL 28 DAY)
  AND normalized_os = 'Mac'
GROUP BY macos_version, arch
ORDER BY macos_version, arch
"
```

**Caveats:**
- `active_users_aggregates` has no architecture column — DAU and arch breakdown require separate queries against different tables
- DAU query uses `os_version_major` (pre-split integer), no CASE mapping needed
- `architecture` in `baseline_clients_daily` is CPU/hardware arch — Intel Firefox under Rosetta 2 reports `aarch64`
- `SAFE_CAST` / `SAFE_OFFSET` required in arch query — some clients have null/malformed `normalized_os_version`

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
