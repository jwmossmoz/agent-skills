---
name: papertrail
description: |
  Query and download logs from Papertrail using the paperctl CLI. Use when:
  (1) Downloading logs from Taskcluster workers or other systems
  (2) Searching for specific log entries across systems
  (3) Investigating CI failures by pulling worker logs
  (4) Listing available systems or groups in Papertrail
  Triggers: "papertrail", "pull logs", "worker logs", "download logs", "search logs"
---

# Papertrail

Query and download logs from Papertrail using `paperctl`.

## Prerequisites

Requires `PAPERTRAIL_API_TOKEN` environment variable or `~/.config/paperctl/config.toml`.

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

### List systems

```bash
paperctl systems list
```

## Query syntax

Papertrail search uses text matching with boolean operators. No regex or wildcards.

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
