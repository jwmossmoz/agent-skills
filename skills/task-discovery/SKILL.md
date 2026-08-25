---
name: task-discovery
description: >
  Use when finding Taskcluster task labels assigned to worker types for pool
  audits, migrations, or targeted try queries. DO NOT USE FOR live task status,
  logs, artifacts, or actions.
metadata:
  version: "1.1"
---

# Task Discovery

Query a decision task graph and group matching labels by worker type or task
kind.

## Prerequisites

Install `uv`. Read-only Taskcluster access does not need authentication.

## Usage

```bash
DISCOVER=~/.claude/skills/task-discovery/scripts/discover.py

# Audit the current autoland task graph.
uv run "$DISCOVER" -w win11-64-24h2 --branch autoland -o summary

# Generate exact task labels for mach try fuzzy.
uv run "$DISCOVER" -w win11-64-24h2 --exact -k test -o query

# List all worker types in the graph.
uv run "$DISCOVER" --list-worker-types --branch autoland
```

Run `uv run "$DISCOVER" --help` for regex matching, output formats, and
timeouts.

## Gotchas

- The default branch is `mozilla-central`. Use `--branch autoland` for current
  migration planning.
- Worker matching is a substring search by default. Use `--exact` when suffix
  variants such as `-gpu`, `-hw`, or `-source` must not match.
- Task graphs can exceed 30 MB. Increase `--timeout` on slow links.

## Related Skills

- Use **taskcluster** for status, logs, artifacts, actions, and worker state.
- Use **os-integrations** to submit alpha-pool validation tasks.
