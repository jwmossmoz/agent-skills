---
name: treeherder-status
description: >
  Check the status of Firefox try pushes on Treeherder by landing job ID. Use after
  submitting try pushes with mach try to monitor job results. Queries Lando API for
  landing status and Treeherder API for job results. Triggers on "treeherder status",
  "check try push", "try results", "landing job", "job status", "check treeherder".
---

# Treeherder Status Checker

## Overview

This skill checks the status of Firefox try pushes on Treeherder. After submitting a try push with `mach try`, you get a landing job ID. Use this skill to check if the commit has landed and query the status of the jobs.

**When to use:** After running `mach try` commands (especially from the os-integrations skill) to check if jobs passed or failed.

**Note:** This skill does not need to be run from any specific directory - it only queries APIs.

## Quick Start

Check status by landing job ID:

```bash
cd ~/.claude/skills/treeherder-status
uv run scripts/check_status.py 173178
```

Filter for specific job types:

```bash
cd ~/.claude/skills/treeherder-status
uv run scripts/check_status.py 173178 marionette-integration
```

## How It Works

1. **Queries Lando API** - Checks if the landing job has completed and gets the commit ID
2. **Queries Treeherder API** - Gets the push information and all associated jobs
3. **Reports Status** - Shows job results with clear visual indicators

## Script Usage

```
python scripts/check_status.py <landing_job_id> [job_filter] [--repo REPO]
```

### Parameters

- `landing_job_id` (required): The Lando landing job ID from `mach try` output
- `job_filter` (optional): Filter jobs by name (e.g., "marionette-integration")
- `--repo` (optional): Repository name (default: "try")

### Examples

**Check all jobs for a try push:**
```bash
uv run scripts/check_status.py 173178
```

**Filter for marionette tests:**
```bash
uv run scripts/check_status.py 173178 marionette-integration
```

**Check a mozilla-central push:**
```bash
uv run scripts/check_status.py 173178 --repo mozilla-central
```

## Output Explained

### Landing Status

- **SUBMITTED** - The commit is still landing, try again in a few moments
- **LANDED** - The commit has landed and jobs are available

### Job Results

- ✅ **success** - Job passed
- ❌ **testfailed** - Tests failed
- 💥 **busted** - Build or infrastructure failure
- 🔄 **retry** - Job is being retried
- 🚫 **usercancel** - Job was cancelled
- 🏃 **running** - Job is currently running
- ⏳ **pending** - Job is waiting to start

## Common Workflow

After running a try push (e.g., from the os-integrations skill):

```bash
# 1. Submit try push (from Firefox repository)
cd ~/firefox && ./mach try fuzzy \
  --query "linux2404-64 marionette-integration" \
  --worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-alpha

# Output shows:
# Treeherder: https://treeherder.mozilla.org/jobs?repo=try&landoCommitID=173178
# Landing job id: 173178

# 2. Wait 1-2 minutes for landing to complete, then check status
cd ~/.claude/skills/treeherder-status
uv run scripts/check_status.py 173178 marionette-integration

# First check shows:
# Landing status: LANDED
# Commit ID: ed901414ea5ec1e188547898b31d133731e77588
# Marionette jobs: 2
# test-linux2404-64/opt-marionette-integration - unknown (unscheduled)
# test-linux2404-64/debug-marionette-integration - unknown (unscheduled)

# 3. Wait 10-30 minutes for builds to complete and tests to schedule
# Jobs remain "unscheduled" until the build jobs (linux64/opt, linux64/debug, etc.) finish
# Check again periodically:
uv run scripts/check_status.py 173178 marionette-integration

# Eventually shows:
# ✅ test-linux2404-64/opt-marionette-integration - success (completed)
# ❌ test-linux2404-64/debug-marionette-integration - testfailed (completed)
```

## Understanding Job States

**Typical job lifecycle:**
1. **unscheduled** - Job exists but waiting for dependencies (usually build jobs)
2. **pending** - Job is scheduled and waiting for a worker
3. **running** - Job is currently executing
4. **completed** - Job finished with a result (success, testfailed, busted, etc.)

**Important:** Test jobs cannot run until their build dependencies complete. For example, `test-linux2404-64/opt-marionette-integration` needs `build-linux64/opt` to finish first. This is why all jobs initially show as "unscheduled" - this is normal and expected.

## Limitations

- **No polling** - The script checks status once and exits. Run it multiple times as needed.
- **Timing expectations:**
  - Landing: 1-2 minutes to go from SUBMITTED to LANDED
  - Build jobs: 10-20 minutes to complete
  - Test jobs: Can only start after builds finish, then 5-15 minutes to run
  - Total: 15-30 minutes from try push to test results
- **Filter matching** - Job filter uses simple substring matching on job type names.

## Exit Codes

- `0` - Success (all jobs passed or still pending)
- `1` - Failure (one or more jobs failed)

## Dependencies

Requires `requests` library (included in uv environment).

