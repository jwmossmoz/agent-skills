---
name: taskcluster
description: >
  Interact with Mozilla Taskcluster CI using the taskcluster CLI.
  Query task status, view logs, download artifacts, retrigger tasks, and manage task groups.
  Use when working with CI tasks from firefox-ci-tc.services.mozilla.com or debugging worker pool issues.
  Triggers on "taskcluster", "task status", "task log", "artifacts", "retrigger", "task group".
---

# Taskcluster

Interact with Mozilla Taskcluster CI using the official `taskcluster` CLI.

## Usage

Run from the skill directory:

```bash
# Query task status
uv run scripts/tc.py status <TASK_ID>

# Get task logs
uv run scripts/tc.py log <TASK_ID>

# List task artifacts
uv run scripts/tc.py artifacts <TASK_ID>

# Get full task definition
uv run scripts/tc.py definition <TASK_ID>

# Retrigger a task (new task ID, updated timestamps)
uv run scripts/tc.py retrigger <TASK_ID>

# Rerun a task (same task ID)
uv run scripts/tc.py rerun <TASK_ID>

# Cancel a task
uv run scripts/tc.py cancel <TASK_ID>

# List tasks in a group
uv run scripts/tc.py group-list <TASK_GROUP_ID>

# Get task group status
uv run scripts/tc.py group-status <TASK_GROUP_ID>

# Extract task ID from Taskcluster URL
uv run scripts/tc.py status https://firefox-ci-tc.services.mozilla.com/tasks/fuCPrKG2T62-4YH1tWYa7Q
```

## Prerequisites

### 1. Taskcluster CLI

The skill uses the `taskcluster` CLI which should be installed via Homebrew:

```bash
brew install taskcluster
```

Check installation:
```bash
taskcluster version
```

### 2. Authentication (Optional)

Most read-only operations (status, logs, artifacts) work without authentication. For write operations (retrigger, cancel), you need Taskcluster credentials.

#### Option 1: Environment Variables

```bash
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
export TASKCLUSTER_CLIENT_ID=your-client-id
export TASKCLUSTER_ACCESS_TOKEN=your-access-token
```

#### Option 2: Configuration File

Create `~/.config/taskcluster/credentials.json` or use the CLI:

```bash
taskcluster signin
```

#### Option 3: 1Password CLI

Store credentials in 1Password and configure in `config.toml`:

```bash
cd scripts
cp config.toml.example config.toml
```

Edit the `config.toml` to specify your 1Password item and vault.

## Common Workflows

### Debugging Task Failures

1. **Check task status**: `tc.py status <TASK_ID>`
2. **View logs**: `tc.py log <TASK_ID>`
3. **Inspect full definition**: `tc.py definition <TASK_ID>`
4. **Check all tasks in group**: `tc.py group-list <GROUP_ID>`

### Working with Treeherder Tasks

When you have a Treeherder URL like:
```
https://treeherder.mozilla.org/jobs?repo=try&revision=ed901414ea5ec1e188547898b31d133731e77588
```

1. Use the treeherder skill to get task IDs
2. Use this skill to query individual tasks

### Retriggering Failed Tasks

```bash
# Retrigger creates a new task with updated timestamps
uv run scripts/tc.py retrigger <TASK_ID>

# Rerun attempts to rerun the same task
uv run scripts/tc.py rerun <TASK_ID>
```

## URL Support

The skill automatically extracts task IDs from Taskcluster URLs:

```bash
# Both of these work identically:
uv run scripts/tc.py status fuCPrKG2T62-4YH1tWYa7Q
uv run scripts/tc.py status https://firefox-ci-tc.services.mozilla.com/tasks/fuCPrKG2T62-4YH1tWYa7Q
```

Supported URL formats:
- `https://firefox-ci-tc.services.mozilla.com/tasks/<TASK_ID>`
- `https://stage.taskcluster.nonprod.cloudops.mozgcp.net/tasks/<TASK_ID>`
- `https://community-tc.services.mozilla.com/tasks/<TASK_ID>`

## Output Formats

All commands return JSON output that can be piped to `jq` for processing:

```bash
# Get only failed tasks from a group
uv run scripts/tc.py group-list <GROUP_ID> | jq '.tasks[] | select(.status.state == "failed")'

# List artifact names
uv run scripts/tc.py artifacts <TASK_ID> | jq '.artifacts[].name'
```

## Related Skills

- **treeherder**: Query CI job results by revision to get task IDs
- **lando**: Check landing job status
- **os-integrations**: Run Firefox mach try commands

## Documentation

- **Taskcluster Docs**: https://docs.taskcluster.net/
- **Taskcluster CLI**: https://github.com/taskcluster/taskcluster/tree/main/clients/client-shell
- **Firefox CI**: https://firefox-ci-tc.services.mozilla.com/
- **Community Taskcluster**: https://community-tc.services.mozilla.com/
