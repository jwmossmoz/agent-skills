# Common Queries

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
