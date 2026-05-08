---
name: papertrail
description: >
  Query and download in-VM Taskcluster worker logs from SolarWinds
  Observability (formerly Papertrail) using paperctl v2.0. Use when
  investigating what a worker process or its OS reported on-host. DO NOT
  USE FOR provisioning failures where no worker started (use tc-logview)
  or Azure-side VM lifecycle events (use splunk).
---

# SolarWinds Observability Logs (paperctl)

Query and download logs from SolarWinds Observability (formerly Papertrail) using `paperctl` v2.0.

> **Scope vs. [`tc-logview`](https://github.com/taskcluster/tc-logview)**: Papertrail holds
> in-VM logs forwarded from the worker host (what the worker process and OS reported).
> `tc-logview` holds Taskcluster's worker-manager and worker-scanner service events in GCP
> Cloud Logging (provisioning decisions, lifecycle, scan health, Azure-side errors as the
> service observed them). When a worker never started, never claimed, or vanished mid-task,
> reach for `tc-logview` first; reach for `paperctl` when the worker came up and you need the
> on-host story. See the `/taskcluster` skill's `references/tc-logview.md` for the full guide.

## Prerequisites

Requires `SWO_API_TOKEN` environment variable or `~/.config/paperctl/config.toml`.

Initialize config interactively:

```bash
paperctl config init
```

## Commands

### Pull logs from a system

Download all logs for a system to `~/.cache/paperctl/logs/<system>.txt`:

```bash
paperctl pull <system-name>
```

Partial name matching is supported. Use Taskcluster worker IDs directly:

```bash
# Matches vm-abc123def.reddog.microsoft.com
paperctl pull vm-abc123def
```

Pull with time range:

```bash
paperctl pull vm-abc123 --since -24h
paperctl pull vm-abc123 --since "2026-01-29T00:00:00" --until "2026-01-29T12:00:00"
```

Pull to specific location:

```bash
paperctl pull vm-abc123 --output ~/logs/worker.txt
paperctl pull vm-abc123 --output ~/logs/  # Uses system name as filename
```

Pull multiple systems in parallel:

```bash
paperctl pull vm-abc,vm-def,vm-ghi --output ~/logs/
```

### Search logs

Search across all systems:

```bash
paperctl search "error" --since -1h
paperctl search "error AND timeout" --since -24h --limit 100
```

Search specific system:

```bash
paperctl search "error" --system vm-abc123 --since -1h
```

Save search results to file:

```bash
paperctl search "error" --since -1h --file errors.txt
```

### List entities (hosts)

```bash
paperctl entities list
paperctl entities list --type Host --output json
paperctl entities list --name web-1
```

### Show entity details

```bash
paperctl entities show <entity-id>
paperctl entities show <entity-id> --output json
```

### List available entity types

```bash
paperctl entities list-types
```

### View configuration

```bash
paperctl config show
```

## Query syntax

SWO search uses text matching with boolean operators. No regex or wildcards.

| Operator | Example |
|----------|---------|
| AND | `error AND timeout` |
| OR | `error OR warning` |
| NOT | `error NOT debug` |
| Exact phrase | `"connection refused"` |

## Time formats

| Format | Example |
|--------|---------|
| Relative | `-1h`, `-24h`, `-7d`, `2 hours ago` |
| ISO timestamp | `2026-01-29T00:00:00Z` |
| Natural language | `yesterday`, `last week` |

## Output formats

Use `--format` to change output:

```bash
paperctl pull vm-abc123 --format json
paperctl pull vm-abc123 --format csv
paperctl search "error" --output json
```

## Common workflows

### Download Taskcluster worker logs

Get worker IDs from Taskcluster, then pull logs:

```bash
# Get recent workers from a pool
curl -s "https://firefox-ci-tc.services.mozilla.com/api/worker-manager/v1/workers/gecko-t%2Fwin11-64-24h2-alpha" | \
  jq -r '.workers | sort_by(.created) | reverse | .[0:3] | .[].workerId'

# Pull logs using partial worker ID
paperctl pull vm-abc123def
```

### Search for errors across workers

```bash
paperctl search "error" --since -1h --file errors.txt
```

### Investigate specific timeframe

```bash
paperctl pull vm-abc123 --since "2026-01-29T10:00:00" --until "2026-01-29T11:00:00" --output incident.txt
```

## Migration from v1.x

v2.0 switched from Papertrail API to SolarWinds Observability API:

| v1.x | v2.0 |
|------|------|
| `PAPERTRAIL_API_TOKEN` | `SWO_API_TOKEN` |
| `paperctl systems list` | `paperctl entities list` |
| `paperctl groups list` | Removed (not in SWO API) |
| `paperctl archives list` | Removed (not in SWO API) |
| `--group` option on search | Removed |
| System IDs (integers) | Entity IDs (strings) |

## Gotchas

- SWO search has no regex or wildcards — just text + boolean operators (`AND` / `OR` / `NOT`). Quote exact phrases.
- v2.0 uses `SWO_API_TOKEN`, not the v1.x `PAPERTRAIL_API_TOKEN`. Old configs will silently fail auth.
- Partial worker IDs match — `paperctl pull vm-abc123def` will find `vm-abc123def.reddog.microsoft.com`. Don't bother resolving the full hostname.
- If the worker never came up, papertrail has nothing — switch to `tc-logview` for the worker-manager view, then to `splunk` for Azure-side events.
