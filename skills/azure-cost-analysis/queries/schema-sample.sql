-- ============================================================
-- Schema sample query
-- ============================================================
-- Use to discover the columns and sample row structure of any
-- BigQuery table in the taskclusteretl or fxci datasets.
--
-- Inputs: replace <table> with the table you want to inspect
--
-- Common tables worth inspecting:
--   taskclusteretl.derived_task_summary
--   taskclusteretl.derived_workertype_costs
--   fxci.tasks
--   fxci.task_runs
--   fxci.task_run_costs        (note: requires submission_date partition filter)
--   fxci.worker_costs
--
-- For partitioned tables, you must include a filter on the partition column
-- (usually `created`, `submission_date`, or `usage_start_date`).
--
-- See: references/taskcluster-task-counting.md
-- ============================================================

SELECT *
FROM <table>
WHERE created >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
LIMIT 10
