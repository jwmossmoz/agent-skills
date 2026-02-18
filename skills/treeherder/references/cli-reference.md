# Treeherder CLI Reference

This skill uses two CLI tools. Use **treeherder-cli** as the primary tool for revision-based failure analysis, and **lumberjackth** for push browsing, failures-by-bug, error suggestions, and perf alerts.

---

# treeherder-cli (Primary)

Rust CLI for fetching and analyzing Firefox CI failures from Treeherder.

## Installation

```bash
cargo install --git https://github.com/padenot/treeherder-cli
```

## Usage

```bash
treeherder-cli <REVISION> [OPTIONS]
treeherder-cli --history <TEST_NAME> [OPTIONS]
treeherder-cli --similar-history <JOB_ID> [OPTIONS]
treeherder-cli --use-cache [OPTIONS]
```

## Options

### Core

| Option | Description |
|--------|-------------|
| `<REVISION>` | Revision hash to query (positional argument) |
| `--json` | Output results as JSON |
| `--repo <REPO>` | Repository to query (default: autoland) |

### Filtering

| Option | Description |
|--------|-------------|
| `--filter <PATTERN>` | Filter by job name (regex) |
| `--platform <PATTERN>` | Filter by platform (regex) |
| `--group-by <FIELD>` | Group failures (e.g., `test` for cross-platform view) |
| `--include-intermittent` | Include intermittent test failures in results |
| `--duration-min <SECONDS>` | Filter to jobs with duration >= N seconds |

### Comparison and History

| Option | Description |
|--------|-------------|
| `--compare <REVISION>` | Compare against another revision to find regressions |
| `--history <TEST_NAME>` | Examine test occurrence patterns across builds |
| `--history-count <N>` | Number of historical records to retrieve |
| `--similar-history <JOB_ID>` | Get job history via Treeherder's similar_jobs API |
| `--similar-count <N>` | Number of similar job results to return |

### Logs and Artifacts

| Option | Description |
|--------|-------------|
| `--fetch-logs` | Download log files for matching jobs |
| `--pattern <REGEX>` | Search pattern within fetched logs |
| `--download-artifacts` | Download build artifacts |
| `--artifact-pattern <PATTERN>` | Filter artifacts by name pattern |
| `--cache-dir <PATH>` | Directory for cached logs |
| `--use-cache` | Use previously cached log data |

### Monitoring

| Option | Description |
|--------|-------------|
| `--watch` | Continuously poll for status updates |
| `--watch-interval <SECONDS>` | Polling frequency (default: 300s / 5 minutes) |
| `--notify` | Trigger notification on state changes |

### Performance

| Option | Description |
|--------|-------------|
| `--perf` | Retrieve performance and resource metrics |

## Examples

```bash
# Basic: get failed jobs for a revision
treeherder-cli a13b9fc22101 --json

# Filter by job name or platform
treeherder-cli a13b9fc22101 --filter "mochitest" --json
treeherder-cli a13b9fc22101 --platform "linux.*64" --json

# Group failures by test name (cross-platform view)
treeherder-cli a13b9fc22101 --group-by test --json

# Compare revisions to find regressions
treeherder-cli a13b9fc22101 --compare b2c3d4e5f678 --json

# Check test history for intermittent detection
treeherder-cli --history "test_audio_playback" --history-count 10 --repo try --json

# Include intermittent failures
treeherder-cli a13b9fc22101 --include-intermittent --json

# Filter long-running jobs (>1 hour)
treeherder-cli a13b9fc22101 --duration-min 3600 --json

# Fetch logs with pattern matching
treeherder-cli a13b9fc22101 --fetch-logs --pattern "ASSERTION|CRASH" --json

# Download artifacts
treeherder-cli a13b9fc22101 --download-artifacts --artifact-pattern "screenshot|errorsummary"

# Get performance/resource data
treeherder-cli a13b9fc22101 --perf --json

# Watch mode with notification
treeherder-cli a13b9fc22101 --watch --notify
treeherder-cli a13b9fc22101 --watch --watch-interval 60

# Cache logs for repeated queries
treeherder-cli a13b9fc22101 --fetch-logs --cache-dir ./logs
treeherder-cli --use-cache --cache-dir ./logs --pattern "ERROR" --json

# Switch repository
treeherder-cli a13b9fc22101 --repo try --json

# Efficient job history via similar_jobs API
treeherder-cli --similar-history 543981186 --similar-count 100 --repo autoland --json
```

For cross-branch comparisons based on the same `job_type_name`, see `references/similar-jobs-comparison.md`.

---

# Lumberjackth CLI (Secondary)

Python CLI for broader Treeherder API access. Use for features treeherder-cli doesn't cover: push listing, failures-by-bug, error suggestions, perf alerts, and result/state/tier filtering.

## Installation

```bash
# Zero-install execution with uvx (preferred)
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

List jobs for a project with filtering.

```bash
lj jobs autoland --push-id 12345           # Jobs for a push
lj jobs try -r abc123                      # Jobs for a revision
lj jobs autoland --result testfailed       # Failed jobs only
lj jobs autoland --state running           # Running jobs
lj jobs autoland --tier 1                  # Tier 1 jobs only
lj jobs autoland -p "linux.*64"            # Filter by platform regex
lj jobs autoland -f "mochitest"            # Filter by job name regex
lj jobs autoland --duration-min 60         # Jobs running 60+ seconds
lj jobs try --push-id 12345 --watch        # Watch mode
```

**Options:**
- `--push-id` - Filter by push ID
- `-r, --revision` - Filter by revision
- `--guid` - Filter by job GUID
- `--result` - Filter by result (success, testfailed, busted, etc.)
- `--state` - Filter by state (pending, running, completed)
- `--tier` - Filter by tier (1, 2, or 3)
- `-p, --platform` - Filter by platform (regex pattern)
- `-f, --filter` - Filter by job name (regex pattern)
- `--duration-min` - Filter to jobs with duration >= N seconds
- `-n, --count` - Number of jobs (default: 20, or all when --push-id specified)
- `-w, --watch` - Watch for job updates (refreshes periodically)
- `-i, --interval` - Refresh interval in seconds when using --watch (default: 30)

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
lj perf-frameworks
```

Common frameworks:
- talos (1)
- raptor (10)
- browsertime (13)
- awsy (4)

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
