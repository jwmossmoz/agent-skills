---
name: treeherder-status
description: >
  Check the status of Firefox try pushes on Treeherder by landing job ID. Uses official
  Mozilla tools: lando-cli for landing job status and treeherder-client for job results.
  Triggers on "treeherder status", "check try push", "try results", "landing job", "job status".
---

# Treeherder Status Checker

## Overview

This skill provides documentation and utilities for checking Firefox try push status using official Mozilla Python packages:
- **lando-cli**: Check landing job status
- **treeherder-client**: Query job results from Treeherder

**When to use:** After running `mach try` commands to monitor if your commit landed and check test results.

## Prerequisites

### Lando CLI Configuration

To use `lando` commands, you need a config file at `~/.mozbuild/lando.toml`:

```toml
[auth]
api_token = "<TOKEN HERE>"
user_email = "your.email@mozilla.com"
```

Reach out to the Conduit team to request an API token.

## Quick Start

### Complete Workflow

After submitting a try push:

```bash
# 1. Check if the landing job completed
uvx --from lando-cli lando check-job 173397

# 2. Once landed, query Treeherder for job results by revision
uv run ~/.claude/skills/treeherder-status/scripts/query-treeherder.py \
  --revision abc123def456 \
  --repo try

# 3. Filter for specific test types
uv run ~/.claude/skills/treeherder-status/scripts/query-treeherder.py \
  --revision abc123def456 \
  --filter mochitest-chrome
```

## Official Tool Usage

### lando-cli

The `lando` command provides access to Mozilla's Lando automation API.

**Check landing job status:**
```bash
uvx --from lando-cli lando check-job <JOB_ID>
```

**Example:**
```bash
# After mach try, you get a landing job ID like 173397
uvx --from lando-cli lando check-job 173397
```

**Output shows:**
- Job status (SUBMITTED, LANDED, FAILED, etc.)
- Commit revision (once landed)
- Any error messages

### treeherder-client

The `treeherder-client` package provides Python API for querying Treeherder.

**Query with convenience script:**
```bash
# By revision
uv run ~/.claude/skills/treeherder-status/scripts/query-treeherder.py \
  --revision abc123def456 \
  --repo try

# By push ID
uv run ~/.claude/skills/treeherder-status/scripts/query-treeherder.py \
  --push-id 12345 \
  --repo try

# With job filter
uv run ~/.claude/skills/treeherder-status/scripts/query-treeherder.py \
  --revision abc123 \
  --filter "marionette-integration"
```

**Direct Python usage:**
```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["treeherder-client"]
# ///

from thclient import TreeherderClient

client = TreeherderClient()

# Get push by revision
data = client._get_json(
    client.PUSH_ENDPOINT,
    project="try",
    revision="abc123def456"
)
push = data["results"][0]
push_id = push["id"]

# Get jobs for push
data = client._get_json(
    client.JOBS_ENDPOINT,
    project="try",
    push_id=push_id
)
jobs = data["results"]

for job in jobs:
    print(f"{job['job_type_name']}: {job['result']}")
```

## Job Status Reference

### Landing Status (Lando)

- **SUBMITTED** - Landing job queued, commit not landed yet (wait 1-2 minutes)
- **LANDED** - Commit successfully landed, jobs scheduling on Treeherder
- **FAILED** - Landing failed due to errors

### Job Results (Treeherder)

- ✅ **success** - Job passed
- ❌ **testfailed** - Tests failed
- 💥 **busted** - Build or infrastructure failure
- 🔄 **retry** - Job is being retried
- 🚫 **usercancel** - Job was cancelled
- 🏃 **running** - Job is currently executing
- ⏳ **pending** - Job scheduled, waiting for worker
- ❓ **unknown/unscheduled** - Job exists but waiting for dependencies (e.g., build jobs)

## Typical Workflow Timeline

After `mach try` submission:

1. **0-2 minutes**: Landing job processes (SUBMITTED → LANDED)
2. **2-5 minutes**: Jobs appear on Treeherder as "unscheduled"
3. **10-20 minutes**: Build jobs complete
4. **15-30 minutes**: Test jobs run and complete

**Note:** Test jobs show "unscheduled" until their build dependencies finish. This is normal.

## Common Use Cases

### After os-integrations Try Push

```bash
# 1. Submit try push with worker overrides
cd ~/firefox
./mach try fuzzy \
  --query 'windows11 24h2 debug mochitest-chrome' \
  --preset os-integration \
  --worker-override win11-64-24h2=gecko-t/win11-64-24h2-alpha

# Output shows landing job ID: 173397

# 2. Check landing status
uvx --from lando-cli lando check-job 173397
# Output: Status LANDED, revision: c081f3f7d219...

# 3. Query Treeherder for results
uv run ~/.claude/skills/treeherder-status/scripts/query-treeherder.py \
  --revision c081f3f7d219 \
  --filter mochitest-chrome

# 4. Check results periodically until tests complete
```

### Monitoring Specific Test Suites

```bash
# Check only marionette tests
uv run ~/.claude/skills/treeherder-status/scripts/query-treeherder.py \
  --revision abc123 \
  --filter marionette-integration

# Check only mochitest-chrome tests
uv run ~/.claude/skills/treeherder-status/scripts/query-treeherder.py \
  --revision abc123 \
  --filter mochitest-chrome
```

## Advanced: Direct API Usage

### Using lando-cli as a Library

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["lando-cli"]
# ///

# lando-cli is primarily a CLI tool
# For API access, use direct HTTP requests to Lando API
# See: https://api.lando.services.mozilla.com/landing_jobs/{job_id}
```

### Using treeherder-client for Complex Queries

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["treeherder-client"]
# ///

from thclient import TreeherderClient

client = TreeherderClient(timeout=30)

# Get multiple pushes
pushes = client.get_pushes("try", count=10)

# Get all jobs for a push with filters
jobs = client.get_jobs(
    "try",
    push_id=12345,
    result="testfailed",  # Only failed jobs
    job_type_name="mochitest"  # Job name contains "mochitest"
)
```

## Benefits of Official Tools

Using `lando-cli` and `treeherder-client` instead of custom wrappers:
- ✅ **Maintained by Mozilla** - Stays up-to-date with API changes
- ✅ **Isolated with uvx/uv** - No global package pollution
- ✅ **Standard interfaces** - Works like other Mozilla developer tools
- ✅ **Better error handling** - Built-in retry logic and error messages
- ✅ **Documentation** - Official docs and community support

## Troubleshooting

### "lando: command not found"
```bash
# Use full uvx command
uvx --from lando-cli lando check-job 173397
```

### "No API token configured"
Create `~/.mozbuild/lando.toml` with your API token (request from Conduit team).

### "No push found for this revision"
- Wait 1-2 minutes after landing for Treeherder to index the push
- Verify the revision hash is correct
- Check if the commit landed successfully with `lando check-job`

### Jobs show "unscheduled"
This is normal. Test jobs wait for build dependencies to complete (10-20 minutes).

## Resources

- **lando-cli**: [PyPI](https://pypi.org/project/lando-cli/) | [GitHub](https://github.com/mozilla-conduit/lando-api)
- **treeherder-client**: [PyPI](https://pypi.org/project/treeherder-client/) | [GitHub](https://github.com/mozilla/treeherder)
- **Treeherder**: https://treeherder.mozilla.org/
- **Lando API**: https://api.lando.services.mozilla.com/

