---
name: papertrail
description: >
  Use when querying in-VM Taskcluster worker and operating-system logs through
  paperctl. DO NOT USE FOR workers that never started or Azure control-plane
  lifecycle events.
metadata:
  version: "1.2"
---

# Papertrail

Search or download logs forwarded from a running worker.

## Scope

| Tool | Use it for |
|---|---|
| **papertrail** | Worker process, Windows events, service output, and container startup |
| **taskcluster-worker-lifecycle-logs** | Worker-manager decisions, registration, scanner state, and workers that never started |
| **taskcluster** | Task logs, artifacts, state, and retriggers |

## Prerequisites

Set `SWO_API_TOKEN` or run `paperctl config init` to create
`~/.config/paperctl/config.toml`.

## Usage

```bash
# Pull one worker around an incident.
paperctl pull vm-abc123 --since -2h --output worker.log

# Search across workers or one worker.
paperctl search 'error AND timeout' --since -24h --limit 100
paperctl search 'WORKER_METRICS' --system vm-abc123 --since -2h --output json

```

Run `paperctl --help` and the command `--help` for time, output, and entity
options.

## Gotchas

- v2.0 uses `SWO_API_TOKEN`, not `PAPERTRAIL_API_TOKEN`.
- Search supports text, quoted phrases, and `AND`, `OR`, and `NOT`. It does not
  support regular expressions or wildcards.
- Prefer the embedded worker timestamp when ingestion time and process time
  differ.
- A proxy startup line does not prove that the main task container started.
  Compare retries and nearby workers when startup evidence is incomplete.
- If the worker never started or claimed work, switch to
  **taskcluster-worker-lifecycle-logs**.

## Related Skills

Use **worker-ready-tracing** for a combined startup timeline.
