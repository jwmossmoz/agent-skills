---
name: treeherder
description: >
  Query Firefox Treeherder for CI job results using Mozilla's official treeherder-client library.
  Use after commits land to check test/build results.
  Triggers on "treeherder", "job results", "check tests", "ci status".
---

# Treeherder

Query Mozilla Treeherder for CI job results, pushes, performance alerts, and other CI data. Designed to support sheriff workflows including monitoring tree health, finding unclassified failures, and investigating failed jobs.

## Quick Start

```bash
cd skills/treeherder

# Check health of recent pushes
uv run scripts/query.py health-summary --repo autoland

# Find unclassified failures
uv run scripts/query.py unclassified --repo autoland

# Get jobs for a revision
uv run scripts/query.py jobs --revision abc123 --repo autoland
```

## Commands

### Core Commands

#### jobs - Query CI jobs for a push

```bash
# Query by revision
uv run scripts/query.py jobs --revision <COMMIT_HASH> --repo try

# Query by push ID with filters
uv run scripts/query.py jobs --push-id <PUSH_ID> --repo autoland --result testfailed

# Filter by test name and platform
uv run scripts/query.py jobs --revision <HASH> --filter mochitest --platform linux

# Only unclassified failures
uv run scripts/query.py jobs --revision <HASH> --repo autoland --unclassified

# Filter by tier (1=sheriff-managed, 2=default, 3=hidden)
uv run scripts/query.py jobs --push-id 12345 --tier 1

# Summary only (no individual job listing)
uv run scripts/query.py jobs --revision <HASH> --summary-only

# Verbose output with task/job IDs
uv run scripts/query.py jobs --revision <HASH> --verbose
```

#### pushes - List recent pushes

```bash
uv run scripts/query.py pushes --repo autoland --count 5
uv run scripts/query.py pushes --repo try --author user@mozilla.com
```

#### repos - List available repositories

```bash
uv run scripts/query.py repos
uv run scripts/query.py repos --json
```

#### logs - Get log URLs for a job

```bash
uv run scripts/query.py logs --job-id 545634438 --repo autoland
uv run scripts/query.py logs --job-guid "76b09e45-ed32-47e4-85b1-6f0945006abd/0"
```

### Sheriff Commands

#### push-health - Get detailed push health status

```bash
uv run scripts/query.py push-health --revision <HASH> --repo autoland
uv run scripts/query.py push-health --push-id 1816157 --repo autoland
```

Shows pass/fail status for tests, builds, and linting with details on failures needing investigation.

#### health-summary - Quick health overview for recent pushes

```bash
uv run scripts/query.py health-summary --repo autoland --count 10
```

Shows T/B/L (Tests/Builds/Linting) status for each push at a glance.

#### unclassified - Find unclassified failures

```bash
# Scan recent pushes for unclassified failures
uv run scripts/query.py unclassified --repo autoland --push-count 10

# Include full job details
uv run scripts/query.py unclassified --repo autoland --verbose
```

#### bug-suggestions - Get suggested bugs for a failed job

```bash
uv run scripts/query.py bug-suggestions --job-id 545634438 --repo autoland

# Include all bug matches (not just open/recent)
uv run scripts/query.py bug-suggestions --job-id 545634438 --verbose
```

Shows error lines with matching Bugzilla bugs to help with classification.

#### errors - Get parsed error lines from a job log

```bash
uv run scripts/query.py errors --job-id 545634438 --repo autoland
```

Shows error lines with line numbers and highlights NEW failures (regressions).

#### notes - Get classification history for a job

```bash
uv run scripts/query.py notes --job-id 545634438 --repo autoland
```

Shows who classified the job, when, and what classification was applied.

#### platforms - List available machine platforms

```bash
uv run scripts/query.py platforms
```

### Performance Commands

#### perf-frameworks - List performance frameworks

```bash
uv run scripts/query.py perf-frameworks
```

Common frameworks: talos (1), raptor (10), browsertime (13), awsy (4)

#### perf-alerts - Query performance alert summaries

```bash
# Recent alerts from Talos
uv run scripts/query.py perf-alerts --framework 1 --limit 5

# Untriaged alerts only
uv run scripts/query.py perf-alerts --status untriaged

# Filter by repository
uv run scripts/query.py perf-alerts --repo autoland --limit 10
```

### Reference Commands

#### classifications - List failure classification types

```bash
uv run scripts/query.py classifications
```

#### job-details - Get detailed job metadata

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

## Failure Classifications

| ID | Name | Use Case |
|----|------|----------|
| 1 | not classified | Default for new failures |
| 2 | fixed by commit | Issue resolved by subsequent commit |
| 3 | expected fail | Known failure, expected behavior |
| 4 | intermittent | Flaky test with existing bug |
| 5 | infra | Infrastructure issue |
| 6 | new failure not classified | New failure, needs investigation |
| 7 | autoclassified intermittent | Auto-matched to known intermittent |
| 8 | intermittent needs bugid | Intermittent but needs bug filed |

## References

- `references/sheriff-workflows.md` - Detailed sheriff workflow examples
- `references/api-reference.md` - Complete REST API documentation

## External Documentation

- **Treeherder**: https://treeherder.mozilla.org/
- **Sheriff Guide**: https://wiki.mozilla.org/Sheriffing/How_To/Treeherder
- **Job Visibility Policy**: https://wiki.mozilla.org/Sheriffing/Job_Visibility_Policy
- **treeherder-client**: https://pypi.org/project/treeherder-client/
- **API Docs**: https://treeherder.readthedocs.io/accessing_data.html
