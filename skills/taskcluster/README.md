# Taskcluster Skill

A skill for interacting with Mozilla Taskcluster CI using the official `taskcluster` CLI.

## Quick Start

Run from the skill directory:

```bash
# Query task status (accepts task ID or full URL)
uv run scripts/tc.py status dtMnwBMHSc6kq5VGqJz0fw
uv run scripts/tc.py status \
  https://firefox-ci-tc.services.mozilla.com/tasks/dtMnwBMHSc6kq5VGqJz0fw

# View task logs
uv run scripts/tc.py log dtMnwBMHSc6kq5VGqJz0fw

# List task artifacts
uv run scripts/tc.py artifacts dtMnwBMHSc6kq5VGqJz0fw

# Get full task definition
uv run scripts/tc.py definition dtMnwBMHSc6kq5VGqJz0fw

# List all tasks in a group
uv run scripts/tc.py group-list <GROUP_ID>
```

## Installation

The skill requires the `taskcluster` CLI to be installed:

```bash
brew install taskcluster
```

## Features

- **No Python dependencies**: Pure wrapper around taskcluster CLI
- **URL parsing**: Automatically extracts task IDs from Taskcluster URLs
- **JSON output**: Pretty-printed JSON for easy piping to `jq`
- **Task operations**: status, logs, artifacts, definition, retrigger, rerun, cancel
- **Group operations**: list, status, cancel entire task groups

## Authentication

Most read-only operations work without authentication. For write operations (retrigger, cancel), you'll need credentials.

Set up authentication with:
```bash
taskcluster signin
```

Or use environment variables:
```bash
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
export TASKCLUSTER_CLIENT_ID=your-client-id
export TASKCLUSTER_ACCESS_TOKEN=your-access-token
```

## Documentation

- See [SKILL.md](SKILL.md) for complete usage documentation
- See [references/examples.md](references/examples.md) for real-world usage patterns
- See [references/integration.md](references/integration.md) for Mozilla CI integration details

## Related Skills

- **treeherder**: Query CI job results by revision to get task IDs
- **lando**: Check landing job status
- **os-integrations**: Run Firefox mach try commands with worker pool overrides

## Common Workflows

### Debug a Failed Task

```bash
# 1. Check status
uv run scripts/tc.py status <TASK_ID>

# 2. View logs
uv run scripts/tc.py log <TASK_ID>

# 3. Get full definition (check worker pool, payload)
uv run scripts/tc.py definition <TASK_ID> | jq '.workerType, .payload'
```

### Monitor a Task Group

```bash
# Get group status summary
uv run scripts/tc.py group-status <GROUP_ID>

# List all tasks in group
uv run scripts/tc.py group-list <GROUP_ID>

# Find failed tasks
uv run scripts/tc.py group-list <GROUP_ID> | \
  jq '.tasks[] | select(.status.state == "failed")'
```

### From Treeherder to Task Details

Replace `<agent-skills-root>` with the path to this repo.

```bash
# 1. Use treeherder skill to get task IDs from a revision
uv run <agent-skills-root>/skills/treeherder/scripts/query.py --revision <REV> --repo try

# 2. Investigate specific tasks
uv run scripts/tc.py status <TASK_ID>
uv run scripts/tc.py log <TASK_ID>
```
