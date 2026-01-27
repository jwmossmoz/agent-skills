---
name: treeherder
description: >
  Query Firefox Treeherder for CI job results using the lumberjackth CLI.
  Use after commits land to check test/build results.
  Triggers on "treeherder", "job results", "check tests", "ci status".
---

# Treeherder

Query Mozilla Treeherder for CI job results, pushes, performance alerts, and other CI data using the `lumberjackth` CLI.

## Quick Start

```bash
# List repositories
uvx --from lumberjackth lj repos

# List recent pushes for mozilla-central
uvx --from lumberjackth lj pushes mozilla-central

# List jobs for a project
uvx --from lumberjackth lj jobs autoland --push-id 12345

# Get details for a specific job
uvx --from lumberjackth lj job autoland "abc123def/0" --logs

# Output as JSON
uvx --from lumberjackth lj --json pushes mozilla-central -n 5
```

## Commands

### repos - List available repositories

```bash
uvx --from lumberjackth lj repos              # Active repositories only
uvx --from lumberjackth lj repos --all        # Include inactive
uvx --from lumberjackth lj --json repos       # JSON output
```

### pushes - List recent pushes

```bash
uvx --from lumberjackth lj pushes autoland                    # Recent pushes
uvx --from lumberjackth lj pushes autoland -n 20              # Last 20 pushes
uvx --from lumberjackth lj pushes try -r abc123               # Filter by revision
uvx --from lumberjackth lj pushes autoland -a user@mozilla.com # Filter by author
```

### jobs - List jobs for a project

```bash
uvx --from lumberjackth lj jobs autoland --push-id 12345           # Jobs for a push
uvx --from lumberjackth lj jobs try --guid "abc123/0"              # Filter by GUID
uvx --from lumberjackth lj jobs autoland --result testfailed       # Failed jobs only
uvx --from lumberjackth lj jobs autoland --state running           # Running jobs
uvx --from lumberjackth lj jobs autoland --tier 1                  # Tier 1 jobs only
uvx --from lumberjackth lj jobs autoland -n 50                     # Limit to 50 jobs
```

### job - Get details for a specific job

```bash
uvx --from lumberjackth lj job autoland "abc123def/0"              # Basic job details
uvx --from lumberjackth lj job autoland "abc123def/0" --logs       # Include log URLs
uvx --from lumberjackth lj --json job autoland "abc123def/0"       # JSON output
```

### perf-alerts - List performance alert summaries

```bash
uvx --from lumberjackth lj perf-alerts                             # Recent alerts
uvx --from lumberjackth lj perf-alerts -r autoland                 # Filter by repository
uvx --from lumberjackth lj perf-alerts -f 1                        # Filter by framework (1=talos)
uvx --from lumberjackth lj perf-alerts -n 20                       # Limit results
```

### perf-frameworks - List performance testing frameworks

```bash
uvx --from lumberjackth lj perf-frameworks                         # List all frameworks
```

Common frameworks: talos (1), raptor (10), browsertime (13), awsy (4)

## Global Options

| Option | Description |
|--------|-------------|
| `-s, --server URL` | Treeherder server URL (default: https://treeherder.mozilla.org) |
| `--json` | Output as JSON instead of tables |
| `--version` | Show version |

## Python API

For programmatic access, use the lumberjackth Python client:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["lumberjackth"]
# ///
from lumberjackth import TreeherderClient

client = TreeherderClient()

# List repositories
repos = client.get_repositories()
for repo in repos:
    print(f"{repo.name} ({repo.dvcs_type})")

# Get pushes
pushes = client.get_pushes("mozilla-central", count=10)
for push in pushes:
    print(f"{push.revision[:12]} by {push.author}")

# Get jobs for a push
jobs = client.get_jobs("mozilla-central", push_id=pushes[0].id)
for job in jobs:
    print(f"{job.job_type_name}: {job.result}")

# Async support
async with TreeherderClient() as client:
    repos = await client.get_repositories_async()
```

Run with: `uv run script.py`

## Common Job Results

| Result | Meaning |
|--------|---------|
| `success` | Job passed |
| `testfailed` | Test failures |
| `busted` | Build/infra failure |
| `retry` | Job was retried |
| `usercancel` | Cancelled by user |
| `running` | Currently executing |
| `pending` | Waiting to run |

## Job Tiers

| Tier | Description | Sheriff Action |
|------|-------------|----------------|
| 1 | Sheriff-managed, shown by default | Close tree or backout on failure |
| 2 | Shown by default | File bugs, fix within 2 business days |
| 3 | Hidden by default | Job owner responsible |

## Prerequisites

None - uses `uvx` for zero-install execution. No authentication required (read-only API).

## References

- `references/sheriff-workflows.md` - Detailed sheriff workflow examples
- `references/api-reference.md` - Complete REST API documentation

## External Documentation

- **Treeherder**: https://treeherder.mozilla.org/
- **Sheriff Guide**: https://wiki.mozilla.org/Sheriffing/How_To/Treeherder
- **Job Visibility Policy**: https://wiki.mozilla.org/Sheriffing/Job_Visibility_Policy
- **lumberjackth**: https://pypi.org/project/lumberjackth/
- **API Docs**: https://treeherder.readthedocs.io/accessing_data.html
