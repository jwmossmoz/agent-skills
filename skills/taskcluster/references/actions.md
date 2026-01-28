# Taskcluster In-Tree Actions Reference

This document explains how Taskcluster in-tree actions work and how to trigger them via the API.

## Overview

In-tree actions are tasks defined in the Firefox taskgraph that can be triggered manually. They're used for operations like:
- **confirm-failures**: Re-run failing tests to determine if they're intermittent
- **backfill**: Run tests on previous pushes to find regression ranges
- **retrigger-multiple**: Retrigger a task multiple times
- **add-new-jobs**: Schedule additional jobs on a push

When you use Treeherder's "Custom Action" menu or "Add new jobs", it's triggering these actions via the Taskcluster hooks API.

## How Actions Work

### 1. Actions are defined in actions.json

Every decision task produces an `actions.json` artifact that lists available actions:

```bash
# Fetch actions.json for a task group (decision task ID)
curl -sL "https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/<DECISION_TASK_ID>/artifacts/public/actions.json" | jq '.actions[].name'
```

### 2. Actions are triggered via hooks

Each action specifies a `hookGroupId` and `hookId`. Triggering the action means calling the Taskcluster hooks API:

```bash
taskcluster api hooks triggerHook <hookGroupId> <hookId> < payload.json
```

### 3. The payload combines action context and user input

The payload includes:
- **decision**: Context from the original push (repository, revision, etc.)
- **user.input**: User-provided parameters for the action
- **user.taskId**: The task to act on
- **user.taskGroupId**: The task group

## Available Actions

### confirm-failures

Re-runs failing tests to determine if they're intermittent or real regressions.

**When to use**: After a test fails, to check if it's a new regression or known intermittent.

**What it does**: Schedules new tasks that run only the failing tests, typically multiple times.

```bash
uv run scripts/tc.py confirm-failures <TASK_ID>
```

### backfill

Runs the same test on previous pushes to identify when a regression was introduced.

**When to use**: After confirming a real failure, to find the exact push that caused it.

**What it does**: Schedules the test to run on N previous pushes.

```bash
uv run scripts/tc.py backfill <TASK_ID>
```

### retrigger-multiple

Retriggers a task multiple times.

**When to use**: To stress-test intermittent failures or gather more data.

```bash
uv run scripts/tc.py retrigger-multiple <TASK_ID> --times 10
```

### retrigger

Creates a new task with the same configuration.

```bash
uv run scripts/tc.py retrigger <TASK_ID>
```

### add-new-jobs

Schedules additional jobs on a push. This is what Treeherder's "Add new jobs" uses.

```bash
uv run scripts/tc.py action <TASK_ID> add-new-jobs --input '{"tasks": ["test-linux64/debug-mochitest-1"]}'
```

## Authentication Requirements

To trigger actions, you need Taskcluster credentials with appropriate scopes:

```
hooks:trigger-hook:project-gecko/in-tree-action-*
```

### Setting up authentication

```bash
# Option 1: Use taskcluster signin (opens browser)
taskcluster signin

# Option 2: Set environment variables
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
export TASKCLUSTER_CLIENT_ID=your-client-id
export TASKCLUSTER_ACCESS_TOKEN=your-access-token
```

## Manual API Usage

If you need to trigger actions directly without the tc.py wrapper:

### 1. Get the task's task group ID

```bash
taskcluster task def <TASK_ID> | jq -r '.taskGroupId'
```

### 2. Fetch actions.json

```bash
curl -sL "https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/<TASK_GROUP_ID>/artifacts/public/actions.json" > actions.json
```

### 3. Find the action and extract hook info

```bash
jq '.actions[] | select(.name == "confirm-failures") | {hookGroupId, hookId, hookPayload}' actions.json
```

### 4. Construct the payload

```json
{
  "decision": {
    "action": { ... from hookPayload.decision.action ... },
    "repository": { ... from hookPayload.decision.repository ... },
    "push": { ... from hookPayload.decision.push ... },
    "parameters": { ... from hookPayload.decision.parameters ... }
  },
  "user": {
    "input": {},
    "taskId": "<TASK_ID>",
    "taskGroupId": "<TASK_GROUP_ID>"
  }
}
```

### 5. Trigger the hook

```bash
taskcluster api hooks triggerHook <hookGroupId> <hookId> < payload.json
```

## Troubleshooting

### "Action not found"

The action might not be available for this type of task. Use `action-list` to see available actions:

```bash
uv run scripts/tc.py action-list <TASK_ID>
```

### "Insufficient scopes"

You need to authenticate with appropriate scopes. Run `taskcluster signin` and ensure you have `hooks:trigger-hook:project-gecko/in-tree-action-*`.

### "Could not fetch actions.json"

The task group might be too old and artifacts have expired, or the decision task failed. Check the task group in the Taskcluster UI.

## References

- [Taskcluster Actions Specification](https://docs.taskcluster.net/docs/manual/using/actions/spec)
- [Firefox Taskgraph Actions](https://firefox-source-docs.mozilla.org/taskcluster/actions.html)
- [Sheriffing/How To/Retrigger Jobs](https://wiki.mozilla.org/Sheriffing/How_To/Retrigger_Jobs)
