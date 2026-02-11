# Sheriff Workflows with Treeherder

This document describes common sheriff workflows using **treeherder-cli** (primary) and **lumberjackth** (secondary).

## Quick Reference

| Task | Tool | Command |
|------|------|---------|
| Get failures for a revision | treeherder-cli | `treeherder-cli abc123 --json` |
| Compare revisions | treeherder-cli | `treeherder-cli abc123 --compare def456 --json` |
| Check test history | treeherder-cli | `treeherder-cli --history "test_name" --json` |
| Fetch logs with search | treeherder-cli | `treeherder-cli abc123 --fetch-logs --pattern "ERROR"` |
| Watch a revision | treeherder-cli | `treeherder-cli abc123 --watch --notify` |
| List recent pushes | lumberjackth | `lj pushes autoland -n 10` |
| Filter by result/tier | lumberjackth | `lj jobs autoland --push-id 123 --result testfailed --tier 1` |
| Get job details with logs | lumberjackth | `lj job autoland "<guid>" --logs` |
| Failures by bug ID | lumberjackth | `lj failures 2012615 -t autoland` |
| Error suggestions | lumberjackth | `lj errors autoland 545896732` |
| Performance alerts | lumberjackth | `lj perf-alerts -r autoland` |

## Workflow 1: Investigating Failures on a Push

### Step 1: Find the revision

```bash
# List recent pushes on autoland
uvx --from lumberjackth lj pushes autoland -n 10

# Filter by author
uvx --from lumberjackth lj pushes autoland -a user@mozilla.com
```

### Step 2: Analyze failures with treeherder-cli

```bash
# Get all failures for the revision
treeherder-cli a13b9fc22101 --json

# Filter by platform or job name
treeherder-cli a13b9fc22101 --platform "windows.*24h2" --json
treeherder-cli a13b9fc22101 --filter "mochitest" --json

# Group failures by test name to see cross-platform impact
treeherder-cli a13b9fc22101 --group-by test --json

# Include intermittent failures for full picture
treeherder-cli a13b9fc22101 --include-intermittent --json
```

### Step 3: Get logs and error details

```bash
# Fetch logs and search for patterns
treeherder-cli a13b9fc22101 --fetch-logs --pattern "ASSERTION|CRASH" --json

# Or use lumberjackth for error lines with bug suggestions
uvx --from lumberjackth lj errors autoland 545896732
```

## Workflow 2: Regression Detection

### Compare a suspicious revision against its parent

```bash
# Compare two revisions to identify regressions
treeherder-cli a13b9fc22101 --compare b2c3d4e5f678 --json
```

### Check test history for intermittent detection

```bash
# Is this test historically flaky?
treeherder-cli --history "browser_all_files_flash.js" --history-count 20 --json

# Check via Treeherder's similar_jobs API
treeherder-cli --similar-history 543981186 --similar-count 100 --repo autoland --json
```

## Workflow 3: Monitoring a Try Push

### Watch with treeherder-cli

```bash
# Watch for updates, get notified on completion
treeherder-cli abc123 --repo try --watch --notify

# Shorter polling interval
treeherder-cli abc123 --repo try --watch --watch-interval 60
```

### Watch with lumberjackth (more granular filtering)

```bash
# Watch with auto-refresh, filtered by result
uvx --from lumberjackth lj jobs try -r abc123 --result testfailed --watch -i 60
```

## Workflow 4: Investigating Intermittent Failures by Bug

Use lumberjackth for bug-based failure queries:

```bash
# All failures for a bug in last 7 days
uvx --from lumberjackth lj failures 2012615

# Filter by repository and platform
uvx --from lumberjackth lj failures 2012615 -t autoland -p "windows.*24h2"

# Filter by build type
uvx --from lumberjackth lj failures 2012615 -b asan

# Specific date range
uvx --from lumberjackth lj failures 2012615 -s 2026-01-26 -e 2026-01-28

# JSON output for scripting
uvx --from lumberjackth lj --json failures 2012615
```

## Workflow 5: Filtering Jobs by Result, State, and Tier

Use lumberjackth for detailed job filtering:

```bash
# Only failed tests
uvx --from lumberjackth lj jobs autoland --push-id 12345 --result testfailed

# Only build failures
uvx --from lumberjackth lj jobs autoland --push-id 12345 --result busted

# Running jobs
uvx --from lumberjackth lj jobs autoland --push-id 12345 --state running

# Tier 1 jobs only (sheriff-managed, require backout on failure)
uvx --from lumberjackth lj jobs autoland --push-id 12345 --tier 1

# Combine filters
uvx --from lumberjackth lj jobs autoland --push-id 12345 --result testfailed --tier 1 -p "linux.*64"
```

## Workflow 6: Downloading Artifacts

```bash
# Download all artifacts for a revision
treeherder-cli a13b9fc22101 --download-artifacts

# Filter to specific artifact types
treeherder-cli a13b9fc22101 --download-artifacts --artifact-pattern "screenshot|errorsummary"
```

## Workflow 7: Performance Alerts

Use lumberjackth for performance alert monitoring:

```bash
# Recent alerts
uvx --from lumberjackth lj perf-alerts -n 10

# Filter by repository
uvx --from lumberjackth lj perf-alerts -r autoland -n 10

# Filter by framework (1=talos, 10=raptor, 13=browsertime)
uvx --from lumberjackth lj perf-alerts -f 1 -n 10

# List performance frameworks
uvx --from lumberjackth lj perf-frameworks
```

Use treeherder-cli for per-job performance data:

```bash
# Get performance/resource metrics for a revision
treeherder-cli a13b9fc22101 --perf --json
```

## Workflow 8: Log Caching for Repeated Analysis

```bash
# Fetch and cache logs
treeherder-cli a13b9fc22101 --fetch-logs --cache-dir ./logs

# Re-analyze cached logs with different patterns (no re-download)
treeherder-cli --use-cache --cache-dir ./logs --pattern "ASSERTION" --json
treeherder-cli --use-cache --cache-dir ./logs --pattern "timeout" --json
```

## Workflow 9: JSON Output for Scripting

Both tools support JSON output:

```bash
# treeherder-cli always outputs JSON with --json
treeherder-cli a13b9fc22101 --json
treeherder-cli a13b9fc22101 --group-by test --json | jq '.[] | .test_name'

# lumberjackth uses --json global flag
uvx --from lumberjackth lj --json pushes autoland -n 5
uvx --from lumberjackth lj --json jobs autoland --push-id 12345 --result testfailed | jq '.[].job_type_name'
```

## Job Tiers Reference

| Tier | Description | Sheriff Action |
|------|-------------|----------------|
| 1 | Sheriff-managed, shown by default | Close tree or backout on failure |
| 2 | Shown by default | File bugs, fix within 2 business days |
| 3 | Hidden by default | Job owner responsible |

## Job Results Reference

| Result | Meaning |
|--------|---------|
| `success` | Job passed |
| `testfailed` | Test failures |
| `busted` | Build/infra failure |
| `retry` | Job was retried |
| `usercancel` | Cancelled by user |
| `running` | Currently executing |
| `pending` | Waiting to run |

## External Resources

- [Treeherder](https://treeherder.mozilla.org/)
- [treeherder-cli](https://github.com/padenot/treeherder-cli)
- [Sheriff How-To Guide](https://wiki.mozilla.org/Sheriffing/How_To/Treeherder)
- [Job Visibility Policy](https://wiki.mozilla.org/Sheriffing/Job_Visibility_Policy)
- [Test Disabling Policy](https://wiki.mozilla.org/EngineeringProductivity/Test_Disabling_Policy)
