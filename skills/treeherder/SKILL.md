---
name: treeherder
description: >
  Query Firefox Treeherder for CI job results using Mozilla's official treeherder-client library.
  Use after commits land to check test/build results.
  Triggers on "treeherder", "job results", "check tests", "ci status".
---

# Treeherder

Query Mozilla Treeherder for CI job results, pushes, performance alerts, and other CI data using the official `treeherder-client` library and direct REST API calls.

## Commands

### jobs - Query CI jobs for a push

```bash
# Query by revision
uv run scripts/query.py jobs --revision <COMMIT_HASH> --repo try

# Query by push ID
uv run scripts/query.py jobs --push-id <PUSH_ID> --repo autoland

# Filter by result status
uv run scripts/query.py jobs --revision <HASH> --result testfailed

# Filter by test name and platform
uv run scripts/query.py jobs --revision <HASH> --filter mochitest --platform linux

# Filter by tier (1, 2, or 3)
uv run scripts/query.py jobs --push-id 12345 --tier 1

# Summary only (no individual job listing)
uv run scripts/query.py jobs --revision <HASH> --summary-only
```

### pushes - List recent pushes

```bash
# List recent pushes for a repository
uv run scripts/query.py pushes --repo autoland --count 5

# Filter by author
uv run scripts/query.py pushes --repo try --author user@mozilla.com
```

### repos - List available repositories

```bash
uv run scripts/query.py repos
uv run scripts/query.py repos --json
```

### classifications - List failure classification types

```bash
uv run scripts/query.py classifications
uv run scripts/query.py classifications --json
```

### logs - Get log URLs for a job

```bash
# By job ID
uv run scripts/query.py logs --job-id 545634438 --repo autoland

# By job GUID
uv run scripts/query.py logs --job-guid "76b09e45-ed32-47e4-85b1-6f0945006abd/0" --repo autoland
```

### perf-frameworks - List performance frameworks

```bash
uv run scripts/query.py perf-frameworks
```

Common frameworks: talos (1), raptor (10), browsertime (13), awsy (4)

### perf-alerts - Query performance alert summaries

```bash
# Get recent alerts
uv run scripts/query.py perf-alerts --limit 5

# Filter by framework
uv run scripts/query.py perf-alerts --framework 1 --limit 10

# Filter by repository
uv run scripts/query.py perf-alerts --repo autoland

# Filter by status (untriaged, investigating, fixed, etc.)
uv run scripts/query.py perf-alerts --status untriaged
```

### job-details - Get detailed job information

```bash
uv run scripts/query.py job-details --job-guid "76b09e45-ed32-47e4-85b1-6f0945006abd/0"
```

## Legacy Usage

For backwards compatibility, the original syntax still works:

```bash
uv run scripts/query.py --revision <COMMIT_HASH> --repo try
uv run scripts/query.py --push-id <PUSH_ID> --filter mochitest
```

## Prerequisites

None - uses read-only access to Treeherder API.

**Note**: The Treeherder API requires a custom User-Agent header. The script handles this automatically.

## API Reference

The script wraps these Treeherder REST API endpoints:

| Endpoint | Description |
|----------|-------------|
| `/api/project/{repo}/push/` | Push/commit information |
| `/api/project/{repo}/jobs/` | CI job results |
| `/api/project/{repo}/job-log-url/` | Job log URLs |
| `/api/jobdetail/` | Detailed job metadata |
| `/api/repository/` | Available repositories |
| `/api/failureclassification/` | Failure classification types |
| `/api/performance/framework/` | Performance test frameworks |
| `/api/performance/alertsummary/` | Performance regression alerts |

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

## Documentation

- **Treeherder**: https://treeherder.mozilla.org/
- **treeherder-client Package**: https://pypi.org/project/treeherder-client/
- **Treeherder API Documentation**: https://treeherder.readthedocs.io/accessing_data.html
- **Source Code**: https://github.com/mozilla/treeherder
