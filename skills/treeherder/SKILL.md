---
name: treeherder
description: >
  Query Firefox Treeherder for CI job results using Mozilla's official treeherder-client library.
  Use after commits land to check test/build results. Supports cross-branch failure search for
  sheriff triage workflows. Triggers on "treeherder", "job results", "check tests", "ci status",
  "find similar failures", "cross-branch search".
---

# Treeherder

Query Mozilla Treeherder for CI job results using the official `treeherder-client` library.

## Usage

Run from the skill directory:

```bash
# Query by revision
uv run scripts/query.py \
  --revision <COMMIT_HASH> \
  --repo try

# Filter for specific tests
uv run scripts/query.py \
  --revision <COMMIT_HASH> \
  --filter mochitest-chrome

# Query by push ID
uv run scripts/query.py \
  --push-id <PUSH_ID>
```

## Cross-Branch Failure Search (Sheriff Workflow)

Search for similar job failures across autoland and mozilla-central to determine if a failure is a code regression or image regression:

```bash
# Find failures matching a job name across branches
uv run scripts/query.py \
  --find-similar "mochitest-browser-chrome" \
  --repos autoland,mozilla-central \
  --limit 100

# Search for specific test failures
uv run scripts/query.py \
  --find-similar "test_keycodes" \
  --limit 200

# JSON output for scripting
uv run scripts/query.py \
  --find-similar "mochitest-browser-media" \
  --json
```

### Sheriff Triage Logic

This is the core signal for distinguishing failure types:

| Scenario | Likely Cause |
|----------|--------------|
| Same test fails on autoland/mozilla-central | **Code regression** |
| Test only fails on alpha/staging pools | **Image regression** |
| Failures classified as intermittent (id=4) | **Known intermittent** |
| No similar failures found | **New issue** - investigate further |

### Failure Classification IDs

| ID | Classification |
|----|----------------|
| 1 | Not classified |
| 2 | Fixed by commit |
| 3 | Expected fail |
| 4 | Intermittent |
| 5 | Infra |
| 6 | Intermittent needs filing |
| 7 | Autoclassified intermittent |

## Prerequisites

None - uses read-only access to Treeherder API.

## Documentation

For full documentation on Treeherder and the treeherder-client library:

- **Treeherder**: https://treeherder.mozilla.org/
- **treeherder-client Package**: https://pypi.org/project/treeherder-client/
- **Treeherder API Documentation**: https://treeherder.readthedocs.io/
- **Source Code**: https://github.com/mozilla/treeherder
- **Sheriffing Wiki**: https://wiki.mozilla.org/Sheriffing
