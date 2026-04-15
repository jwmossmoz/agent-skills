# Queue Diagnosis SQL Queries

Standalone query templates for manual use via the Redash skill. The
`diagnose.py` script runs these automatically, but they're documented here
for ad-hoc investigation or when the script isn't available.

All queries target `moz-fx-data-shared-prod.fxci.*` tables. Always filter on
`submission_date` (the partition key) to avoid full table scans.

## Queue Time Summary

Aggregate queue time stats for a pool over a date range. Queue time is
`started - scheduled` for tasks that actually started.

```sql
WITH base AS (
  SELECT
    tr.task_id,
    tr.run_id,
    tr.state,
    tr.reason_resolved,
    tr.scheduled,
    tr.started,
    t.task_queue_id
  FROM `moz-fx-data-shared-prod.fxci.task_runs` tr
  JOIN `moz-fx-data-shared-prod.fxci.tasks` t USING (task_id)
  WHERE tr.submission_date BETWEEN DATE '{start_date}' - 1 AND DATE '{end_date}' + 1
    AND t.submission_date BETWEEN DATE '{start_date}' - 1 AND DATE '{end_date}' + 1
    AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
    AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
    AND t.task_queue_id = '{pool_id}'
)
SELECT
  COUNT(*) AS total_runs,
  COUNTIF(started IS NOT NULL) AS started_runs,
  APPROX_QUANTILES(
    IF(started IS NOT NULL, TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(50)] AS median_queue_ms,
  APPROX_QUANTILES(
    IF(started IS NOT NULL, TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(90)] AS p90_queue_ms,
  APPROX_QUANTILES(
    IF(started IS NOT NULL, TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(95)] AS p95_queue_ms,
  MAX(IF(started IS NOT NULL, TIMESTAMP_DIFF(started, scheduled, MILLISECOND), NULL)) AS max_queue_ms,
  COUNTIF(state = 'exception' AND reason_resolved = 'deadline-exceeded') AS expired_count
FROM base
```

**Parameters:**
- `{start_date}` — inclusive UTC start (e.g., `2026-04-13`)
- `{end_date}` — exclusive UTC end (e.g., `2026-04-16`)
- `{pool_id}` — full queue ID (e.g., `gecko-t/win11-64-25h2`)

## Daily Volume by Project

Daily task counts broken down by project. Use a 7-day window to see the
trend and identify spikes.

```sql
SELECT
  DATE(tr.scheduled) AS day,
  t.tags.project AS project,
  COUNT(*) AS task_count,
  COUNTIF(tr.started IS NOT NULL) AS started_count,
  COUNTIF(tr.state = 'exception' AND tr.reason_resolved = 'deadline-exceeded') AS expired_count,
  APPROX_QUANTILES(
    IF(tr.started IS NOT NULL, TIMESTAMP_DIFF(tr.started, tr.scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(50)] AS median_queue_ms,
  APPROX_QUANTILES(
    IF(tr.started IS NOT NULL, TIMESTAMP_DIFF(tr.started, tr.scheduled, MILLISECOND), NULL),
    100
  )[OFFSET(90)] AS p90_queue_ms
FROM `moz-fx-data-shared-prod.fxci.task_runs` tr
JOIN `moz-fx-data-shared-prod.fxci.tasks` t USING (task_id)
WHERE tr.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND t.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
  AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
  AND t.task_queue_id = '{pool_id}'
GROUP BY 1, 2
ORDER BY 1, 2
```

## Top Pushers (Last 48 Hours)

Identifies who is submitting the most tasks, broken down by project. Useful
for spotting automated bots (wptsync, phabricator) or large individual try
pushes.

```sql
SELECT
  t.tags.project AS project,
  t.tags.created_for_user AS pusher,
  COUNT(DISTINCT t.task_group_id) AS task_groups,
  COUNT(*) AS total_tasks
FROM `moz-fx-data-shared-prod.fxci.task_runs` tr
JOIN `moz-fx-data-shared-prod.fxci.tasks` t USING (task_id)
WHERE tr.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND t.submission_date BETWEEN '{start_date}' AND '{end_date}'
  AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
  AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
  AND t.task_queue_id = '{pool_id}'
GROUP BY 1, 2
ORDER BY total_tasks DESC
LIMIT 25
```

## Queue Time by Task Group

Drill down into which task groups have the worst queue times. Useful after
the summary shows high queue times to find the specific pushes affected.

```sql
WITH base AS (
  SELECT
    tr.task_id,
    tr.run_id,
    tr.scheduled,
    tr.started,
    t.task_queue_id,
    t.task_group_id,
    t.tags.project AS project,
    t.tags.created_for_user AS created_for_user
  FROM `moz-fx-data-shared-prod.fxci.task_runs` tr
  JOIN `moz-fx-data-shared-prod.fxci.tasks` t USING (task_id)
  WHERE tr.submission_date BETWEEN DATE '{start_date}' - 1 AND DATE '{end_date}' + 1
    AND t.submission_date BETWEEN DATE '{start_date}' - 1 AND DATE '{end_date}' + 1
    AND tr.scheduled >= TIMESTAMP('{start_date} 00:00:00+00')
    AND tr.scheduled < TIMESTAMP('{end_date} 00:00:00+00')
    AND tr.started IS NOT NULL
    AND t.task_queue_id = '{pool_id}'
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
```
