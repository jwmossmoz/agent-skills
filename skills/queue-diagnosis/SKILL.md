---
name: queue-diagnosis
description: |
  Diagnose why a Taskcluster worker pool queue is backed up. Checks pool health
  (pending tasks, capacity, provisioning errors) via Taskcluster CLI and analyzes
  demand patterns (queue times, task volume by project, top pushers) via BigQuery.
  Produces a diagnostic summary identifying demand-side vs supply-side causes.
  Use whenever a worker pool has high pending counts, elevated queue times, or
  deadline-exceeded expirations. Also use when someone asks "why is the queue
  backed up", "why are tasks waiting", "what's wrong with <pool>", or mentions
  pending task counts for any gecko-t or releng-hardware pool.
---

# Queue Diagnosis

Diagnose why a Taskcluster worker pool queue is backed up by combining
real-time pool status from Taskcluster with historical demand analysis from
BigQuery.

## Arguments

The pool ID in `provisioner/worker-type` format (e.g., `gecko-t/win11-64-25h2`).

## How to use

Run the diagnostic script. It gathers all data in parallel and produces a
structured report:

```bash
uv run scripts/diagnose.py <pool-id>
```

Example:
```bash
uv run scripts/diagnose.py gecko-t/win11-64-25h2
```

The script outputs a JSON report with four sections: `pool_status`,
`queue_times`, `daily_volume`, and `top_pushers`. Read the output and
present a diagnostic summary to the user.

## Interpreting results

### Supply-side problems (infrastructure)

Look at the `pool_status` section:

- **High error count relative to running workers** — provisioning failures are
  preventing scale-up. Check `errors` for patterns (quota exhaustion, image
  failures, deployment conflicts).
- **Running workers well below max_capacity despite pending tasks** — Azure
  can't fulfill requests. Could be regional quota limits, spot VM scarcity, or
  image issues.
- **Many stopping workers** — normal for spot pools (eviction churn), but if
  stopping > 30% of running, churn is eating into effective capacity.
- **OS provisioning timeouts** — the bootstrap script is slow. Often happens
  under load or in specific Azure regions.

Common spot pool errors that are NOT problems:
- "Operation execution has been preempted by a more recent operation" — normal
  spot VM lifecycle
- Concurrent request conflicts — Azure ARM template race conditions, self-healing

### Demand-side problems (too many tasks)

Look at `daily_volume` and `top_pushers`:

- **Task volume 2-3x above recent baseline** — the pool is healthy but
  overwhelmed. Compare current day to the same weekday last week.
- **`try` project dominating** — developer try pushes or automated sync bots
  (wptsync, phabricator) flooding the pool. Try tasks are lower priority but
  still consume capacity.
- **`autoland` spike** — high landing rate, often tied to release cycles.
  Check for `elm`, `maple`, `mozilla-beta`, or `mozilla-release` activity as
  signals of an active merge/release.
- **Single pusher with disproportionate volume** — one person or bot submitting
  thousands of tasks. Worth flagging.
- **Deadline expirations (expired_count)** — tasks that never got picked up
  before their deadline. If > 2-3% of total, the pool is seriously behind.

### Presenting the diagnosis

Structure the summary as:

1. **Current pool state** — pending, running, capacity utilization %
2. **Queue time impact** — median, p90, p95, max (convert ms to human-readable)
3. **Root cause** — demand-side, supply-side, or both, with evidence
4. **Top contributors** — which projects and pushers are driving volume
5. **Trend** — is this getting better or worse (compare daily volumes)

## Authentication

The script calls two external services. Both must be authenticated before
the skill can run.

### Taskcluster

The `taskcluster` CLI must be configured with credentials that have read
access to the worker-manager and queue APIs. Authentication is set via
environment variables:

- `TASKCLUSTER_ROOT_URL` — must be `https://firefox-ci-tc.services.mozilla.com`
- `TASKCLUSTER_CLIENT_ID` — your Taskcluster client ID
- `TASKCLUSTER_ACCESS_TOKEN` — your Taskcluster access token

These are typically configured in your shell profile or via
`taskcluster signin`. Verify with:

```bash
taskcluster api workerManager workerPool gecko-t/win11-64-25h2
```

### Redash (BigQuery)

The Redash queries require an API key for `sql.telemetry.mozilla.org`:

- `REDASH_API_KEY` — your personal Redash API key

To get a key: log in to [sql.telemetry.mozilla.org](https://sql.telemetry.mozilla.org),
go to your profile (top-right menu), and copy the API key. Verify with:

```bash
uv run ~/.claude/skills/redash/scripts/query_redash.py --sql "SELECT 1 AS test"
```

### Runtime dependencies

- `taskcluster` CLI (install via `pip install taskcluster` or download binary)
- `uv` (install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Redash skill installed at `~/.claude/skills/redash`

## Manual queries

If the script fails or you need to dig deeper, see `references/queries.md`
for the individual SQL queries you can run via the Redash skill.
