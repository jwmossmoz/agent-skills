-- ============================================================
-- Azure-only task counts by branch and pool
-- ============================================================
-- Source table: taskclusteretl.derived_task_summary (BigQuery via Redash)
-- Inputs: replace YYYY-MM-DD with start and end dates
-- Output columns: date, project, provisionerId, workerType, kind, platform,
--                 workerGroup, task_count, avg_exec_minutes
--
-- Use cases:
--   - Correlate Azure cost (Cost Management worker-pool-id tag) with task volume
--   - Investigate volume vs rate when cost is rising
--   - Compute cost-per-task for stable-volume pools
--
-- Notes:
--   - The workerGroup NOT LIKE filters exclude GCP zones (region-cardinal-letter
--     pattern). Azure regions are bare names (eastus2, northcentralus, etc.).
--   - Some non-Azure rows can slip through (mdc1 hardware, scriptworker pools);
--     they won't match any Azure pool_id and are silently ignored in cost
--     attribution.
--   - Join key for cost attribution: provisionerId + '/' + workerType matches
--     the Azure worker-pool-id tag value.
--
-- See: references/taskcluster-task-counting.md
-- ============================================================

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
WHERE created >= 'YYYY-MM-DD'
  AND created <  'YYYY-MM-DD'
  AND workerGroup NOT LIKE 'us-%'
  AND workerGroup NOT LIKE 'europe-%'
  AND workerGroup NOT LIKE 'northamerica-%'
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY 1, 2, 3, 4
