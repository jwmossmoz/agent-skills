---
name: task-discovery
description: >
  Discover Firefox CI tasks by worker pool. Query the Taskcluster task graph to find
  tasks assigned to specific worker types. Use when planning worker pool migrations,
  crafting mach try pushes, or auditing which tasks run on a pool. Triggers on
  "discover tasks", "find tasks", "worker pool tasks", "task discovery", "which tasks run on".
---

# Task Discovery

Query the Taskcluster task graph to find tasks by worker type. Useful for worker pool
migrations (e.g., `win11-64-24h2` → `win11-64-25h2`) and crafting precise `mach try` pushes.

## Usage

```bash
uv run ~/github_moz/agent-skills/skills/task-discovery/scripts/discover.py [options]
```

## Output Formats

| Format | Description |
|--------|-------------|
| `labels` | One task label per line, sorted (default) |
| `json` | `{"worker_type": "...", "count": N, "by_kind": {...}, "labels": [...]}` |
| `summary` | Grouped by kind with counts per worker type (human-readable) |
| `query` | `-q '<label>'` flags for `mach try fuzzy` |

## Examples

```bash
# List all unique worker types in the task graph
uv run discover.py --list-worker-types

# Find all tasks running on win11-64-24h2 (substring match)
uv run discover.py -w win11-64-24h2 -o summary

# Exact match only — excludes -gpu, -hw, -source variants
uv run discover.py -w win11-64-24h2 --exact -o json

# Filter to browsertime tasks on hardware workers
uv run discover.py -w win11-64-24h2-hw -k browsertime -o labels

# Generate mach try flags for a migration
uv run discover.py -w win11-64-24h2 -k test -o query | head -20

# Regex match for multiple variants
uv run discover.py -w 'win11-64-24h2(-gpu|-source)' --regex -o summary

# Check autoland instead of mozilla-central
uv run discover.py -w win11-64-24h2 --branch autoland -o summary
```

## Migration Workflow

When migrating tasks from one pool to another:

1. **Audit current pool**: `discover.py -w win11-64-24h2 -o summary`
2. **Get task list**: `discover.py -w win11-64-24h2 -k test -o labels > tasks.txt`
3. **Build try command**: Use `query` output piped into `mach try fuzzy`

```bash
mach try fuzzy $(uv run discover.py -w win11-64-24h2-hw -k browsertime -o query)
```

## Options Reference

| Flag | Default | Description |
|------|---------|-------------|
| `-w, --worker-type` | — | Worker type pattern |
| `--exact` | off | Require exact match (no substring) |
| `--regex` | off | Treat pattern as regex |
| `-o, --output` | `labels` | Output format |
| `--branch` | `mozilla-central` | Branch to fetch from |
| `-k, --kind` | all | Filter to specific kind(s), repeatable |
| `--timeout` | `120` | HTTP timeout in seconds |
| `--list-worker-types` | — | List all unique worker types (no `-w` needed) |
