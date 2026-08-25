---
name: taskcluster
description: >
  Use when inspecting or operating Mozilla Taskcluster tasks, task groups,
  artifacts, in-tree actions, or worker pools. DO NOT USE FOR task-graph
  discovery or worker-manager and worker-scanner lifecycle logs.
metadata:
  version: "1.1"
---

# Taskcluster

Use the native CLI for direct operations and `tc.py` for structured artifacts
or Firefox in-tree actions.

## Prerequisites

```bash
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
TC=~/.claude/skills/taskcluster/scripts/tc.py
```

Install `taskcluster` and `uv`. Read operations need no authentication. Sign in
before a write operation.

## Usage

```bash
taskcluster task status <TASK_ID>
taskcluster task log <TASK_ID>
taskcluster group list --failed <GROUP_ID>
uv run "$TC" artifacts <TASK_ID>
uv run "$TC" retrigger <TASK_ID>
uv run "$TC" confirm-failures <TASK_ID>
uv run "$TC" backfill <TASK_ID>
```

Use each CLI's `--help` for the full command set. Read
[actions.md](references/actions.md) for other in-tree actions and
[worker-pools.md](references/worker-pools.md) before bulk worker operations.

## Gotchas

- Set the Firefox CI root URL; the default is Community Taskcluster.
- Do not use `taskcluster task retrigger` for Firefox CI. It clears upstream
  dependencies. Use `tc.py retrigger`.
- `task rerun` reuses an ID; `tc.py retrigger` creates a new task.

## Related Skills

Use **task-discovery** for graph labels, **treeherder** for test history, and
**taskcluster-worker-lifecycle-logs** for service logs.

## References

[examples.md](references/examples.md) has workflows and
[integration.md](references/integration.md) has tool handoffs.
