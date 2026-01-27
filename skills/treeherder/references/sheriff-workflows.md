# Sheriff Workflows with Treeherder

This document describes common sheriff workflows and how to accomplish them using the lumberjackth CLI.

## Quick Reference

| Task | Command |
|------|---------|
| List recent pushes | `lj pushes autoland -n 10` |
| Get jobs for a push | `lj jobs autoland --push-id <id>` |
| Filter failed jobs | `lj jobs autoland --push-id <id> --result testfailed` |
| Get job details with logs | `lj job autoland "<guid>" --logs` |
| Performance alerts | `lj perf-alerts -r autoland` |

## Workflow 1: Monitoring Tree Health

### Check recent pushes

```bash
# List last 10 pushes on autoland
lj pushes autoland -n 10

# Filter by author
lj pushes autoland -a user@mozilla.com
```

Output shows push ID, revision, author, and commit count:
```
                        Pushes for autoland
┏━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ ID      ┃ Revision     ┃ Author              ┃ Time                ┃ Commits ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ 1815584 │ 12ae7cd09e4d │ user@mozilla.com    │ 2026-01-27 10:30:00 │       1 │
└─────────┴──────────────┴─────────────────────┴─────────────────────┴─────────┘
```

### Get jobs for a specific push

```bash
# All jobs for a push
lj jobs autoland --push-id 1815584

# Failed jobs only
lj jobs autoland --push-id 1815584 --result testfailed

# Tier 1 jobs (sheriff-managed)
lj jobs autoland --push-id 1815584 --tier 1
```

## Workflow 2: Investigating Failed Jobs

### Step 1: Find failed jobs

```bash
# Get all failed jobs for a push
lj jobs autoland --push-id 1815584 --result testfailed

# Or filter by platform
lj --json jobs autoland --push-id 1815584 --result testfailed | jq '.[] | select(.platform | contains("linux"))'
```

### Step 2: Get job details and logs

```bash
# Get detailed info for a specific job
lj job autoland "abc123def/0" --logs
```

Output includes:
- Job ID and type
- Platform and state
- Result and tier
- Submit/start/end timestamps
- Duration
- Task ID with Taskcluster link
- Log URLs

### Step 3: View logs in Taskcluster

The job output includes direct Taskcluster links:
```
  Task ID: abc123TaskId
  Task URL: https://firefox-ci-tc.services.mozilla.com/tasks/abc123TaskId
```

## Workflow 3: Filtering by Platform and Tier

### Filter by result state

```bash
# Only failed tests
lj jobs autoland --push-id 12345 --result testfailed

# Only build failures
lj jobs autoland --push-id 12345 --result busted

# Running jobs
lj jobs autoland --push-id 12345 --state running
```

### Filter by tier

```bash
# Tier 1 jobs only (sheriff-managed, require backout on failure)
lj jobs autoland --push-id 12345 --tier 1

# Tier 2 jobs (shown by default, bugs filed but no auto-backout)
lj jobs autoland --push-id 12345 --tier 2
```

## Workflow 4: Performance Alerts

### Check for recent performance regressions

```bash
# Recent alerts
lj perf-alerts -n 10

# Filter by repository
lj perf-alerts -r autoland -n 10

# Filter by framework (1=talos, 10=raptor, 13=browsertime)
lj perf-alerts -f 1 -n 10
```

### List performance frameworks

```bash
lj perf-frameworks
```

Common frameworks:
- 1: talos
- 4: awsy (memory)
- 10: raptor
- 13: browsertime

## Workflow 5: JSON Output for Scripting

All commands support `--json` for machine-readable output:

```bash
# Get pushes as JSON
lj --json pushes autoland -n 5

# Get failed jobs as JSON and filter with jq
lj --json jobs autoland --push-id 12345 --result testfailed | jq '.[].job_type_name'

# Get job details as JSON
lj --json job autoland "abc123/0" --logs
```

## Job Tiers Reference

| Tier | Description | Sheriff Action |
|------|-------------|----------------|
| 1 | Sheriff-managed, shown by default | Close tree or backout on failure |
| 2 | Shown by default | File bugs, fix within 2 business days |
| 3 | Hidden by default | Job owner responsible |

## Job Results Reference

| Result | Meaning |
|--------|---------|
| `success` | Job passed |
| `testfailed` | Test failures |
| `busted` | Build/infra failure |
| `retry` | Job was retried |
| `usercancel` | Cancelled by user |
| `running` | Currently executing |
| `pending` | Waiting to run |

## Python API for Advanced Workflows

For workflows not covered by the CLI, use the Python API:

```python
from lumberjackth import TreeherderClient

client = TreeherderClient()

# Get jobs and filter for unclassified failures
jobs = client.get_jobs("autoland", push_id=12345, result="testfailed")
unclassified = [j for j in jobs if j.failure_classification_id == 1]

for job in unclassified:
    print(f"{job.job_type_name} - {job.platform}")
    if job.task_id:
        print(f"  Task: https://firefox-ci-tc.services.mozilla.com/tasks/{job.task_id}")
```

## External Resources

- [Treeherder](https://treeherder.mozilla.org/)
- [Sheriff How-To Guide](https://wiki.mozilla.org/Sheriffing/How_To/Treeherder)
- [Job Visibility Policy](https://wiki.mozilla.org/Sheriffing/Job_Visibility_Policy)
- [Test Disabling Policy](https://wiki.mozilla.org/EngineeringProductivity/Test_Disabling_Policy)
- [lumberjackth on PyPI](https://pypi.org/project/lumberjackth/)
