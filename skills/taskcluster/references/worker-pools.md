# Worker Pool Management

This guide shows how to manage Taskcluster worker pools using the native `taskcluster api` CLI commands.

## Worker Pool Operations

### List Workers in a Pool

```bash
# Get all workers in a pool
taskcluster api workerManager listWorkersForWorkerPool <WORKER_POOL_ID>

# Example: gecko-t/win11-64-24h2-alpha
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha

# Filter by state
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq -r '.workers[] | select(.state == "running") | "\(.workerGroup)/\(.workerId)"'

# Count workers by state
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq '[.workers[] | .state] | group_by(.) | map({state: .[0], count: length})'
```

### Worker States

Workers can be in these states:
- **requested** - Provisioning has been requested but worker hasn't started
- **running** - Worker is active and can claim tasks
- **stopping** - Worker is in the process of shutting down
- **stopped** - Worker has been terminated

### Terminate Workers

```bash
# Remove a single worker
taskcluster api workerManager removeWorker <WORKER_POOL_ID> <WORKER_GROUP> <WORKER_ID>

# Example
taskcluster api workerManager removeWorker gecko-t/win11-64-24h2-alpha uksouth vm-abc123
```

### Bulk Worker Termination

```bash
# Terminate all running workers
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq -r '.workers[] | select(.state == "running") | "\(.workerPoolId) \(.workerGroup) \(.workerId)"' | \
  while read pool group worker; do
    echo "Terminating: $worker"
    taskcluster api workerManager removeWorker "$pool" "$group" "$worker"
  done

# Terminate all requested workers
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq -r '.workers[] | select(.state == "requested") | "\(.workerPoolId) \(.workerGroup) \(.workerId)"' | \
  while read pool group worker; do
    echo "Terminating: $worker"
    taskcluster api workerManager removeWorker "$pool" "$group" "$worker"
  done

# Terminate all active workers (running + requested)
for state in running requested; do
  taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
    jq -r '.workers[] | select(.state == "'$state'") | "\(.workerPoolId) \(.workerGroup) \(.workerId)"' | \
    while read pool group worker; do
      echo "Terminating $state worker: $worker"
      taskcluster api workerManager removeWorker "$pool" "$group" "$worker"
    done
done
```

## Task Queue Operations

### List Tasks by Worker Pool

```bash
# List claimed tasks (currently running)
taskcluster api queue listClaimedTasks <WORKER_POOL_ID>

# Get task IDs only
taskcluster api queue listClaimedTasks gecko-t/win11-64-24h2-alpha | \
  jq -r '.tasks[].taskId'

# Show task names
taskcluster api queue listClaimedTasks gecko-t/win11-64-24h2-alpha | \
  jq -r '.tasks[] | "\(.taskId) - \(.task.metadata.name)"'

# List pending tasks (waiting to be claimed)
taskcluster api queue listPendingTasks <WORKER_POOL_ID>

# Count pending and claimed tasks
echo "Claimed: $(taskcluster api queue listClaimedTasks gecko-t/win11-64-24h2-alpha | jq '.tasks | length')"
echo "Pending: $(taskcluster api queue listPendingTasks gecko-t/win11-64-24h2-alpha | jq '.tasks | length')"
```

### Cancel Tasks by Worker Pool

```bash
# Cancel all claimed tasks
taskcluster api queue listClaimedTasks gecko-t/win11-64-24h2-alpha | \
  jq -r '.tasks[].taskId' | \
  while read task_id; do
    echo "Canceling task: $task_id"
    taskcluster api queue cancelTask "$task_id"
  done

# Cancel all pending tasks
taskcluster api queue listPendingTasks gecko-t/win11-64-24h2-alpha | \
  jq -r '.tasks[].taskId' | \
  while read task_id; do
    echo "Canceling task: $task_id"
    taskcluster api queue cancelTask "$task_id"
  done
```

## Emergency Shutdown

Complete shutdown of a worker pool (cancel all tasks, terminate all workers):

```bash
#!/bin/bash
POOL_ID="gecko-t/win11-64-24h2-alpha"

echo "=== Canceling claimed tasks ==="
taskcluster api queue listClaimedTasks "$POOL_ID" | \
  jq -r '.tasks[].taskId' | \
  while read task_id; do
    echo "Canceling: $task_id"
    taskcluster api queue cancelTask "$task_id"
  done

echo "=== Canceling pending tasks ==="
taskcluster api queue listPendingTasks "$POOL_ID" | \
  jq -r '.tasks[].taskId' | \
  while read task_id; do
    echo "Canceling: $task_id"
    taskcluster api queue cancelTask "$task_id"
  done

echo "=== Terminating running workers ==="
taskcluster api workerManager listWorkersForWorkerPool "$POOL_ID" | \
  jq -r '.workers[] | select(.state == "running") | "\(.workerPoolId) \(.workerGroup) \(.workerId)"' | \
  while read pool group worker; do
    echo "Terminating: $worker"
    taskcluster api workerManager removeWorker "$pool" "$group" "$worker"
  done

echo "=== Terminating requested workers ==="
taskcluster api workerManager listWorkersForWorkerPool "$POOL_ID" | \
  jq -r '.workers[] | select(.state == "requested") | "\(.workerPoolId) \(.workerGroup) \(.workerId)"' | \
  while read pool group worker; do
    echo "Terminating: $worker"
    taskcluster api workerManager removeWorker "$pool" "$group" "$worker"
  done

echo "=== Shutdown complete ==="
taskcluster api workerManager listWorkersForWorkerPool "$POOL_ID" | \
  jq '[.workers[] | .state] | group_by(.) | map({state: .[0], count: length})'
```

## Worker Health Monitoring

### Check Worker Status

```bash
# Show worker distribution by state
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq -r '.workers[] | .state' | sort | uniq -c

# Find idle workers (running but no recent tasks)
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq -r '.workers[] | select(.state == "running" and (.recentTasks | length == 0)) | .workerId'

# Show workers with their recent tasks
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq -r '.workers[] | select(.state == "running") | "\(.workerId): \(.recentTasks[0].taskId // "idle")"'
```

### Quarantine Workers

```bash
# Quarantine a problematic worker (prevents it from claiming new tasks)
taskcluster api queue quarantineWorker gecko-t/win11-64-24h2-alpha <WORKER_GROUP> <WORKER_ID>

# Example
taskcluster api queue quarantineWorker gecko-t/win11-64-24h2-alpha uksouth vm-abc123 \
  --quarantineUntil "2026-02-06T00:00:00.000Z"
```

## Common Use Cases

### Worker Pool Maintenance

Before deploying a new worker image or making infrastructure changes:

```bash
# 1. Check current pool status
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq '[.workers[] | .state] | group_by(.) | map({state: .[0], count: length})'

# 2. Drain the pool (cancel pending tasks, let running tasks complete)
taskcluster api queue listPendingTasks gecko-t/win11-64-24h2-alpha | \
  jq -r '.tasks[].taskId' | \
  while read task_id; do
    taskcluster api queue cancelTask "$task_id"
  done

# 3. Wait for running tasks to complete, or force cancel if needed
# Monitor: taskcluster api queue listClaimedTasks gecko-t/win11-64-24h2-alpha

# 4. Terminate workers
# (see bulk termination examples above)
```

### Debugging Worker Issues

```bash
# Find which worker is running a specific task
TASK_ID="abc123..."
taskcluster api queue status "$TASK_ID" | jq -r '.status.runs[-1] | "\(.workerGroup)/\(.workerId)"'

# Get worker details
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq '.workers[] | select(.workerId == "vm-abc123")'

# Check what tasks a worker has run recently
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq '.workers[] | select(.workerId == "vm-abc123") | .recentTasks'
```

### Image Rollout Validation

When validating a new worker image:

```bash
# Check worker pool capacity
taskcluster api workerManager listWorkersForWorkerPool gecko-t/win11-64-24h2-alpha | \
  jq '[.workers[] | select(.state == "running")] | length'

# Monitor task success rate
# (Use with treeherder skill or lumberjackth for detailed analysis)

# If rollback needed, terminate all workers (will respawn with previous image)
# (see emergency shutdown example above)
```

## Related Commands

- **tc.py cancel** - Cancel individual tasks (use for single task operations)
- **tc.py status** - Check task status
- **tc.py retrigger** - Retrigger failed tasks after worker pool recovery

## References

- [Taskcluster Worker Manager API](https://docs.taskcluster.net/docs/reference/core/worker-manager)
- [Taskcluster Queue API](https://docs.taskcluster.net/docs/reference/platform/queue)
- [Worker Lifecycle](https://docs.taskcluster.net/docs/manual/design/workers)
