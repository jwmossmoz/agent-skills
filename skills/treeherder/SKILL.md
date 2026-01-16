---
name: treeherder
description: >
  Query Firefox Treeherder for CI job results using Mozilla's official treeherder-client library.
  Use after commits land to check test/build results.
  Triggers on "treeherder", "job results", "check tests", "ci status".
---

# Treeherder

## Overview

Query Mozilla Treeherder for CI job results using the official `treeherder-client` Python library. After your commit lands (check with the `lando` skill), use this to see build and test results.

**When to use:** After verifying your commit landed (via lando skill) to check if builds passed and tests succeeded.

## Quick Start

```bash
# Query by revision (after commit lands)
uv run ~/.claude/skills/treeherder/scripts/query.py \
  --revision c081f3f7d219 \
  --repo try

# Filter for specific test types
uv run ~/.claude/skills/treeherder/scripts/query.py \
  --revision c081f3f7d219 \
  --filter mochitest-chrome \
  --repo try

# Query by push ID directly
uv run ~/.claude/skills/treeherder/scripts/query.py \
  --push-id 12345 \
  --repo try
```

## Job Status Reference

- ✅ **success** - Job passed
- ❌ **testfailed** - Tests failed
- 💥 **busted** - Build or infrastructure failure
- 🔄 **retry** - Job is being retried
- 🚫 **usercancel** - Job was cancelled
- 🏃 **running** - Job is currently executing
- ⏳ **pending** - Job scheduled, waiting for worker
- ❓ **unknown/unscheduled** - Waiting for dependencies (e.g., builds)

## Complete Workflow

```bash
# 1. Submit try push (from Firefox repository)
cd ~/firefox
./mach try fuzzy --query 'windows11 24h2 debug mochitest-chrome'

# Output: Landing job id: 173397

# 2. Wait for landing (lando skill)
uvx --from lando-cli lando check-job 173397

# Output: Status LANDED, Revision: c081f3f7d219...

# 3. Query Treeherder for job results (this skill)
uv run ~/.claude/skills/treeherder/scripts/query.py \
  --revision c081f3f7d219 \
  --filter mochitest-chrome

# 4. Check periodically until tests complete (15-30 minutes total)
```

## Typical Timeline

After commit lands:

1. **2-5 minutes**: Jobs appear on Treeherder as "unscheduled"
2. **10-20 minutes**: Build jobs complete
3. **15-30 minutes**: Test jobs complete with final results

**Note:** Test jobs show "unscheduled" until their build dependencies finish. This is normal.

## Script Options

```bash
uv run ~/.claude/skills/treeherder/scripts/query.py --help
```

**Parameters:**
- `--revision <HASH>` - Commit revision to query
- `--push-id <ID>` - Push ID to query
- `--repo <NAME>` - Repository name (default: try)
- `--filter <TEXT>` - Filter jobs by name substring

**Exit codes:**
- `0` - All jobs passed or still pending
- `1` - One or more jobs failed

## Common Filters

```bash
# Check only mochitest-chrome tests
--filter mochitest-chrome

# Check only marionette tests
--filter marionette-integration

# Check only Windows 11 tests
--filter windows11

# Check only debug builds
--filter debug
```

## Direct Python Usage

For custom queries, use `treeherder-client` directly:

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
    revision="c081f3f7d219"
)
push = data["results"][0]

# Get jobs for push
data = client._get_json(
    client.JOBS_ENDPOINT,
    project="try",
    push_id=push["id"]
)

for job in data["results"]:
    print(f"{job['job_type_name']}: {job['result']}")
```

## Advanced Queries

### Get only failed jobs

```python
jobs = client.get_jobs(
    "try",
    push_id=12345,
    result="testfailed"
)
```

### Get jobs by type pattern

```python
jobs = client.get_jobs(
    "try",
    push_id=12345,
    job_type_name="mochitest"
)
```

### Query multiple repositories

```python
for repo in ["try", "autoland", "mozilla-central"]:
    data = client._get_json(
        client.PUSH_ENDPOINT,
        project=repo,
        revision="abc123"
    )
    if data.get("results"):
        print(f"Found in {repo}")
```

## Integration with Other Skills

### With os-integrations + lando

Complete workflow for testing alpha images:

```bash
# 1. Submit try push with worker overrides (os-integrations)
cd ~/firefox
./mach try fuzzy \
  --query 'windows11 24h2 debug' \
  --preset os-integration \
  --worker-override win11-64-24h2=gecko-t/win11-64-24h2-alpha

# Landing job id: 173397

# 2. Check landing (lando)
uvx --from lando-cli lando check-job 173397

# Revision: c081f3f7d219...

# 3. Query results (treeherder)
uv run ~/.claude/skills/treeherder/scripts/query.py \
  --revision c081f3f7d219 \
  --filter mochitest-chrome
```

## Troubleshooting

### "No push found for this revision"

- **Wait longer**: Treeherder indexing takes 2-5 minutes after landing
- **Verify revision**: Check the revision hash is correct
- **Check landing**: Ensure commit landed successfully with `lando` skill

### Jobs show "unscheduled"

**Normal behavior.** Test jobs wait for build dependencies (10-20 minutes).

Check again later:

```bash
# Wait 15-20 minutes, then re-query
uv run ~/.claude/skills/treeherder/scripts/query.py \
  --revision c081f3f7d219 \
  --filter your-test-type
```

### Script not found

Use the full path:

```bash
uv run ~/.claude/skills/treeherder/scripts/query.py --help
```

Or from the skill directory:

```bash
cd ~/.claude/skills/treeherder
uv run scripts/query.py --help
```

## Benefits

- ✅ **Official Mozilla library** - Maintained by the Treeherder team
- ✅ **No installation** - Use with `uv run` for isolated execution
- ✅ **Flexible queries** - Filter by revision, push ID, job type, result
- ✅ **Exit codes** - Scriptable for CI/CD workflows
- ✅ **Direct API access** - Full Python library for custom queries

## Resources

- **treeherder-client**: [PyPI](https://pypi.org/project/treeherder-client/) | [GitHub](https://github.com/mozilla/treeherder)
- **Treeherder**: https://treeherder.mozilla.org/
- **Treeherder API Docs**: https://treeherder.readthedocs.io/
- **Mozilla CI Docs**: https://firefox-source-docs.mozilla.org/
