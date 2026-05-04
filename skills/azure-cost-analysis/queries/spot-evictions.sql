-- ============================================================
-- Spot eviction and claim-expired counts (Azure)
-- ============================================================
-- Source tables: fxci.task_runs JOIN fxci.tasks (BigQuery via Redash)
-- Inputs: replace YYYY-MM-DD with start date
-- Output columns: submission_date, reason_resolved, azure_region,
--                 provisioner_id, worker_type, run_count
--
-- Reason codes:
--   worker-shutdown  = primary spot eviction signal — VM went away unexpectedly
--   claim-expired    = task waited too long for any worker to pick it up
--                      (queue starvation, often during/after capacity events)
--
-- Use cases:
--   - Detect Azure spot capacity events
--   - Correlate eviction rate with cost-per-task spikes
--   - Most reliable eviction signal in ephemeral-disk environments
--     (no VM-internal logs survive the eviction)
--
-- Post-processing notes:
--   The workerGroup NOT LIKE filters drop most non-Azure rows but a few
--   slip through. Filter results to Azure-region values only:
--     eastus2, centralus, westus2, canadacentral, centralindia, eastus,
--     northcentralus, northeurope, westus3, westus, southindia, uksouth
--   Exclude: mdc1 (releng hardware), bitbar (mobile device farm),
--            lambda, *-signing/*-balrog/*-beetmover (scriptworker k8s pools)
--
-- See: references/spot-evictions.md
-- ============================================================

SELECT
    tr.submission_date,
    tr.reason_resolved,
    tr.worker_group AS azure_region,
    SPLIT(t.task_queue_id, '/')[SAFE_OFFSET(0)] AS provisioner_id,
    SPLIT(t.task_queue_id, '/')[SAFE_OFFSET(1)] AS worker_type,
    count(*) AS run_count
FROM fxci.task_runs AS tr
INNER JOIN fxci.tasks AS t
    ON tr.task_id = t.task_id
   AND tr.submission_date = t.submission_date
WHERE
    tr.state = 'exception'
    AND tr.reason_resolved IN ('claim-expired', 'worker-shutdown')
    AND tr.submission_date >= 'YYYY-MM-DD'
    AND t.submission_date  >= 'YYYY-MM-DD'
    AND tr.worker_group NOT LIKE 'us-%'
    AND tr.worker_group NOT LIKE 'europe-%'
    AND tr.worker_group NOT LIKE 'northamerica-%'
GROUP BY tr.submission_date,
         tr.reason_resolved,
         tr.worker_group,
         provisioner_id,
         worker_type
ORDER BY tr.submission_date DESC,
         tr.reason_resolved ASC,
         run_count DESC
