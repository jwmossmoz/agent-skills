# fxci Schema

Taskcluster CI task execution and cost data in BigQuery.

## Tables

### tasks

Core task metadata (lightweight). Use this over `task_definitions` when the tags struct has what you need.

| Column | Type | Description |
|--------|------|-------------|
| `task_id` | STRING | Unique task identifier |
| `task_group_id` | STRING | Group of related tasks |
| `task_queue_id` | STRING | Queue the task was submitted to |
| `scheduler_id` | STRING | Scheduler that created the task |
| `submission_date` | DATE | Partition key — always filter on this |
| `tags` | STRUCT | See tags struct below |

**tags struct fields:**
| Field | Type |
|-------|------|
| `created_for_user` | STRING |
| `kind` | STRING |
| `label` | STRING |
| `os` | STRING |
| `owned_by` | STRING |
| `project` | STRING |
| `trust_domain` | STRING |
| `worker_implementation` | STRING |
| `test_suite` | STRING |
| `test_platform` | STRING |
| `test_variant` | STRING |

### task_definitions

Full task definitions including payloads. Heavy table — prefer `tasks` when possible.

| Column | Type | Description |
|--------|------|-------------|
| `taskId` | STRING | Unique task identifier (camelCase) |
| `taskGroupId` | STRING | Group of related tasks |
| `taskQueueId` | STRING | Queue the task was submitted to |
| `provisionerId` | STRING | Provisioner |
| `workerType` | STRING | Worker type |
| `schedulerId` | STRING | Scheduler |
| `projectId` | STRING | Project identifier |
| `priority` | STRING | Task priority |
| `retries` | INT64 | Max retries |
| `requires` | STRING | Task requirement type |
| `dependencies` | ARRAY\<STRING\> | Task IDs this depends on |
| `routes` | ARRAY\<STRING\> | Pulse routing keys |
| `scopes` | ARRAY\<STRING\> | Required scopes |
| `extra` | JSON | Extra task data |
| `metadata` | JSON | Task metadata (name, description, owner, source) |
| `payload` | JSON | Full task payload |
| `tags` | JSON | Task tags (JSON, not struct) |
| `created` | TIMESTAMP | When the task was created |
| `deadline` | TIMESTAMP | Task deadline |
| `expires` | TIMESTAMP | When the task expires |
| `submission_date` | DATE | Partition key |

### task_runs

Individual run records per task. A task can have multiple runs (retries).

| Column | Type | Description |
|--------|------|-------------|
| `task_id` | STRING | Task identifier |
| `run_id` | INT64 | Run number (0-indexed) |
| `state` | STRING | Run state |
| `reason_created` | STRING | Why the run was created |
| `reason_resolved` | STRING | Why the run resolved |
| `scheduled` | TIMESTAMP | When the run was scheduled |
| `started` | TIMESTAMP | When the run started |
| `resolved` | TIMESTAMP | When the run resolved |
| `worker_group` | STRING | Worker group that ran it |
| `worker_id` | STRING | Worker that ran it |
| `submission_date` | DATE | Partition key |

### task_run_costs

Cost per task run.

| Column | Type | Description |
|--------|------|-------------|
| `task_id` | STRING | Task identifier |
| `run_id` | INT64 | Run number |
| `run_cost` | FLOAT64 | Cost in USD |
| `submission_date` | DATE | Partition key |

### worker_costs

GCP instance-level costs.

| Column | Type | Description |
|--------|------|-------------|
| `project` | STRING | GCP project |
| `name` | STRING | Instance name |
| `zone` | STRING | GCP zone |
| `instance_id` | STRING | Instance identifier |
| `total_cost` | FLOAT64 | Total cost in USD |
| `usage_start_date` | DATE | Usage date |

### worker_metrics

Worker uptime metrics.

| Column | Type | Description |
|--------|------|-------------|
| `instance_id` | STRING | Instance identifier |
| `project` | STRING | GCP project |
| `zone` | STRING | GCP zone |
| `uptime` | FLOAT64 | Uptime value |
| `interval_start_time` | TIMESTAMP | Interval start |
| `interval_end_time` | TIMESTAMP | Interval end |
| `submission_date` | DATE | Partition key |

## Joins

- `tasks` ↔ `task_runs` ↔ `task_run_costs` — join on `task_id` (and `run_id` for runs↔costs)
- `tasks` ↔ `task_definitions` — join on `tasks.task_id = task_definitions.taskId`
- `worker_costs` ↔ `worker_metrics` — join on `instance_id`

## Performance

Always filter by `submission_date` on every table — it's the partition key. Queries without this filter will scan the full table and be slow/expensive.
