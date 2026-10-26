# Post-merge worker-pool health check

After the fxci-config PR merges, the fxci-config deploy CI applies the
new `worker-images.yml` to worker-manager. From that point forward,
newly provisioned workers in the affected pools should be backed by the
new image. This reference describes how to verify that — and what to
escalate when it doesn't happen.

Wait at least 15–30 minutes after merge before checking. Worker-manager
re-evaluates pool config on its own cadence and existing VMs continue
running until they terminate normally; the rollout is gradual, not
instantaneous.

## Read this first: deploymentId is not a typed field

The ronin_puppet `deploymentId` is **not** projected as a typed
worker-manager log field. A query like

```bash
tc-logview query -e fx-ci --service worker-manager \
  --filter '"<deploymentId>"' --since 30m
```

returns 0 entries even when workers ARE running with the new image.
Don't burn time on substring filters as your primary signal — they
produce false negatives. Use these checks instead:

- `worker-error` events for the affected pool over the last 30 min
  (typed field `workerPoolId`) — should be flat.
- Pending counts via `taskcluster api queue pendingTasks <pool>` —
  should be at or near steady-state.
- The Taskcluster UI worker-type page (linked below) — shows worker
  count and recent task throughput at a glance.

The "confirm the deploymentId" recipe below reads the raw event
payload (where the tag actually lives) instead of substring-filtering
typed fields. Use that when you need to confirm a specific
deploymentId; use the signals above when you just need "is the
rollout healthy?".

## Identifying the pools to check

`worker-images.yml` bindings flow into `worker-pools.yml` aliases.
Before you start, list the pool IDs that consume each fxci-config
alias you bumped — `worker-pools.yml` is where pool IDs (in
`<provisioner>/<workerType>` form like `gecko-t/win11-64-25h2`) are
defined. Pull them out with:

```bash
cd ~/github_moz/fxci-config
grep -n <alias> worker-pools.yml
```

Read the 1–2 surrounding lines for the `<provisioner>/<workerType>`
pool ID — the YAML structure varies, but the pool ID is always
adjacent to the alias reference.

Phase 3's fxci-config diff is the authoritative list of which aliases
moved.

## Scope checks to after the merge, and account for idle pools

Two traps that produce a false "healthy":

1. **Scope to the merge timestamp, not a rolling window.** Get the merge
   time (`gh pr view <PR> --repo mozilla-releng/fxci-config --json mergedAt`)
   and query `--from <merge-time>`, not `--since 1h/2h`. A rolling window
   spans the pre-merge period and counts old-image workers, so the pool
   looks busy and healthy on stale data. Only workers that reach `running`
   **after** the merge are on the new image.

   ```bash
   tc-logview query -e fx-ci --type worker-running --from <merge-time> \
     --json --limit 1000 \
     | jq -r 'select(.workerPoolId|test("win10|win11|win2022")) | .workerPoolId' \
     | sort | uniq -c
   tc-logview query -e fx-ci --type worker-error --from <merge-time> --json --limit 1000 | ...
   ```

2. **Idle pools (0 pending) show no new workers.** A pool with no demand
   provisions nothing post-merge, so its new image is *configured* (launch
   config verified, see below) but **not yet observed booting**. Don't count
   those as confirmed. This bites hardest on low-traffic, previously-
   problematic pools (e.g. the ARM64 builders): a busy test pool confirms
   itself within minutes, but a quiet builder can sit idle for hours.

   For an idle pool you need to confirm, either wait for organic demand or
   push a task onto it (a `mach try` job targeting that worker type) so a
   fresh worker provisions on the new image. **Do not move the tracking
   Story to Done until every pool you care about has had a post-merge worker
   reach `running` with no worker-error** — a verified launch config alone
   is necessary but not sufficient.

## Confirming the new deploymentId is in use (Windows)

`tc-logview`'s typed fields for `worker-running` are
`providerId, registrationDuration, workerId, workerPoolId` (run
`tc-logview list --service worker-manager` to confirm). The
ronin_puppet `deploymentId` is set as a VM tag on the Azure side
during build (it lives under `vm.tags` in the worker-images config),
so to surface it from a `worker-running` event you have to read the
raw payload — the tag isn't projected as a typed field.

Run a single query first to see exactly where `deploymentId` lives in
the payload your environment returns; then build the aggregation:

```bash
# 1. Inspect a single event to find the actual jq path
tc-logview query -e fx-ci --type worker-running \
  --where 'workerPoolId="<your-pool>"' \
  --since 1h --raw --limit 1 \
  | jq '.' | grep -i deploymentid
```

Once you have the path (likely under `providerMetadata` or the
provider's `tags` block, but verify), aggregate the recently-launched
workers by it:

```bash
tc-logview query -e fx-ci --type worker-running \
  --where 'workerPoolId="<your-pool>"' \
  --since 30m --json --limit 200 \
  | jq -r '<the path you confirmed>' \
  | sort | uniq -c
```

You want the new `deploymentId` appearing in the count and old IDs
decreasing over time. If only old IDs show up after 30+ minutes,
something is wrong with the rollout (see "Escalation" below).

If reading the raw payload is too noisy, an easier substring check
works for spot-confirming a specific deploymentId:

```bash
tc-logview query -e fx-ci --service worker-manager \
  --filter '"<new-deploymentId>"' \
  --where 'workerPoolId="<your-pool>"' \
  --since 30m --limit 50
```

Loop across every pool that was bumped — the pool list is whatever
phase 3's fxci-config diff actually touched.

## Confirming the new image name (Linux)

Linux pools don't use ronin_puppet `deploymentId`; the equivalent
signal is the GCE image name. Same approach as Windows: dump one raw
`worker-running` event for the pool, find where the image reference
lives, then aggregate. Substring-filter the dated image name as a
faster alternative:

```bash
tc-logview query -e fx-ci --service worker-manager \
  --filter '"gw-fxci-gcp-l1-2404-amd64-headless-googlecompute-<YYYY-MM-DD>"' \
  --where 'workerPoolId="<your-pool>"' \
  --since 30m --limit 50
```

## Pending counts and pool capacity

Pending should not grow unboundedly post-merge. A short-lived spike is
normal as old workers drain and new ones boot, but a sustained climb
means demand is outpacing supply or new workers are failing to start.

Run `taskcluster api workerManager --help` and `taskcluster api queue
--help` to discover the exact subcommand names in your installed
taskcluster CLI before scripting; the CLI's command surface evolves
and the right subcommand for "pool config" or "pending tasks" varies
by version.

The fastest visual is the Taskcluster UI's worker-type page:
`https://firefox-ci-tc.services.mozilla.com/provisioners/<provisioner>/worker-types/<workerType>`
— substitute the provisioner and workerType from the pool ID.

## Watching for new failure modes

A bad image often shows up first as a spike in `worker-error` events.
The typed fields for `worker-error` are `description, errorId, kind,
title, workerPoolId`:

```bash
tc-logview query -e fx-ci --type worker-error \
  --where 'workerPoolId="<your-pool>"' \
  --since 2h --json --limit 200 \
  | jq -r '.title // .description // empty' \
  | sort | uniq -c | sort -rn | head -20
```

Compare against the same pool's last-week baseline. Categories that
weren't there before are the suspicious ones.

For Windows specifically, in-VM logs (NXLog / generic-worker startup)
are forwarded to SolarWinds Observability — pull them with the
`papertrail` skill if a `worker-error` count is climbing and you need
the actual error text.

## Escalation criteria

| Symptom | What it usually means | First move |
|---|---|---|
| New deploymentId/image name doesn't appear after 30 min | fxci-config deploy CI didn't apply, or the worker-images.yml diff didn't reach worker-manager | Check the most recent `apply` task in the `firefox-ci-tc` Taskcluster admin namespace; rerun if it failed. |
| Old deploymentId/image name persists for a specific pool only | The pool has a per-pool override in fxci-config that wasn't bumped | Re-grep the `worker-pools.yml` and `worker-images.yml` keys for the pool. |
| `worker-error` rate ≥ 2× baseline within 2 h of merge | Image regression — probably bad ronin_puppet content | Roll back ronin_puppet `deploymentId` to the prior value, rebuild the affected image at the next `image_version`, ship a fxci-config revert PR. |
| Pending grows steadily, no new errors | Demand-side spike or capacity limit | Hand off to the `queue-diagnosis` skill — it does a fuller supply/demand split. |
| Pending grows AND new errors | Both: image issue plus accumulated demand | Roll back first, then triage the queue once provisioning is healthy again. |

## Don't reinvent queue-diagnosis

If the post-merge check uncovers a queue that's actually backed up
rather than just slow to roll over, switch to the `queue-diagnosis`
skill — it gathers Taskcluster pool state and Redash demand data and
produces a structured diagnosis. Don't duplicate that work inline here.

## Cleanup notes

- This phase is observational. Avoid issuing terminations or capacity
  changes during the rollover unless something is clearly broken — the
  pool drains itself within an hour or so under normal conditions.
- Capture any unexpected findings in `~/moz_artifacts/` so future
  rollouts can spot the same pattern earlier.

## Phase 5 — Post-merge worker-pool health check

After merge, fxci-config's deploy CI propagates `worker-images.yml` to
worker-manager and new workers should boot from the new image. Wait 15–30 min,
then per bumped pool:

1. **Confirm the new `deploymentId` (Windows) / dated image name (Linux)** on
   freshly-provisioned workers via `tc-logview` `worker-running` events. The
   `deploymentId` is **not** a typed field — a `--filter '"<id>"'` returns 0
   even when it's live; read the raw payload instead.
2. **Scope to the merge timestamp**, not a rolling `--since` window, and
   account for idle pools: a pool with 0 pending provisions nothing post-merge,
   so its image is configured but not yet observed booting. Don't mark the
   Story Done until every pool you care about has had a post-merge worker reach
   `running` with no `worker-error`.
3. **Watch `worker-error`** by typed `workerPoolId`; a spike right after merge
   usually means a bad image — be ready to roll back.
4. If pending climbs, hand off to `queue-diagnosis` rather than triaging here.

Queries, escalation thresholds, idle-pool handling, and the rollback recipe:
`references/post-merge-health.md`.
