# Taskcluster Skill Examples

Common usage patterns for the Taskcluster skill based on Mozilla CI workflows.

## Basic Task Operations

### Check Task Status

```bash
# Using task ID directly
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py status dtMnwBMHSc6kq5VGqJz0fw

# Using full Taskcluster URL (from Treeherder or other sources)
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py status \
  https://firefox-ci-tc.services.mozilla.com/tasks/dtMnwBMHSc6kq5VGqJz0fw
```

### View Task Logs

```bash
# Stream the log for a task
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py log dtMnwBMHSc6kq5VGqJz0fw

# View log for a specific run (if task was rerun)
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py log dtMnwBMHSc6kq5VGqJz0fw --run 0
```

### List Task Artifacts

```bash
# List all artifacts for a task
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py artifacts dtMnwBMHSc6kq5VGqJz0fw

# Pipe to jq to extract specific artifact URLs
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py artifacts dtMnwBMHSc6kq5VGqJz0fw | \
  jq -r '.artifacts[] | select(.name | contains("log")) | .url'
```

### Get Full Task Definition

```bash
# Useful for debugging worker pool configuration issues
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py definition dtMnwBMHSc6kq5VGqJz0fw

# Extract worker pool information
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py definition dtMnwBMHSc6kq5VGqJz0fw | \
  jq -r '.payload.env.TASKCLUSTER_WORKER_POOL_ID'
```

## Task Group Operations

### List All Tasks in a Group

```bash
# Get all tasks from a task group (useful for viewing all jobs from a push)
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py group-list fuCPrKG2T62-4YH1tWYa7Q

# Filter to show only failed tasks
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py group-list fuCPrKG2T62-4YH1tWYa7Q | \
  jq '.tasks[] | select(.status.state == "failed") | {taskId, label: .task.metadata.name}'
```

### Check Group Status Summary

```bash
# Get overall status of a task group
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py group-status fuCPrKG2T62-4YH1tWYa7Q

# Count tasks by state
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py group-status fuCPrKG2T62-4YH1tWYa7Q | \
  jq '.taskGroupId as $id | .status | group_by(.state) | map({state: .[0].state, count: length})'
```

## Debugging Failed Tasks

### Workflow: Investigate Task Failure

```bash
# 1. Check task status
uv run tc.py status dtMnwBMHSc6kq5VGqJz0fw

# 2. View the task log
uv run tc.py log dtMnwBMHSc6kq5VGqJz0fw | tail -100

# 3. Get task definition to check worker pool and payload
uv run tc.py definition dtMnwBMHSc6kq5VGqJz0fw | jq '.workerType, .payload'

# 4. Check if other tasks in the group also failed
TASK_GROUP_ID=$(uv run tc.py definition dtMnwBMHSc6kq5VGqJz0fw | jq -r '.taskGroupId')
uv run tc.py group-list $TASK_GROUP_ID | \
  jq '.tasks[] | select(.status.state == "failed") | .task.metadata.name'
```

### Worker Pool Configuration Issues

Common pattern when debugging worker pool errors (like E8ads_v6 NVMe issues):

```bash
# Get worker type and pool from failed task
uv run tc.py definition <TASK_ID> | jq -r '.workerType, .provisionerId'

# Check the full payload to see what's being requested
uv run tc.py definition <TASK_ID> | jq '.payload'

# Check task state and reason for failure
uv run tc.py status <TASK_ID> | jq '.status.runs[-1].reasonResolved'
```

## Retriggering Tasks

### Retrigger a Failed Task

```bash
# Retrigger creates a NEW task with updated timestamps
# Use this when you've fixed the issue and want to try again
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py retrigger dtMnwBMHSc6kq5VGqJz0fw

# Output will include the new task ID
```

### Rerun a Task

```bash
# Rerun attempts to run the SAME task again (same task ID)
# Use this when the task failed due to intermittent issues
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py rerun dtMnwBMHSc6kq5VGqJz0fw
```

### Bulk Retrigger Failed Tasks in a Group

```bash
# Get all failed task IDs from a group and retrigger them
uv run tc.py group-list fuCPrKG2T62-4YH1tWYa7Q | \
  jq -r '.tasks[] | select(.status.state == "failed") | .status.taskId' | \
  while read task_id; do
    echo "Retriggering $task_id"
    uv run tc.py retrigger "$task_id"
  done
```

## Integration with Treeherder

### Workflow: From Treeherder URL to Task Details

```bash
# 1. Start with a Treeherder URL
REVISION="ed901414ea5ec1e188547898b31d133731e77588"

# 2. Use treeherder skill to get task IDs
uv run ~/github_moz/agent-skills/skills/treeherder/scripts/query.py --revision $REVISION --repo try

# 3. Pick a failed task ID and investigate
TASK_ID="dtMnwBMHSc6kq5VGqJz0fw"
uv run tc.py status $TASK_ID
uv run tc.py log $TASK_ID
```

## Cancel Operations

### Cancel a Single Task

```bash
# Cancel a running or pending task
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py cancel dtMnwBMHSc6kq5VGqJz0fw
```

### Cancel All Tasks in a Group

```bash
# Cancel all tasks in a task group (useful for stopping an unwanted push)
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py group-cancel fuCPrKG2T62-4YH1tWYa7Q
```

### Cancel All Pending Tasks in a Group

```bash
# Cancel only pending tasks (leave running tasks alone)
uv run tc.py group-list fuCPrKG2T62-4YH1tWYa7Q | \
  jq -r '.tasks[] | select(.status.state == "pending") | .status.taskId' | \
  while read task_id; do
    uv run tc.py cancel "$task_id"
  done
```

## Advanced Queries with jq

### Find Tasks by Worker Type

```bash
# List all tasks using a specific worker type
uv run tc.py group-list fuCPrKG2T62-4YH1tWYa7Q | \
  jq '.tasks[] | select(.task.workerType == "gecko-t-win11-64-24h2-amd") | .task.metadata.name'
```

### Get Task Duration Statistics

```bash
# Calculate average task duration in a group
uv run tc.py group-list fuCPrKG2T62-4YH1tWYa7Q | \
  jq '.tasks[] | select(.status.state == "completed") |
      .status.runs[-1] |
      {
        name: .taskId,
        duration: (((.resolved | fromdate) - (.started | fromdate)) / 60)
      }'
```

### Find Tasks with Specific Artifacts

```bash
# Find all tasks that have crash reports
uv run tc.py group-list fuCPrKG2T62-4YH1tWYa7Q | \
  jq -r '.tasks[].status.taskId' | \
  while read task_id; do
    uv run tc.py artifacts "$task_id" 2>/dev/null | \
      jq -r --arg tid "$task_id" \
        'select(.artifacts[]? | .name | contains("crash")) | $tid'
  done
```

## Real-World Scenarios

### Scenario 1: Alpha Worker Pool Testing

When testing new worker pools (e.g., win11-64-24h2-alpha):

```bash
# 1. Trigger a try push with os-integrations skill
cd ~/firefox && uv run ~/github_moz/agent-skills/skills/os-integrations/scripts/run_try.py win11-24h2

# 2. Get the task group ID from the output
TASK_GROUP_ID="<from mach try output>"

# 3. Monitor the task group
uv run tc.py group-status $TASK_GROUP_ID

# 4. Check for failures
uv run tc.py group-list $TASK_GROUP_ID | \
  jq '.tasks[] | select(.status.state == "failed")'

# 5. Investigate a specific failure
FAILED_TASK=$(uv run tc.py group-list $TASK_GROUP_ID | \
  jq -r '.tasks[] | select(.status.state == "failed") | .status.taskId' | head -1)

uv run tc.py log $FAILED_TASK
uv run tc.py definition $FAILED_TASK | jq '.payload, .workerType'
```

### Scenario 2: Verifying Worker Image Updates

After updating worker images in fxci-config:

```bash
# 1. Find tasks using the new image
uv run tc.py group-list <TASK_GROUP_ID> | \
  jq '.tasks[] |
      {
        taskId: .status.taskId,
        workerType: .task.workerType,
        workerGroup: .status.runs[-1].workerGroup
      }'

# 2. Check if tasks are running on expected workers
uv run tc.py definition <TASK_ID> | \
  jq '.payload.image // .payload.osGroups // .task.tags'
```

### Scenario 3: Analyzing Intermittent Test Failures

```bash
# 1. Get all runs of a specific test
uv run tc.py group-list $TASK_GROUP_ID | \
  jq '.tasks[] | select(.task.metadata.name | contains("mochitest-plain"))'

# 2. Check which runs failed
uv run tc.py status $TASK_ID | \
  jq '.status.runs[] | {runId, state: .state, resolved: .reasonResolved}'

# 3. Compare logs between successful and failed runs
uv run tc.py log $TASK_ID --run 0 > run0.log
uv run tc.py log $TASK_ID --run 1 > run1.log
diff run0.log run1.log
```
