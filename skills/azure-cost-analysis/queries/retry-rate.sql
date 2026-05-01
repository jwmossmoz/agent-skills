-- ============================================================
-- Task retry rate by pool, by month
-- ============================================================
-- Source tables: fxci.tasks JOIN fxci.task_runs (BigQuery via Redash)
-- Inputs: replace YYYY-MM-DD with date range
--         (also adjust the workerType IN clause for pools of interest)
-- Output columns: month, provisioner_id, worker_type, total_tasks,
--                 retried_tasks, retry_rate_pct, total_retry_runs
--
-- Definitions:
--   run_id = 0     → task's first attempt
--   run_id > 0     → retry (task had to re-run because the prior run failed)
--   retried_tasks  → distinct tasks that needed at least one retry
--   total_retry_runs → total run_id > 0 records (a task can retry multiple times)
--
-- Use cases:
--   - Detect rising retry rates indicating worker preemption / instability
--   - Correlate with eviction event timelines
--   - Compare across pools to find anomalies
--
-- Important interpretation note:
--   Retry rate alone usually does not explain large cost-per-task increases.
--   A rate going from 4% to 6% means roughly 2% more total VM-runs per
--   completed task — small in cost terms. If cost-per-task rose far more
--   than retry rate would suggest, the dominant mechanism is something
--   other than retries (provisioning overhead, idle billing, etc.)
--
-- See: references/spot-evictions.md
-- ============================================================

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
    ON t.task_id = tr.task_id
   AND t.submission_date = tr.submission_date
WHERE
    t.submission_date  BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'
    AND tr.submission_date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'
    -- Adjust this list to the pools relevant to your investigation:
    AND SPLIT(t.task_queue_id, '/')[SAFE_OFFSET(1)] IN (
        'win11-64-24h2',
        'win11-64-25h2',
        'win11-64-24h2-gpu',
        'win11-64-25h2-gpu',
        'b-win2022',
        'win10-64-2009'
    )
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
