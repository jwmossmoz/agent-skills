# Sheriff Workflows with Treeherder

This document describes common sheriff workflows and how to accomplish them using the treeherder skill.

## Quick Reference

| Task | Command |
|------|---------|
| Check push health | `push-health --revision <rev>` |
| Find unclassified failures | `unclassified --repo autoland` |
| Get bug suggestions for a job | `bug-suggestions --job-id <id>` |
| View error lines | `errors --job-id <id>` |
| Check job classification | `notes --job-id <id>` |

## Workflow 1: Monitoring Tree Health

### Check recent push health at a glance

```bash
# Quick overview of last 10 pushes
uv run scripts/query.py health-summary --repo autoland --count 10
```

Output shows Tests (T), Builds (B), and Linting (L) status for each push:
```
Push health summary for autoland (last 10):

  069b4737e402 T:✅ B:✅ L:➖  (amarc@mozilla.com)
  bafb3817f343 T:✅ B:✅ L:➖  (ffxbld@lando.moz.tools)
  b41eb98a45de T:❌ B:✅ L:➖  (amarc@mozilla.com)
    Failures: 2 test, 0 build | Need investigation: 1
```

### Get detailed health for a specific push

```bash
uv run scripts/query.py push-health --revision 069b4737e402 --repo autoland
```

Output includes:
- Overall pass/fail status
- Test results with failures needing investigation
- Build status
- Linting status
- Job counts by state

## Workflow 2: Finding Unclassified Failures

Sheriffs need to classify all failures. The `unclassified` command scans recent pushes for failures that haven't been classified yet.

```bash
# Scan last 10 pushes on autoland
uv run scripts/query.py unclassified --repo autoland --push-count 10

# Scan try repo
uv run scripts/query.py unclassified --repo try --push-count 20
```

Example output:
```
Scanning 10 recent pushes for unclassified failures...

Found 3 unclassified failure(s):

  Push 1815584 (12ae7cd09e4d) by ffxbld@lando.moz.tools:
    Treeherder: https://treeherder.mozilla.org/jobs?repo=autoland&revision=...
    ❌ test-linux2404-64-asan/opt-web-platform-tests-wdspec-headless-2 [linux2404-64-asan] (job:545634438)
```

### Filter jobs on a specific push

```bash
# Get only unclassified failures for a push
uv run scripts/query.py jobs --revision abc123 --repo autoland --unclassified

# Combine with result filter
uv run scripts/query.py jobs --revision abc123 --repo autoland --unclassified --result testfailed
```

## Workflow 3: Investigating a Failed Job

When you find a failed job, use these commands to investigate:

### Step 1: Get error lines from the log

```bash
uv run scripts/query.py errors --job-id 545634438 --repo autoland
```

Output shows parsed error lines with line numbers and highlights NEW failures:
```
Error lines for job 545634438:

  [2401]
    11:05:09     INFO - PID 1371 | [Parent 1402, Main Thread] ###!!! ABORT...

  [2417] ← NEW FAILURE
    11:05:09    ERROR - PID 1371 | ==1402==ERROR: AddressSanitizer: SEGV...

⚠️  1 new failure(s) detected in this revision
```

### Step 2: Get bug suggestions

```bash
uv run scripts/query.py bug-suggestions --job-id 545634438 --repo autoland

# Include all matching bugs (not just open/recent)
uv run scripts/query.py bug-suggestions --job-id 545634438 --repo autoland --verbose
```

Output shows matching bugs for each error line:
```
Bug suggestions for job 545634438:

  Line 2447 [NEW IN REV]:
    SUMMARY: AddressSanitizer: SEGV /builds/worker/workspace/obj-build/dist/...
    Open bugs (1):
      Bug 1234567: Intermittent SUMMARY: AddressSanitizer: SEGV...
```

### Step 3: Get log URLs

```bash
uv run scripts/query.py logs --job-id 545634438 --repo autoland
```

Output provides direct links to logs:
```
Log URLs for job:

  live_backing_log (parsed):
    https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/.../logs/live_backing.log

  errorsummary_json (parsed):
    https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/.../wpt_errorsummary.log
```

### Step 4: Check if already classified

```bash
uv run scripts/query.py notes --job-id 545634438 --repo autoland
```

Output shows classification history:
```
Classification notes for job 545634438:

  2026-01-27T13:02:34 by sstanca@mozilla.com
    Classification: expected fail
```

## Workflow 4: Filtering by Platform and Tier

### Filter by platform

```bash
# Only Windows jobs
uv run scripts/query.py jobs --revision abc123 --repo autoland --platform windows

# Only Linux ASAN jobs
uv run scripts/query.py jobs --revision abc123 --repo autoland --platform linux2404-64-asan
```

### Filter by tier

```bash
# Tier 1 jobs only (sheriff-managed, require backout on failure)
uv run scripts/query.py jobs --revision abc123 --repo autoland --tier 1

# Tier 2 jobs (shown by default, bugs filed but no auto-backout)
uv run scripts/query.py jobs --revision abc123 --repo autoland --tier 2
```

### List available platforms

```bash
uv run scripts/query.py platforms
```

## Workflow 5: Performance Alerts

### Check for recent performance regressions

```bash
# Recent alerts from Talos
uv run scripts/query.py perf-alerts --framework 1 --limit 5

# Alerts from Browsertime
uv run scripts/query.py perf-alerts --framework 13 --limit 5

# Untriaged alerts only
uv run scripts/query.py perf-alerts --status untriaged --limit 10
```

### List performance frameworks

```bash
uv run scripts/query.py perf-frameworks
```

Common frameworks:
- 1: talos
- 4: awsy (memory)
- 10: raptor
- 13: browsertime

## Job Tiers Reference

| Tier | Description | Sheriff Action |
|------|-------------|----------------|
| 1 | Sheriff-managed, shown by default | Close tree or backout on failure |
| 2 | Shown by default | File bugs, fix within 2 business days |
| 3 | Hidden by default | Job owner responsible |

## Classification Types Reference

| ID | Name | Use Case |
|----|------|----------|
| 1 | not classified | Default for new failures |
| 2 | fixed by commit | Issue resolved by a subsequent commit |
| 3 | expected fail | Known failure, expected behavior |
| 4 | intermittent | Flaky test with existing bug |
| 5 | infra | Infrastructure issue, not a code bug |
| 6 | new failure not classified | New failure, needs investigation |
| 7 | autoclassified intermittent | Auto-matched to known intermittent |
| 8 | intermittent needs bugid | Intermittent but needs bug filed |

## JSON Output

All commands support `--json` for machine-readable output:

```bash
# Get health data as JSON
uv run scripts/query.py push-health --revision abc123 --repo autoland --json

# Get unclassified failures as JSON
uv run scripts/query.py unclassified --repo autoland --json
```

## External Resources

- [Treeherder](https://treeherder.mozilla.org/)
- [Sheriff How-To Guide](https://wiki.mozilla.org/Sheriffing/How_To/Treeherder)
- [Job Visibility Policy](https://wiki.mozilla.org/Sheriffing/Job_Visibility_Policy)
- [Test Disabling Policy](https://wiki.mozilla.org/EngineeringProductivity/Test_Disabling_Policy)
