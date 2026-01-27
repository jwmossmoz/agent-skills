---
name: treeherder
description: >
  Query Firefox Treeherder for CI job results using Mozilla's official treeherder-client library.
  Use after commits land to check test/build results.
  Triggers on "treeherder", "job results", "check tests", "ci status".
---

# Treeherder

Query Mozilla Treeherder for CI job results, pushes, performance alerts, and other CI data using the `lumberjackth` CLI.

## Quick Start

```bash
# List repositories
lj repos

# List recent pushes for mozilla-central
lj pushes mozilla-central

# List jobs for a project
lj jobs autoland --push-id 12345

# Get details for a specific job
lj job autoland "abc123def/0" --logs

# Output as JSON
lj --json pushes mozilla-central -n 5
```

## Commands

### repos - List available repositories

```bash
lj repos              # Active repositories only
lj repos --all        # Include inactive
lj --json repos       # JSON output
```

### pushes - List recent pushes

```bash
lj pushes autoland                    # Recent pushes
lj pushes autoland -n 20              # Last 20 pushes
lj pushes try -r abc123               # Filter by revision
lj pushes autoland -a user@mozilla.com # Filter by author
```

### jobs - List jobs for a project

```bash
lj jobs autoland --push-id 12345           # Jobs for a push
lj jobs try --guid "abc123/0"              # Filter by GUID
lj jobs autoland --result testfailed       # Failed jobs only
lj jobs autoland --state running           # Running jobs
lj jobs autoland --tier 1                  # Tier 1 jobs only
lj jobs autoland -n 50                     # Limit to 50 jobs
```

### job - Get details for a specific job

```bash
lj job autoland "abc123def/0"              # Basic job details
lj job autoland "abc123def/0" --logs       # Include log URLs
lj --json job autoland "abc123def/0"       # JSON output
```

### perf-alerts - List performance alert summaries

```bash
lj perf-alerts                             # Recent alerts
lj perf-alerts -r autoland                 # Filter by repository
lj perf-alerts -f 1                        # Filter by framework (1=talos)
lj perf-alerts -n 20                       # Limit results
```

### perf-frameworks - List performance testing frameworks

```bash
lj perf-frameworks                         # List all frameworks
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

## Installation

The `lumberjackth` package is available on PyPI:

```bash
pip install lumberjackth
# or
uv pip install lumberjackth
# or use uvx for one-off commands
uvx lumberjackth repos
```

## References

- `references/sheriff-workflows.md` - Detailed sheriff workflow examples
- `references/api-reference.md` - Complete REST API documentation

## External Documentation

- **Treeherder**: https://treeherder.mozilla.org/
- **Sheriff Guide**: https://wiki.mozilla.org/Sheriffing/How_To/Treeherder
- **Job Visibility Policy**: https://wiki.mozilla.org/Sheriffing/Job_Visibility_Policy
- **lumberjackth**: https://pypi.org/project/lumberjackth/
- **API Docs**: https://treeherder.readthedocs.io/accessing_data.html
