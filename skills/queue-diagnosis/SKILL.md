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

Both cloud pools (e.g., `gecko-t/win11-64-25h2`) and hardware pools (e.g.,
`releng-hardware/win11-64-24h2-hw`) are supported. Hardware pools have limited
supply-side data because they are not managed by Taskcluster worker-manager.

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

The script outputs a JSON report with sections: `pool_status`,
`queue_times`, `daily_volume`, `top_pushers`, `top_task_groups`,
`unstarted_task_groups` (only when present), `links`, and `diagnosis`.
Start with `diagnosis`: it is the script's first-pass classification of
whether the queue is supply-side infrastructure pressure, demand-side load,
mixed, recently impacted, currently clear, or inconclusive. Then verify the
classification against the raw sections before presenting it to the user.

`diagnosis.verdict` is intentionally heuristic:

- `supply-side` — active backlog with infrastructure evidence such as
  worker-manager warnings, provisioning errors, low effective capacity,
  Azure ghost workers, or Spot eviction storms.
- `demand-side` — active backlog primarily explained by task volume spikes,
  concentrated try/bot pushes, or one project dominating recent demand.
- `mixed` — both infrastructure pressure and demand spike signals are present.
- `recently-impacted` — no current pending backlog, but queue-time impact was
  high in the lookback window.
- `no-active-backlog` — no pending backlog and no large recent queue-time
  impact.
- `inconclusive-active-backlog` — pending tasks exist, but the gathered data
  does not clearly identify supply or demand as the cause.
- `auth-blocked` — Taskcluster auth failed; run `taskcluster signin` and
  rerun before making a supply-side claim.

Use `diagnosis.evidence` and `diagnosis.next_actions` as a checklist, not as
copy-paste prose. `diagnosis.scores` exposes the internal supply/demand
heuristic strengths for transparency; treat them as relative signal, not a
metric. The raw data remains authoritative.

`pool_status.errors` is a dict of `{normalized_description: {count,
sample}}` — use `count` for frequencies and `sample` when quoting the
actionable text back to the user. `pool_status.oldest_error` and
`newest_error` bound the reporting window so you can tell if errors are
ongoing or stale.

`unstarted_task_groups` lists groups with 0 started tasks (still pending
or scheduled). Surface these separately if present — they can mask real
supply issues if lumped in with active groups.

If `pool_status.auth_failure` is `true`, the Taskcluster CLI failed to
authenticate. Tell the user to run `taskcluster signin` and stop — the
supply-side data in the report is unavailable. Do not confuse this with
a hardware pool (which sets `managed: false`, not `auth_failure`).

Every claim in the summary must have a clickable link so the user can
verify it. The report provides these automatically.

## Interpreting results

### Hardware pools (releng-hardware)

Hardware pools (provisioner `releng-hardware`) are not managed by Taskcluster
worker-manager. The worker-manager APIs return 404 for these pools, so the
`pool_status` section will not include capacity, provider, or provisioning
error data. Supply-side analysis is limited to the queue pending count (from
the queue API) and BigQuery task run data (queue times, volume, expirations).
For hardware pool supply issues, check the physical machine fleet status
outside of this tool.

### Supply-side problems (infrastructure)

Look at the `pool_status` section (cloud/managed pools only).

**`warnings` vs `notes`:**
- **`warnings`** fires only when stuck workers are actively blocking demand:
  high stopping_pct AND pending tasks AND near-max capacity. Always surface
  these prominently — they indicate real supply-side pain.
- **`notes`** describes unusual state that isn't currently urgent. A pool
  with 0 pending and 0 running but 100% stopping is draining between
  shifts, not blocked. Mention it but don't treat it as a crisis.

**Signal fields:**
- `stopping_pct` — fraction of currentCapacity in 'stopping'. Healthy spot
  churn is under ~10%; 30%+ is unusual regardless of urgency.
- `oldest_stopping_age_minutes` — how long the oldest stopping worker has
  been stuck. Normal spot eviction cleanup is <30 min; >60 min means
  worker-manager likely can't reap them. This is a strong signal that
  cloud VMs are gone but TC is still tracking them.
- `capacity_headroom` / `capacity_headroom_pct` — how many more workers
  worker-manager could request before hitting maxCapacity. Low headroom
  with pending tasks is the "can't scale up" signal.
- `effective_capacity_ceiling` / `effective_capacity_pct` — `max_capacity -
  stopping`. The real ceiling if every stopping worker is a zombie. When
  `effective_capacity_pct` is well below 100%, the reported capacity is
  inflated by stuck workers and `current_capacity` alone is misleading.
  Quote this number when describing pool state, not just `current_capacity`.
- `azure_ghost_check` — present on Azure pools when the `az` CLI is
  available. Contains `ghost_count`, `real_stopping_count`,
  `azure_vms_in_rg`, `ghost_pct`, and `vm_lifetime`. A non-zero
  `ghost_count` is direct proof that worker-manager is tracking phantom
  workers (TC says 'stopping' but no matching VM exists in the Azure
  resource group). Cite this number in the summary.
- `spot_eviction_history` — Azure's own 28-day trailing Spot eviction
  rate per region for this pool's VM SKU, pulled from the
  `SpotResources` Azure Resource Graph table via REST. Contains
  `vm_size`, `source`, `per_region: [{region, eviction_rate,
  eviction_pct_midpoint}]` sorted worst-first, and
  `regions_without_data` for any configured region the table doesn't
  cover. Eviction rate is a bucket (`0-5`, `5-10`, `10-15`, `15-20`,
  `20+` — percent-per-hour chance of eviction) so treat it as
  ordinal, not precise. This is a reference table, not derived from
  our workers. Use it to tell "chronically bad region" apart from
  "recent capacity shift": a region with historical 0-5% but live
  `vm_lifetime` showing <20% past-2h survival is a storm in a
  normally-healthy region, and the script will surface that as a
  dedicated note.
- `azure_ghost_check.vm_lifetime` — the critical signal for
  distinguishing "reaper is stuck" from "Spot is evicting too fast":
  - `median_age_minutes`, `oldest_age_minutes`, `pct_under_1h`,
    `pct_over_2h` summarize how long live Azure VMs are surviving.
  - `age_buckets` breaks the fleet into `lt_30m`, `30m_1h`, `1h_2h`,
    `2h_4h`, `4h_8h`, `gt_8h`.
  - `per_region` lists per-region VM counts, median age, and how many
    survived past 2h — the "healthy regions" vs "eviction zones"
    split you'd otherwise have to derive by hand.
  When `pct_under_1h` is high and `pct_over_2h` is near zero, it is a
  Spot-eviction storm, not a scanner bug — the script surfaces this as
  a warning/note automatically.

**Don't over-index on a single error bucket.** `errors` is sorted by count
descending — the top entries are the recurring issues, the tail is noise.
A bucket with count=1 over a multi-day window is usually a one-off event,
not a pool-wide problem. Also consult `errors_by_region` before blaming a
region: if errors are spread across all regions roughly in proportion to
worker distribution, it's background churn, not a regional outage. A
single-region concentration (>40% from one region) is what justifies
calling out a region-specific cause.

**`region_health`** joins per-region worker distribution with per-region
error counts so you can answer "which regions are still landing VMs?".
Each row has `region`, `running`, `stopping`, `requested`, and `errors`,
sorted by `running` descending. Regions with non-zero running and zero
errors are safe fallback capacity; regions with many errors and zero or
near-zero running are effectively shut out right now (common on GCP
during single-zone Spot scarcity). Use this when suggesting which zones
to prioritize in launchConfigs or when explaining why scale-up is failing.
Worker fetching is capped at 10k, so on very large pools the running and
stopping counts may be proportionally undercounted but the ranking is
still useful.

**Other supply-side issues to check:**
- **High error count relative to running workers** — provisioning failures
  are preventing scale-up. Check `errors` for patterns (quota exhaustion,
  image failures, deployment conflicts).
- **Running workers well below max_capacity despite pending tasks** — cloud
  provider can't fulfill requests. Could be regional quota limits, spot VM
  scarcity, or image issues.
- **OS provisioning timeouts** — the bootstrap script is slow. Often happens
  under load or in specific regions.

For Azure pools, the script runs this cross-check automatically when the
`az` CLI is authenticated (subscription `108d46d5-fe9b-4850-9a7d-8c914aa6c1f0`
for FXCI). The result appears in `pool_status.azure_ghost_check`. If the
check is skipped, the dict will contain a `skipped` field explaining why
(az not installed, auth failed, resource group not found, etc.) — tell
the user to run `az login` if authentication is the issue.

Common spot pool errors that are NOT problems:
- "Operation execution has been preempted by a more recent operation" — normal
  spot VM lifecycle
- Concurrent request conflicts — Azure ARM template race conditions, self-healing

#### Spot-eviction storm vs. reaper lag

A pool with a huge `ghost_count` and pending tasks looks like a
worker-manager bug, but it is usually not. The two patterns produce the
same top-line symptoms (high `stopping`, low `effective_capacity_pct`,
pending tasks) but have completely different fixes. Use
`azure_ghost_check.vm_lifetime` to tell them apart before blaming
worker-manager:

- **Spot-eviction storm** (upstream, cloud-side): `pct_under_1h >= 70`
  and `pct_over_2h <= 15`. VMs are being evicted inside the first hour.
  Ghost count is a *lagging indicator* of eviction rate — every VM
  eventually becomes a ghost because Spot kills it before it can work.
  Scanner tuning does nothing here; the fix is launchConfig region mix
  (prune hot zones), raising `maxCapacity` to absorb the ghost
  overhead, or adding non-Spot baseline. Confirm by reading
  `vm_lifetime.per_region` — healthy regions have non-zero
  `survived_over_2h`; eviction zones have zero.
- **Reaper lag** (worker-manager side): VMs survive hours in Azure
  (`pct_over_2h` is meaningful, e.g. 40%+), but `ghost_count` is also
  high because TC is tracking many records Azure has deleted. The
  scanner's deprovision chain is sequential — one resource per ~60 min
  revisit, so 5 resources ≈ 5 hours per ghost. Confirm by pulling
  worker-manager logs and counting `setting state to STOPPED`
  transitions per hour; if arrival rate exceeds reap rate over time,
  the backlog will grow. If they match, the pool is at an inefficient
  but stable steady state.

Don't reason from `lastDateActive` being absent in the TC API response
— that field is not returned by `listWorkersForWorkerPool`, so "every
worker looks idle" is a quirk of the API, not evidence that workers
never claimed tasks.

#### Worker-manager log spot-checks (optional)

When the ghost pattern needs to be attributed to a specific side, pull
worker-manager logs directly. The FXCI cluster is
`webservices-high-prod` in project `moz-fx-webservices-high-prod`.
Filter by `jsonPayload.Fields.workerPoolId` (not the top-level
`jsonPayload.message` contains operator, which won't match the pool
label).

```bash
# Reap rate (workers reaching STOPPED) in the last 6h
gcloud logging read '
  resource.type="k8s_container"
  resource.labels.cluster_name="webservices-high-prod"
  jsonPayload.Logger="taskcluster.worker-manager.provider.azure2"
  jsonPayload.Fields.workerPoolId="<pool>"
  jsonPayload.Fields.message="setting state to STOPPED"
' --project moz-fx-webservices-high-prod --freshness=6h \
  --format='value(timestamp)' | awk '{print substr($0,1,13)}' | sort | uniq -c

# Per-worker reap trace (one resource per revisit ≈ 60 min gap)
gcloud logging read '
  resource.type="k8s_container"
  resource.labels.cluster_name="webservices-high-prod"
  jsonPayload.Fields.workerPoolId="<pool>"
  jsonPayload.message:"<workerId>"
' --project moz-fx-webservices-high-prod --freshness=24h \
  --format='value(timestamp,jsonPayload.message)'
```

The `serviceContext.version` in each log entry shows the deployed
worker-manager version — useful when checking whether a specific fix
has rolled out.

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

1. **Current pool state** — pending, running, capacity utilization %. Link to
   the pool in TC using the `links.worker_pool` URL.
2. **Queue time impact** — median, p90, p95, max (convert ms to human-readable)
3. **Root cause** — demand-side, supply-side, or both, with evidence
4. **Top contributors** — which projects and pushers are driving volume. For
   each major contributor, include their largest task group links from
   `top_task_groups`. Each entry has `tc_url` (Taskcluster task group view)
   and `treeherder_url` (Treeherder job view).
5. **Trend** — is this getting better or worse (compare daily volumes)

Every top contributor and task group mentioned must have a clickable link.
The `top_task_groups` section provides both `tc_url` and `treeherder_url`
for each task group. Present these as markdown links so the user can click
through and verify.

**Example output format:**

```
wptsync@mozilla.com — 4,330 tasks across 117 groups (try)
  Largest group: [TC](https://firefox-ci-tc..../tasks/groups/Q1uV...) |
  [Treeherder](https://treeherder.mozilla.org/jobs?repo=try&taskGroupId=Q1uV...)
  641 tasks, median queue 56 min, max 2h 42min
```

### Drilling deeper with treeherder-cli

Once you've identified a problematic task group, use `treeherder-cli` for
follow-up investigation when you have the push revision (not the task group
ID). `treeherder-cli` works with revision hashes, not task group IDs.

```bash
# Check failures for a specific revision on autoland
treeherder-cli <revision> --repo autoland --json

# Filter to a specific platform
treeherder-cli <revision> --repo autoland --platform "windows.*25h2" --json

# Compare two revisions to find what changed
treeherder-cli <rev1> --compare <rev2> --json
```

Use this when you need to understand whether a specific push introduced
failures or regressions, not just that it consumed pool capacity.

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
