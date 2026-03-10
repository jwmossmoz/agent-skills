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
