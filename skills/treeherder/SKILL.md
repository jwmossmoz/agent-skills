---
name: treeherder
description: >
  Query Firefox Treeherder for CI job results using Mozilla's official treeherder-client library.
  Use after commits land to check test/build results.
  Triggers on "treeherder", "job results", "check tests", "ci status".
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

## Job Classification API

Query how sheriffs have classified job failures:

```bash
# Get classification by Taskcluster task ID
uv run scripts/classification.py get --task-id fuCPrKG2T62-4YH1tWYa7Q

# Get classification by Treeherder job ID
uv run scripts/classification.py get --job-id 12345 --repo autoland

# Include sheriff notes/comments
uv run scripts/classification.py get --task-id fuCPrKG2T62-4YH1tWYa7Q --include-notes

# Classification summary for all failures in a push
uv run scripts/classification.py summary --revision abc123 --repo autoland

# JSON output
uv run scripts/classification.py get --task-id abc123 --json
```

### Classification IDs

| ID | Classification | Meaning |
|----|----------------|---------|
| 1 | not classified | No sheriff has reviewed this yet |
| 2 | fixed by commit | A subsequent commit fixed the issue |
| 3 | expected fail | Known expected failure |
| 4 | intermittent | Known flaky test |
| 5 | infra | Infrastructure issue (not code) |
| 6 | intermittent needs filing | Flaky test that needs a bug filed |
| 7 | autoclassified intermittent | Automatically detected as intermittent |

### Sheriff Workflow Integration

When investigating failures, check classification first:
- **intermittent (4)**: Known flaky, likely not your image change
- **infra (5)**: Infrastructure issue, possibly image-related
- **not classified (1)**: Needs investigation

## Prerequisites

None - uses read-only access to Treeherder API.

## Documentation

For full documentation on Treeherder and the treeherder-client library:

- **Treeherder**: https://treeherder.mozilla.org/
- **treeherder-client Package**: https://pypi.org/project/treeherder-client/
- **Treeherder API Documentation**: https://treeherder.readthedocs.io/
- **Source Code**: https://github.com/mozilla/treeherder
