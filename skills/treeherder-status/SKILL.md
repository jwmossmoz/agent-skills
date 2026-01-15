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
# This is done by os-integrations skill or manually with mach try
# Output shows: Landing job id: 173178

# 2. Wait a minute for landing, then check status
cd ~/.claude/skills/treeherder-status
uv run scripts/check_status.py 173178 marionette-integration

# 3. If still SUBMITTED, wait and check again
uv run scripts/check_status.py 173178 marionette-integration
```

## Limitations

- **No polling** - The script checks status once and exits. Run it multiple times as needed.
- **Timing** - Landing jobs typically take 1-2 minutes. Jobs may take longer to schedule and run.
- **Filter matching** - Job filter uses simple substring matching on job type names.

## Exit Codes

- `0` - Success (all jobs passed or still pending)
- `1` - Failure (one or more jobs failed)

## Dependencies

Requires `requests` library (included in uv environment).

