# Taskcluster Service-Level Changes

Cost investigations often focus on `fxci-config` (worker pool definitions). But bugs and changes in the **Taskcluster service code itself** can drive cost just as much — and sometimes more invisibly. The runtime services that provision, monitor, and tear down workers have their own change history that should be checked when investigating a cost anomaly.

## Repo

- `https://github.com/taskcluster/taskcluster` (public)
- This is the TC platform repo. Multiple services live here as a monorepo.

## Cost-relevant services

Focus on services that affect VM lifecycle and task scheduling:

| Service | Path in repo | What it does | Cost relevance |
|---|---|---|---|
| **worker-manager** | `services/worker-manager/` | Provisions, monitors, and deprovisions worker instances. Tracks state machine (RUNNING / STOPPING / STOPPED). | Direct — bugs here can leave workers in stuck states, block capacity, or cause over-provisioning |
| **worker-scanner** | (part of worker-manager) | Reconciles worker state with cloud reality, catches orphans | Direct — bugs slow cleanup, allow phantom entries to accumulate |
| **queue** | `services/queue/` | Task scheduling, claim management | Indirect — claim timeout settings, retry behavior |
| **provisioner-manager** | (legacy) | Older provisioning logic | Generally not in active use for modern pools |
| **generic-worker** | `workers/generic-worker/` | The worker process that runs on each VM (Linux/Windows) | Indirect — task overhead, retry behavior on the worker side |
| **docker-worker** | `workers/docker-worker/` | Linux container worker | Indirect (GCP-side mostly) |

For Azure cost investigations, **worker-manager and worker-scanner are the main suspects** when fxci-config doesn't explain the change.

## How to check service-level changes

### Recent commits across the repo (very broad)
```bash
gh pr list --repo taskcluster/taskcluster --state merged --limit 50 --search "worker-manager OR worker-scanner OR provisioner"
```

Or via the API:
```bash
curl -s "https://api.github.com/repos/taskcluster/taskcluster/commits?since=YYYY-MM-DDT00:00:00Z&per_page=50&path=services/worker-manager" \
  | python3 -c "import json,sys; [print(c['commit']['committer']['date'][:10], c['sha'][:8], c['commit']['message'].split(chr(10))[0][:90]) for c in json.load(sys.stdin)]"
```

### Specific to a deployment/release
TC services are deployed from tagged releases. Knowing **which release was active during your cost-anomaly window** is essential — a bug merged into main may not be in production yet, and a bug in a deployed release may have been fixed in main but not yet redeployed.

To check what's deployed: TC engineering team or your deployment infrastructure logs. The release tag history:
```bash
curl -s "https://api.github.com/repos/taskcluster/taskcluster/releases?per_page=20" \
  | python3 -c "import json,sys; [print(r['tag_name'], r['published_at'][:10], r['name']) for r in json.load(sys.stdin)]"
```

### Search for cost-relevant patterns in commit messages

| Pattern | Why it matters |
|---|---|
| `deprovision`, `terminate`, `cleanup` | Worker teardown logic — bugs here cause stuck states or over-billing |
| `maxCapacity`, `capacityPerInstance`, `quota` | Provisioning ceilings and counting logic |
| `preempt`, `evict`, `spot` | Spot-VM-specific handling |
| `retry`, `claim-expired`, `worker-shutdown` | Task retry behavior |
| `state machine`, `STOPPING`, `STOPPED` | Worker lifecycle state |
| `idle`, `inactivity`, `timeout` | Idle billing and shutdown behavior |
| `404`, `not found`, `error handling` | Often where cleanup bugs hide — unhandled error responses during resource deletion can leave workers in stuck states |

### Cross-reference issues alongside PRs

Bugs are often filed before fix PRs land. Check `https://github.com/taskcluster/taskcluster/issues` for issues filed during or after the cost-anomaly window — they may describe symptoms you observed.

**Look at recently-merged fix PRs in particular.** If engineering merged a fix recently, that bug was active during the period the fix was needed. The window between bug introduction and fix is exactly the period where its cost impact would manifest. Examples of this pattern:

- A bug introduced months ago may be operationally invisible until a workload condition triggers it (e.g. a pre-existing cleanup bug only manifests under high eviction rates because cleanup mechanisms keep up at low rates)
- A fix PR's description usually references the issue and explains the failure mode — that's your starting point
- Even if the fix is already deployed, the cost data window before the fix deployment is when the bug was actively contributing

## When TC service changes are the answer (vs fxci-config)

Use this rough decision tree:

| Symptom | Most likely source |
|---|---|
| Cost per pool changed but pool config didn't | TC service-level (provisioning logic, lifecycle bugs) |
| Pool config recently changed (vmSize, region, weight) | fxci-config |
| New cost meter appeared | Either — could be SKU change (fxci-config) or new resource type provisioned (TC service) |
| Cost rises with eviction rate | TC service (cleanup/teardown logic) — cost should not scale with evictions if cleanup works correctly |
| Queue starvation while VMs are available | TC service (worker-manager state tracking, provisioner counting) |
| Workers stuck in non-running state | TC service (state machine, deprovisioning) |
| Cost change correlates with a fxci-config commit | fxci-config |

## TC services often interact with fxci-config

Some bugs are TC-service-side but only manifest when fxci-config configures certain values. Example:
- fxci-config sets `maxCapacity: 2000`
- TC worker-manager has a bug that miscounts capacity (#8517: phantom workers count against the cap)
- The two together produce a behavior neither alone would
- Fix is in TC services, not fxci-config

When investigating, check both. A change in either repo (or interaction between them) can be the answer.

## Operational note: ephemeral disks limit forensics

If your worker pools use ephemeral OS disks (cheaper, but VM-internal storage gone on stop/eviction):
- Worker-manager and worker-scanner logs are still available (TC service-level, captured externally)
- VM-internal logs (worker process logs, Windows event logs) are NOT available after the VM is gone
- For investigating service-level bugs that manifest in VM-side state, the TC service logs are your only window

See `spot-evictions.md` for more on ephemeral-disk constraints.
