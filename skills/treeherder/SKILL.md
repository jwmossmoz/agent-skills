---
name: treeherder
description: >
  Query Mozilla Treeherder for CI job results, failure analysis, test
  history, similar-job comparison, cross-branch sheriff triage, and bug
  suggestions via treeherder-cli plus the Treeherder REST API for endpoints
  the CLI doesn't cover. Use after pushes land or to investigate
  intermittents and pass/fail cliffs across branches.
metadata:
  version: "1.0"
---

# Treeherder

Query Mozilla Treeherder for CI job results, failure analysis, and performance data.

## Tool

This skill uses **treeherder-cli**, a Rust CLI for revision-based failure analysis, comparison, history, log searching, artifact downloads, and watch mode.

```bash
cargo install --git https://github.com/padenot/treeherder-cli
```

For tasks treeherder-cli does not cover (push listing, failures-by-bug, error-line bug suggestions, performance alerts, repository listing), call the Treeherder REST API directly. See `references/api-reference.md`.

## Quick Start

```bash
# Get failed jobs for a revision
treeherder-cli a13b9fc22101 --json

# Filter by job name or platform
treeherder-cli a13b9fc22101 --filter "mochitest" --json
treeherder-cli a13b9fc22101 --platform "linux.*64" --json

# Group failures by test (cross-platform view)
treeherder-cli a13b9fc22101 --group-by test --json

# Compare revisions to find regressions
treeherder-cli a13b9fc22101 --compare b2c3d4e5f678 --json

# Check test history for intermittent detection
treeherder-cli --history "test_audio_playback" --history-count 10 --repo try --json

# Show similar job history for a failed job ID
treeherder-cli --similar-history 543981186 --similar-count 100 --repo try --json

# Fetch logs with pattern matching
treeherder-cli a13b9fc22101 --fetch-logs --pattern "ASSERTION|CRASH" --json

# Download artifacts
treeherder-cli a13b9fc22101 --download-artifacts --artifact-pattern "screenshot|errorsummary"

# Watch mode with notification
treeherder-cli a13b9fc22101 --watch --notify

# Switch repository (default: autoland)
treeherder-cli a13b9fc22101 --repo try --json
```

## When to Use Which Approach

| Task | Approach | Example |
|------|----------|---------|
| Analyze failures for a revision | treeherder-cli | `treeherder-cli abc123 --json` |
| Compare two revisions | treeherder-cli | `treeherder-cli abc123 --compare def456 --json` |
| Check test history | treeherder-cli | `treeherder-cli --history "test_name" --json` |
| Compare a failed job to similar jobs | treeherder-cli | `treeherder-cli --similar-history 543981186 --repo try --json` |
| Fetch/search logs | treeherder-cli | `treeherder-cli abc123 --fetch-logs --pattern "ERROR"` |
| Download artifacts | treeherder-cli | `treeherder-cli abc123 --download-artifacts` |
| Watch a revision | treeherder-cli | `treeherder-cli abc123 --watch --notify` |
| Performance/resource data | treeherder-cli | `treeherder-cli abc123 --perf --json` |
| List recent pushes | REST API | `GET /api/project/{repo}/push/?count=10` |
| Failures by bug ID | REST API | `GET /api/failuresbybug/?bug=2012615` |
| Error lines + bug suggestions | REST API | `GET /api/project/{repo}/jobs/{id}/bug_suggestions/` |
| Performance alert summaries | REST API | `GET /api/performance/alertsummary/` |
| List repositories | REST API | `GET /api/repository/` |

## Cross-Branch Failure Search

Use cross-branch checks to decide whether a failure is likely a code regression, image regression, or known intermittent:

1. Resolve the failing task to a Treeherder job ID if needed.
2. Run `treeherder-cli --similar-history <JOB_ID> --repo autoland --json`.
3. Repeat for `mozilla-central` or other relevant repositories.
4. Compare whether the same test is failing on production branches, alpha/staging pools only, or historically intermittent.

| Scenario | Likely cause |
|----------|--------------|
| Same test fails on autoland/mozilla-central | Code regression |
| Test only fails on alpha/staging pools | Image regression |
| Failures are classified intermittent | Known intermittent |
| No similar failures found | New issue; investigate further |

## Bug Suggestions for Failing Jobs

`treeherder-cli` does not bulk-query known intermittent bugs for failing jobs. Use the Treeherder REST API directly to check whether test failures have associated Bugzilla bugs.

### Workflow

1. Get failing job IDs from `treeherder-cli` JSON output
2. Query the bug suggestions endpoint for each job
3. Aggregate results to identify known intermittents vs novel failures

### API Endpoint

```
GET https://treeherder.mozilla.org/api/project/{repo}/jobs/{job_id}/bug_suggestions/
```

Returns an array of failure lines with matched Bugzilla bugs:
```json
[
  {
    "search": "TEST-UNEXPECTED-FAIL | test.js | Test timed out",
    "path_end": "path/to/test.js",
    "bugs": {
      "open_recent": [
        {"id": 1940606, "status": "REOPENED", "summary": "Intermittent test.js | ...", "keywords": ["intermittent-failure"]}
      ],
      "all_others": []
    },
    "failure_new_in_rev": false
  }
]
```

### Example Script

```python
import json
import urllib.request

headers = {"User-Agent": "Mozilla/5.0"}
repo = "try"
job_id = 553921053

url = f"https://treeherder.mozilla.org/api/project/{repo}/jobs/{job_id}/bug_suggestions/"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    suggestions = json.loads(resp.read())

for suggestion in suggestions:
    test = suggestion.get("path_end", "")
    bugs = suggestion["bugs"].get("open_recent", []) + suggestion["bugs"].get("all_others", [])
    print(f"{test}: {'known bugs' if bugs else 'NO known bugs'}")
```

### Bulk Query Pattern

When checking many failing jobs (for example, validating a new worker image), combine with `treeherder-cli --json` output:

```bash
treeherder-cli REVISION --repo try --platform "25h2" --json > failures.json
python3 bulk_bug_check.py failures.json
```

Deduplicate by `job_type_name` to avoid querying the same test suite multiple times across retries. A `User-Agent` header is required for all API requests.

## Prerequisites

- **treeherder-cli**: `cargo install --git https://github.com/padenot/treeherder-cli`

No authentication required.

## References

- `references/cli-reference.md` - Complete treeherder-cli reference
- `references/sheriff-workflows.md` - Sheriff workflow examples
- `references/api-reference.md` - REST API documentation
- `references/similar-jobs-comparison.md` - Compare failed jobs using Treeherder's `similar_jobs` API

## Gotchas

- The Treeherder REST API requires a `User-Agent` header. Bare `urllib`/`curl` calls without one get rate-limited or 403'd.
- `treeherder-cli` accepts revision SHAs, but `--similar-history` takes a Treeherder *job* ID (numeric), not a Taskcluster task ID. Resolve task to job ID via `/api/project/{repo}/jobs/?task_id=...`.
- Default repo is `autoland`. Pass `--repo try` (or `mozilla-central`, `mozilla-beta`) when looking elsewhere.
- For batch bug-suggestion checks across many failing jobs, dedupe by `job_type_name` to avoid hammering the API on retries.
- Treeherder's `failure_new_in_rev` field tells you whether a failure first appeared in this revision, which is useful for distinguishing regressions from intermittents that landed earlier.

## External Documentation

- **Treeherder**: https://treeherder.mozilla.org/
- **treeherder-cli**: https://github.com/padenot/treeherder-cli
