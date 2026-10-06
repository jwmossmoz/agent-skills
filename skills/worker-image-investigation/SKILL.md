---
name: worker-image-investigation
description: >
  Use when triaging a Firefox CI failure to a code, image, intermittent, or
  infra verdict, or when a failure needs image, SBOM, test-history, pool, or
  Azure VM comparison. DO NOT USE FOR starting a build.
metadata:
  version: "1.3"
---

# Worker Image Investigation

## Prerequisites

Install `uv` and `taskcluster`; add `az` for VM access. Follow
[fx-tests.md](references/fx-tests.md) for XPCShell or Mochitest history.

## Usage

```bash
SCRIPTS=~/.claude/skills/worker-image-investigation/scripts
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
uv run "$SCRIPTS/triage.py" <FAILING_TASK_ID> [--json] [--skip-treeherder]
uv run "$SCRIPTS/investigate.py" investigate <FAILING_TASK_ID>
uv run "$SCRIPTS/investigate.py" compare <PASSING_TASK_ID> <FAILING_TASK_ID>
```

`triage.py` gives one verdict: `CODE_REGRESSION`, `IMAGE_REGRESSION`,
`INTERMITTENT`, `INFRA`, or `NEEDS_INVESTIGATION`. Other `investigate.py`
commands: `find-image-regressions`, `batch-compare`, `workers`, `sbom`,
`vm-info`.

## Investigation

1. Treat the `triage.py` verdict as a hypothesis; read the task log.
2. Check history with `fx-tests` or **treeherder**.
3. Compare an equivalent pass and failure (same revision, test, platform,
   configuration). A version difference is not proof.
4. Gate: against the latest autoland baseline, all Tier 1 tasks must pass. A
   unique Tier 1 failure or more Tier 1 intermittents blocks deployment.
5. Read [azure-commands.md](references/azure-commands.md) only when guest
   inspection is needed.

## Gotchas

- An image can make a known intermittent repeatable.
- `--skip-treeherder` drops history and classification evidence.
- Missing `fx-tests` history means unknown, not new.
- Some SBOM files need UTF-16LE decoding.
- Debug VM names are at most 15 characters; take image and size from the pool
  config and delete the VM after use.

## Related Skills

**taskcluster** (tasks), **taskcluster-worker-lifecycle-logs** (unclaimed
tasks), **papertrail** (guest logs), **worker-image-build** (new build),
**bugzilla** (confirmed regression).
