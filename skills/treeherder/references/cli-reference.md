# Treeherder CLI Reference

This skill uses **treeherder-cli** for revision-based failure analysis, comparison, history, log searching, artifact downloads, and watch mode.

For features treeherder-cli does not cover (push listing, failures-by-bug, error-line bug suggestions, perf alerts, repository listing), call the Treeherder REST API directly. See `api-reference.md`.

---

# treeherder-cli

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
