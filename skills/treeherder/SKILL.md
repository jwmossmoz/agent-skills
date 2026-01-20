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

## Prerequisites

None - uses read-only access to Treeherder API.

## Documentation

For full documentation on Treeherder and the treeherder-client library:

- **Treeherder**: https://treeherder.mozilla.org/
- **treeherder-client Package**: https://pypi.org/project/treeherder-client/
- **Treeherder API Documentation**: https://treeherder.readthedocs.io/
- **Source Code**: https://github.com/mozilla/treeherder
