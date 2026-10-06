---
name: worker-image-investigation
description: >
  Use when triaging a Firefox CI failure to a code, image, intermittent, or
  infra verdict, or when a failure needs image, SBOM, test-history, pool, or
  Azure VM comparison. DO NOT USE FOR starting a build.
metadata:
  version: "1.4"
---

# Worker Image Investigation

## Prerequisites

Install `uv` and `taskcluster`; add `az` for VM access. Follow
[fx-tests.md](references/fx-tests.md) for XPCShell or Mochitest history.

## Usage

```bash
SCRIPTS=~/.claude/skills/worker-image-investigation/scripts
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
uv run "$SCRIPTS/triage.py" <FAILING_TASK_ID>
uv run "$SCRIPTS/investigate.py" compare <PASSING_TASK_ID> <FAILING_TASK_ID>
```

Run `investigate.py --help` for image, SBOM, pool, and VM commands.

## Investigation

1. Treat the `triage.py` verdict as a hypothesis; read the task log.
2. Check history with `fx-tests` or **treeherder**.
3. Compare an equivalent pass and failure (same revision, test, platform,
   configuration). A version difference is not proof.
4. Check today's equivalent baseline tasks. Shared failures, including Tier 1,
   do not block; failures against passing equivalents do. Read
   [validation-gate.md](references/validation-gate.md) before deciding.
5. Read [azure-commands.md](references/azure-commands.md) only when guest
   inspection is needed.

## Gotchas

- Passing retries can hide earlier harness failures; inspect full task logs.
- `--skip-treeherder` drops history and classification evidence.
- Missing `fx-tests` history means unknown, not new.
- Some SBOM files need UTF-16LE decoding.
- Debug VM names are at most 15 characters; take image and size from the pool
  config and delete the VM after use.

## Related Skills

**taskcluster** (tasks), **taskcluster-worker-lifecycle-logs** (unclaimed
tasks), **papertrail** (guest logs), **worker-image-build** (new build),
**bugzilla** (confirmed regression).
