# Lumberjackth CLI Reference

Complete command-line reference for the `lumberjackth` CLI tool.

## Installation

```bash
# Zero-install execution with uvx
uvx --from lumberjackth lj <command>

# Or install globally
pip install lumberjackth
lj <command>
```

## Global Options

| Option | Description |
|--------|-------------|
| `-s, --server URL` | Treeherder server URL (default: https://treeherder.mozilla.org) |
| `--json` | Output as JSON instead of tables |
| `--version` | Show version |

---

## repos

List available repositories.

```bash
lj repos              # Active repositories only
lj repos --all        # Include inactive
lj --json repos       # JSON output
```

**Options:**
- `--active/--all` - Show only active repositories (default: active)

---

## pushes

List recent pushes for a project.

```bash
lj pushes autoland                      # Recent pushes
lj pushes autoland -n 20                # Last 20 pushes
lj pushes try -r abc123                 # Filter by revision
lj pushes autoland -a user@mozilla.com  # Filter by author
```

**Options:**
- `-n, --count` - Number of pushes to show (default: 10)
- `-r, --revision` - Filter by revision
- `-a, --author` - Filter by author email

---

## jobs

List jobs for a project with powerful filtering.

```bash
lj jobs autoland --push-id 12345           # Jobs for a push
lj jobs try --guid "abc123/0"              # Filter by GUID
lj jobs autoland --result testfailed       # Failed jobs only
lj jobs autoland --state running           # Running jobs
lj jobs autoland --tier 1                  # Tier 1 jobs only
lj jobs autoland -p "linux.*64"            # Filter by platform regex
lj jobs autoland -f "mochitest"            # Filter by job name regex
lj jobs autoland --duration-min 60         # Jobs running 60+ seconds
lj jobs autoland -n 50                     # Limit to 50 jobs
```

**Options:**
- `--push-id` - Filter by push ID
- `--guid` - Filter by job GUID
- `--result` - Filter by result (success, testfailed, busted, etc.)
- `--state` - Filter by state (pending, running, completed)
- `--tier` - Filter by tier (1, 2, or 3)
- `-p, --platform` - Filter by platform (regex pattern)
- `-f, --filter` - Filter by job name (regex pattern)
- `--duration-min` - Filter to jobs with duration >= N seconds
- `-n, --count` - Number of jobs (default: 20, or all when --push-id specified)

---

## job

Get details for a specific job.

```bash
lj job autoland "abc123def/0"              # Basic job details
lj job autoland "abc123def/0" --logs       # Include log URLs
lj --json job autoland "abc123def/0"       # JSON output
```

**Options:**
- `--logs` - Show log URLs

---

## log

Fetch and search job logs.

```bash
lj log autoland 545896732                  # View full log
lj log autoland 545896732 --tail 100       # Last 100 lines
lj log autoland 545896732 --head 50        # First 50 lines
lj log autoland 545896732 -p "ERROR|FAIL"  # Search with regex
lj log autoland 545896732 -p "assertion" -c 5  # With context lines
lj --json log autoland 545896732 -p "TEST-UNEXPECTED"  # JSON output
```

**Options:**
- `-p, --pattern` - Regex pattern to search for
- `-c, --context` - Number of context lines around matches
- `--log-name` - Log to fetch (default: live_backing_log)
- `--head` - Show only the first N lines
- `--tail` - Show only the last N lines

---

## failures

Query test failures by Bugzilla bug ID. Useful for investigating intermittent failures.

```bash
lj failures 2012615                        # All failures in last 7 days
lj failures 2012615 -t autoland            # Filter by repository
lj failures 2012615 -p "windows.*24h2"     # Filter by platform regex
lj failures 2012615 -b asan                # Filter by build type
lj failures 2012615 -s 2026-01-26 -e 2026-01-28  # Date range
lj failures 2012615 -n 10                  # Limit results
lj --json failures 2012615                 # JSON output
```

**Options:**
- `-t, --tree` - Repository filter (all, autoland, mozilla-central, etc.)
- `-p, --platform` - Filter by platform (regex pattern)
- `-b, --build-type` - Filter by build type (regex pattern)
- `-s, --startday` - Start date (YYYY-MM-DD), defaults to 7 days ago
- `-e, --endday` - End date (YYYY-MM-DD), defaults to today
- `-n, --count` - Limit number of results

---

## errors

Show error lines and bug suggestions for a failed job.

```bash
lj errors autoland 545896732               # Show errors + suggestions
lj errors autoland 545896732 --no-suggestions  # Just errors
lj --json errors autoland 545896732        # JSON output
```

**Options:**
- `--suggestions/--no-suggestions` - Show bug suggestions (default: on)

---

## perf-alerts

List performance alert summaries.

```bash
lj perf-alerts                             # Recent alerts
lj perf-alerts -r autoland                 # Filter by repository
lj perf-alerts -f 1                        # Filter by framework (1=talos)
lj perf-alerts -n 20                       # Limit results
```

**Options:**
- `-r, --repository` - Filter by repository
- `-f, --framework` - Filter by framework ID
- `-n, --limit` - Number of alerts to show

---

## perf-frameworks

List performance testing frameworks.

```bash
lj perf-frameworks                         # List all frameworks
```

Common frameworks:
- talos (1)
- raptor (10)
- browsertime (13)
- awsy (4)

---

## Python API

For programmatic access:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["lumberjackth"]
# ///
from lumberjackth import TreeherderClient

client = TreeherderClient()

# Get pushes
pushes = client.get_pushes("mozilla-central", count=10)

# Get jobs for a push
jobs = client.get_jobs("mozilla-central", push_id=pushes[0].id)

# Fetch job logs
log_content = client.get_job_log("autoland", job_id=12345)
matches = client.search_job_log("autoland", job_id=12345, pattern="ERROR")

# Query failures by bug
failures = client.get_failures_by_bug(2012615, tree="autoland")

# Async support
async with TreeherderClient() as client:
    repos = await client.get_repositories_async()
```

---

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
