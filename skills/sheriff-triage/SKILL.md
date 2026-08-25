---
name: sheriff-triage
description: >
  Use when a sheriff or image maintainer needs one evidence-based verdict for
  a Firefox CI failure from Taskcluster, Treeherder classifications, history,
  and image versions.
metadata:
  version: "1.1"
---

# Sheriff Triage

This skill is a short routing layer over Taskcluster, Treeherder, and worker
image evidence.

## Prerequisites

Install `taskcluster`, `treeherder-client`, and `uv`. Set
`TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com`.

## Usage

```bash
TRIAGE=~/.claude/skills/sheriff-triage/scripts/triage.py

uv run "$TRIAGE" <TASK_ID>
uv run "$TRIAGE" <TASK_ID> --json
uv run "$TRIAGE" <TASK_ID> --skip-treeherder
```

The report classifies the evidence as `CODE_REGRESSION`, `IMAGE_REGRESSION`,
`INTERMITTENT`, `INFRA`, or `NEEDS_INVESTIGATION`.

## Decision rules

- Treat the verdict as a hypothesis. Check the task log before you act.
- For image validation, compare with the latest autoland decision baseline and
  equivalent production-pool history.
- A Tier 1 failure unique to the new image is a release blocker, even if the
  test was intermittent before.
- Use `--skip-treeherder` only for a fast first pass; it removes important
  history and classification evidence.

## Related Skills

- Use **treeherder** for deeper test history and classification details.
- Use **worker-image-investigation** for SBOM, task-group, and VM analysis.
- Use **taskcluster-worker-lifecycle-logs** if no worker claimed the task.
- Use **bugzilla** after the regression is confirmed.

## References

- [scripts/triage.py](scripts/triage.py): implementation and full options
