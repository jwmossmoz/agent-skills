# Taskcluster Skill Examples

Common usage patterns for the Taskcluster skill based on Mozilla CI workflows.

Always set the root URL first:

```bash
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
TC=/Users/jwmoss/github_moz/agent-skills/skills/taskcluster/scripts/tc.py
```

## Basic Task Operations

### Check Task Status

```bash
taskcluster task status <TASK_ID>
```

### View Task Logs

```bash
# Stream the log
taskcluster task log <TASK_ID>

# Pipe to tail for the last 100 lines
taskcluster task log <TASK_ID> | tail -100
```

### Get Full Task Definition

```bash
# Full task definition as JSON
taskcluster task def <TASK_ID>

# Extract worker type and payload
taskcluster task def <TASK_ID> | jq '.workerType, .payload'

# Check worker pool and env vars
taskcluster task def <TASK_ID> | jq '.provisionerId, .workerType, .payload.env'
```

### List Task Artifacts (with URLs)

The native CLI only lists artifact names. Use `tc.py` when you need URLs, content types, or expiry:

```bash
# Full artifact listing with URLs and metadata
uv run "$TC" artifacts <TASK_ID>

# Extract log artifact URLs
uv run "$TC" artifacts <TASK_ID> | jq -r '.artifacts[] | select(.name | contains("log")) | .url'

# For a specific run
uv run "$TC" artifacts <TASK_ID> --run 0
```

## Task Group Operations

### List Tasks in a Group

```bash
# All tasks
taskcluster group list --all <TASK_GROUP_ID>

# Only failed tasks
taskcluster group list --failed <TASK_GROUP_ID>

# Only running tasks
taskcluster group list --running <TASK_GROUP_ID>
```

### Group Status Summary (State Counts)

```bash
# Native group status (text output)
taskcluster group status <TASK_GROUP_ID>

# Structured JSON with totalTasks and stateCounts breakdown (for scripting)
uv run "$TC" group-status <TASK_GROUP_ID>
uv run "$TC" group-status <TASK_GROUP_ID> | jq '.taskSummary'
```

## Debugging Failed Tasks

### Workflow: Investigate Task Failure

```bash
# 1. Check task status
taskcluster task status <TASK_ID>

# 2. View the task log
taskcluster task log <TASK_ID> | tail -100

# 3. Get task definition to check worker pool and payload
taskcluster task def <TASK_ID> | jq '.workerType, .payload'

# 4. Check if other tasks in the group also failed
TASK_GROUP_ID=$(taskcluster task def <TASK_ID> | jq -r '.taskGroupId')
taskcluster group list --failed $TASK_GROUP_ID
```

### Worker Pool Configuration Issues

```bash
# Get worker type and provisioner from failed task
taskcluster task def <TASK_ID> | jq -r '.workerType, .provisionerId'

# Check the full payload
taskcluster task def <TASK_ID> | jq '.payload'

# Check task state and reason for failure
taskcluster api queue status <TASK_ID> | jq '.status.runs[-1].reasonResolved'
```

## Retriggering Tasks

### Retrigger a Failed Task

```bash
# Retrigger via in-tree action — preserves dependencies (correct for Firefox CI)
uv run "$TC" retrigger <TASK_ID>

# Rerun the same task (same task ID, no dependency handling needed)
taskcluster task rerun <TASK_ID>
```

**Important**: `taskcluster task retrigger` clears dependencies and breaks Firefox CI tasks that
depend on upstream artifacts. Always use `uv run "$TC" retrigger` for Firefox CI tasks.

### Bulk Retrigger Failed Tasks in a Group

```bash
taskcluster group list --failed <TASK_GROUP_ID> | \
  awk '{print $1}' | \
  while read task_id; do
    echo "Retriggering $task_id"
    uv run "$TC" retrigger "$task_id"
  done
```

## Cancel Operations

### Cancel a Single Task

```bash
taskcluster task cancel <TASK_ID>
```

### Cancel All Tasks in a Group

```bash
# Efficient API approach (seal first, then cancel)
taskcluster api queue sealTaskGroup <TASK_GROUP_ID>
taskcluster api queue cancelTaskGroup <TASK_GROUP_ID>

# Or via CLI (slower, cancels one by one)
taskcluster group cancel --force <TASK_GROUP_ID>
```

## Integration with Treeherder

### Workflow: From Treeherder URL to Task Details

```bash
REVISION="ed901414ea5ec1e188547898b31d133731e77588"

# 1. Use treeherder-cli for failure analysis
treeherder-cli $REVISION --json

# 2. Pick a failed task ID and investigate
TASK_ID="dtMnwBMHSc6kq5VGqJz0fw"
taskcluster task status $TASK_ID
taskcluster task log $TASK_ID
```

## Real-World Scenarios

### Scenario 1: Alpha Worker Pool Testing

When testing new worker pools (e.g., win11-64-24h2-alpha):

```bash
# 1. Trigger a try push with os-integrations skill
cd ~/firefox && uv run /Users/jwmoss/github_moz/agent-skills/skills/os-integrations/scripts/run_try.py win11-24h2

# 2. Get the task group ID from the output
TASK_GROUP_ID="<from mach try output>"

# 3. Monitor the task group
taskcluster group status $TASK_GROUP_ID

# 4. Check for failures
taskcluster group list --failed $TASK_GROUP_ID

# 5. Investigate a specific failure
FAILED_TASK=$(taskcluster group list --failed $TASK_GROUP_ID | head -1 | awk '{print $1}')
taskcluster task log $FAILED_TASK
taskcluster task def $FAILED_TASK | jq '.payload, .workerType'
```

### Scenario 2: Verifying Worker Image Updates

After updating worker images in fxci-config:

```bash
# Find tasks using the new image and check their state
taskcluster group list --all <TASK_GROUP_ID>

# Check what worker ran a specific task
taskcluster api queue status <TASK_ID> | jq '.status.runs[-1] | {workerGroup, workerId, state}'

# Get full definition to check image tags
taskcluster task def <TASK_ID> | jq '.task.tags // .tags'
```

### Scenario 3: Analyzing Intermittent Test Failures

```bash
# 1. Check historical pass/fail rate for the test (is it usually flaky?)
treeherder-cli --history "mochitest-plain" --history-count 20 --repo autoland --json

# 2. Compare the failed job against similar past jobs
treeherder-cli --similar-history <JOB_ID> --similar-count 50 --repo autoland --json

# 3. Check error lines for known bug suggestions
uvx --from lumberjackth lj errors autoland <JOB_ID>

# 4. Check run history for the specific task
taskcluster api queue status $TASK_ID | jq '.status.runs[] | {runId, state, reasonResolved}'

# 5. If triage suggests intermittent, confirm in CI
uv run "$TC" confirm-failures $TASK_ID

# 6. If triage suggests regression, backfill to find the culprit push
uv run "$TC" backfill $TASK_ID
```
