---
name: worker-image-investigation
description: >
  Use when a Firefox CI failure can be worker-image related and needs image,
  SBOM, test-history, pool, or Azure VM comparison. DO NOT USE FOR starting a
  build.
metadata:
  version: "1.2"
---

# Worker Image Investigation

## Prerequisites

Install `uv` and `taskcluster`; add `az` for VM access. Follow
[fx-tests.md](references/fx-tests.md) for XPCShell or Mochitest history.

## Usage

```bash
WII=~/.claude/skills/worker-image-investigation/scripts/investigate.py
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
uv run "$WII" investigate <FAILING_TASK_ID>
uv run "$WII" compare <PASSING_TASK_ID> <FAILING_TASK_ID>
uv run "$WII" find-image-regressions <TASK_GROUP_ID>
```

Other commands are `batch-compare`, `workers`, `sbom`, `vm-info`, and
`sheriff-report`.

## Investigation

1. Inspect the task, pool, image version, and SBOM.
2. Check history with `fx-tests` or **treeherder**.
3. Compare an equivalent pass and failure. Match revision, test, platform, and
   configuration. A version difference is not proof.
4. Check the full try group. If no worker claimed the task, use
   **taskcluster-worker-lifecycle-logs**.
5. Use [azure-commands.md](references/azure-commands.md) only when earlier
   evidence requires guest inspection.

## Validation gate

Use the latest autoland decision baseline. All Tier 1 tasks must pass. A unique
Tier 1 failure or a clear increase in Tier 1 intermittents blocks deployment.

## Gotchas

- An image can make a known intermittent repeatable.
- Missing `fx-tests` history means unknown, not new.
- Some SBOM files need UTF-16LE decoding.
- Debug VM names must be at most 15 characters. Get image and size from the
  pool configuration, and delete the VM after use.

## Related Skills

Use **taskcluster** for tasks, **papertrail** for guest logs, and **worker-image-build** for a new build.
