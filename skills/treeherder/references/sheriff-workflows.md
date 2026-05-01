# Sheriff Workflows with Treeherder

This document describes common sheriff workflows using **treeherder-cli** plus direct REST API calls for tasks the CLI does not cover.

## Quick Reference

| Task | Approach | Command |
|------|----------|---------|
| Get failures for a revision | treeherder-cli | `treeherder-cli abc123 --json` |
| Compare revisions | treeherder-cli | `treeherder-cli abc123 --compare def456 --json` |
| Check test history | treeherder-cli | `treeherder-cli --history "test_name" --json` |
| Compare a failed job with similar jobs | treeherder-cli | `treeherder-cli --similar-history 543981186 --repo try --json` |
| Fetch logs with search | treeherder-cli | `treeherder-cli abc123 --fetch-logs --pattern "ERROR"` |
| Watch a revision | treeherder-cli | `treeherder-cli abc123 --watch --notify` |
| List recent pushes | REST API | `GET /api/project/{repo}/push/?count=10` |
| Failures by bug ID | REST API | `GET /api/failuresbybug/?bug=2012615` |
| Error lines + bug suggestions | REST API | `GET /api/project/{repo}/jobs/{id}/bug_suggestions/` |
| Performance alert summaries | REST API | `GET /api/performance/alertsummary/` |

## Workflow 1: Investigating Failures on a Push

### Step 1: Find the revision

Query the push endpoint for recent pushes on a repo:

```bash
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/project/autoland/push/?count=10" \
  | jq '.results[] | {id, revision, author}'

# Filter by author
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/project/autoland/push/?count=20&author=user@mozilla.com" \
  | jq '.results[] | {revision, push_timestamp}'
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

# Or pull bug suggestions for a specific failed job ID via the REST API
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/project/autoland/jobs/545896732/bug_suggestions/" \
  | jq '.[] | {test: .path_end, bugs: [.bugs.open_recent[]?.id]}'
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

```bash
# Watch for updates, get notified on completion
treeherder-cli abc123 --repo try --watch --notify

# Shorter polling interval (seconds)
treeherder-cli abc123 --repo try --watch --watch-interval 60
```

## Workflow 4: Investigating Intermittent Failures by Bug

The `failuresbybug` endpoint returns occurrences of a bug across recent pushes:

```bash
# All failures for a bug in the last 7 days (default range)
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/failuresbybug/?bug=2012615" \
  | jq '.[] | {tree, platform, build_type, test_suite, push_time}'

# Filter by repository
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/failuresbybug/?bug=2012615&tree=autoland" \
  | jq '.'

# Specific date range
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/failuresbybug/?bug=2012615&startday=2026-01-26&endday=2026-01-28" \
  | jq '.'
```

Filter by platform or build type with `jq` after the request:

```bash
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/failuresbybug/?bug=2012615&tree=autoland" \
  | jq '[.[] | select(.platform | test("windows.*24h2"))]'
```

## Workflow 5: Filtering Jobs by Result, State, and Tier

`treeherder-cli` filters by platform and job-name regex; for filtering by `result`, `state`, or `tier`, query the jobs endpoint directly:

```bash
# Failed jobs only on a push
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/project/autoland/jobs/?push_id=12345&result=testfailed&count=2000" \
  | jq '.results[] | {id, job_type_name, result, tier}'

# Build failures (busted) only
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/project/autoland/jobs/?push_id=12345&result=busted&count=2000" \
  | jq '.results[] | {id, job_type_name, ref_data_name}'

# Tier 1 failures only
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/project/autoland/jobs/?push_id=12345&result=testfailed&tier=1&count=2000" \
  | jq '.results[] | .job_type_name'
```

`treeherder-cli` is still the right tool when you start from a revision instead of a push ID:

```bash
treeherder-cli abc123 --platform "linux.*64" --filter "mochitest" --json
```

## Workflow 6: Downloading Artifacts

```bash
# Download all artifacts for a revision
treeherder-cli a13b9fc22101 --download-artifacts

# Filter to specific artifact types
treeherder-cli a13b9fc22101 --download-artifacts --artifact-pattern "screenshot|errorsummary"
```

## Workflow 7: Performance Alerts

Use the REST API for performance alert summaries:

```bash
# Recent alerts
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/performance/alertsummary/?limit=10" \
  | jq '.results[] | {repository, push_timestamp, alerts: [.alerts[].id]}'

# Filter by repository
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/performance/alertsummary/?repository=autoland&limit=10" \
  | jq '.'

# List frameworks (talos=1, raptor=10, browsertime=13, awsy=4)
curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/performance/framework/" \
  | jq '.[] | {id, name}'
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

`treeherder-cli` outputs JSON with `--json`; the REST API is JSON natively.

```bash
# Filter and pipe to jq
treeherder-cli a13b9fc22101 --json | jq '.[] | select(.result == "testfailed") | .job_type_name'
treeherder-cli a13b9fc22101 --group-by test --json | jq '.[] | .test_name'

curl -s -A "Mozilla/5.0" \
  "https://treeherder.mozilla.org/api/project/autoland/jobs/?push_id=12345&result=testfailed&count=2000" \
  | jq '.results[].job_type_name'
```

## Workflow 10: Compare a Failed Try Job with Similar Jobs

Use this when a try failure needs cross-branch context.

### Step 1: Get similar job history on the same repo

```bash
treeherder-cli --similar-history 549239688 --repo try --similar-count 100 --json
```

### Step 2: Compare exact job type on other branches

```bash
job_type="test-windows11-64-24h2/debug-mochitest-browser-chrome-msix-13"
enc=$(jq -nr --arg v "$job_type" '$v|@uri')

for repo in autoland mozilla-central mozilla-beta; do
  curl -s "https://treeherder.mozilla.org/api/project/${repo}/jobs/?job_type_name=${enc}&result=success&count=2000" \
    | jq -r --arg repo "$repo" '
        if (.results|length)==0 then
          "\($repo)\tNO_MATCH"
        else
          (.results|last) as $last
          | "\($repo)\t\($last.last_modified)\t\($last.ref_data_name)\t\($last.id)"
        end'
done
```

For full API details and a complete example, see `references/similar-jobs-comparison.md`.

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
