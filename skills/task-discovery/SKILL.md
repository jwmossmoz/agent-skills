---
name: task-discovery
description: >
  Query the Taskcluster task graph to list tasks assigned to specific
  worker types — for worker-pool migrations, audits of which tasks run
  on a pool, or building targeted `mach try fuzzy` queries. DO NOT USE
  FOR live task status, retriggers, or task logs (use taskcluster).
---

# Task Discovery

Query the Taskcluster task graph to find tasks by worker type. Useful for worker pool
migrations (e.g., `win11-64-24h2` → `win11-64-25h2`) and crafting precise `mach try` pushes.

## Usage

```bash
uv run ~/.claude/skills/task-discovery/scripts/discover.py [options]
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

## Gotchas

- Default branch is `mozilla-central`. For migration planning, pass `--branch autoland` — autoland is the integration branch upstream of central and reflects newer task graphs first.
- `-w` is substring match by default. `win11-64-24h2` will pull in `-gpu`, `-hw`, and `-source` variants. Use `--exact` or `--regex` when you don't want them.
- The decision task graph can be 30+ MB; the 120s timeout default is fine on home internet but can stall on bad links — bump with `--timeout`.
- `query` output is designed for `mach try fuzzy $(...)` — paste it through xargs/$() rather than copying labels by hand.
