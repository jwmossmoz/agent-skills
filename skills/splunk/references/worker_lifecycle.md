# Worker lifecycle in `azure_audit`

What VM-side events look like in the Azure activity log, and what each
common failure signature implies for next steps.

## Event flow for a healthy worker

A normal ephemeral worker generates this rough sequence in `azure_audit`:

1. `MICROSOFT.NETWORK/NETWORKINTERFACES/WRITE` — `resultType=Start`, then `Success`.
2. `MICROSOFT.COMPUTE/DISKS/WRITE` — OS disk allocated.
3. `MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE` — `resultType=Start`,
   `resultSignature=Started`. This is the create-attempt event.
4. `MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE` — `resultType=Success`,
   `resultSignature=OK`. Bootstrap script ran cleanly.
5. (worker claims and runs tasks — visible in tc-logview / papertrail, not here)
6. `MICROSOFT.COMPUTE/VIRTUALMACHINES/DELETE` — `resultType=Start`, then `Success`.
7. NIC + disk DELETEs to clean up.

The skill cares mostly about steps 3–4 (provisioning outcome) and step 6
(termination timing — for lifespan analysis).

## Common failure signatures

### `Failed.OSProvisioningTimedOut`
The bootstrap script (worker-runner / generic-worker startup, sysprep,
custom-data) didn't finish within Azure's window. Azure marked the VM as
failed and the platform deleted it.

**Next step**: pull the in-VM logs for that worker via the **papertrail**
skill — the bootstrap was actually running, it just didn't finish in time.
Common causes: image regression, slow Windows update install at first boot,
network reach to Taskcluster slow.

### `Failed.Conflict`
Azure refused the operation, usually because the resource (VM, NIC) already
exists or the underlying disk/NIC is in a bad state.

**Next step**: check whether worker-manager retried and ended up creating
two VMs with the same name (rare). More commonly an NIC was leaked from a
previous failed provision. Cross-reference with `tc-logview` to see if
worker-manager logged a corresponding error.

### `Failed.OperationPreempted` / "preempted by a more recent operation"
The user's notes call this out specifically: on **25H2 Spot pools**, this is
**Azure spot eviction mid-provisioning**, not a Taskcluster bug. The pool
was provisioning a spot VM and Azure pulled the capacity before bootstrap
finished. See `~/.claude/projects/-Users-jwmoss/memory/project_25h2_operation_preempted.md`.

**Next step**: confirm the pool is using spot capacity (`gecko-t/win11-64-25h2`,
`-gpu`, `-large` are all spot). If eviction rate spikes, that's an Azure
capacity signal — escalate to Azure support, not a TC fix.

### `Failed.AllocationFailed` / `Failed.OverconstrainedAllocationRequest`
Azure had no capacity for the requested SKU + region combo, or the
constraints (zone, dedicated host) couldn't be satisfied. Common around
peak demand windows.

**Next step**: spread across more regions / zones; check if the pool's
`launchConfig` is over-constrained.

### `Failed.SkuNotAvailable`
The requested VM size isn't offered in the chosen region/zone (often after
Azure rotates SKUs). Image is fine; pool config needs updating.

## When VMs persist much longer than expected

Symptom: lifespan-bucket query (see `query_examples.md`) shows VMs in the
`8hr+` bucket for an aggressively-ephemeral pool.

**Causes to check**:
1. Worker-manager scanner wasn't running — `tc-logview` `scan-seen` should
   show regular hits per `providerId`. If absent, the scanner crashed.
2. Worker registered but never claimed a task and the
   `idleTimeoutSecs` on the pool is huge.
3. VM is in a `Failed` provisioning state but Azure didn't auto-delete and
   neither did worker-scanner.

Trace one offender end-to-end with the per-VM recipe in `query_examples.md`,
then cross-reference `tc-logview` `worker-removed` events to see whether
Taskcluster ever asked Azure to terminate it.

## Correlating across log sources

| Question | Tool | Why |
|---|---|---|
| Did worker-manager ask for this VM? | `tc-logview` `worker-requested` | TC's view of the request |
| Did Azure accept and start it? | this skill, VM `WRITE`/`Start` | Azure-side provisioning attempt |
| Did the bootstrap script complete? | `papertrail` | In-VM log of generic-worker startup |
| Did the worker claim tasks? | `taskcluster` skill | Live task logs |
| When did Azure (or TC) delete the VM? | this skill, VM `DELETE` + `tc-logview` `worker-removed` | Compare timestamps to see who initiated |

## Investigation workflow templates

### Worker never started

1. `tc-logview` `worker-error` for the time window — was there a Taskcluster-side
   error before Azure was even called?
2. This skill: search by RG + window for `operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE"`
   `resultType=Failure`. Group by `resultSignature` for the cause.
3. If `OSProvisioningTimedOut` → papertrail for the in-VM bootstrap log.
4. If `Conflict` / `AllocationFailed` → Azure platform issue, not the image.

### Worker terminated unexpectedly mid-task

1. `tc-logview` `worker-removed` for the worker pool — TC's reason field is
   the most reliable. (`spot-eviction`, `task-failure`, `health-check`, etc.)
2. This skill: trace the VM's `resourceId` for `MICROSOFT.COMPUTE/VIRTUALMACHINES/DELETE`
   events — was Azure or TC the one that initiated?
3. `papertrail` for the running worker — look for OOM, disk-full, agent crashes
   prior to deletion.

### High failure rate on a pool

1. This skill: stats by `operationName` + `resultSignature` for the pool's RG
   over the suspect window. Identify the top 3 failure signatures.
2. `tc-logview`: are there `worker-error` events that precede each
   provisioning failure? If yes, the provisioning never reached Azure — it's
   a worker-manager / config issue.
3. Cross-pool comparison: run the same query against the comparison pool
   (`-24H2` vs `-25H2`) over the same window. A pool-specific rate spike
   points at the image, the pool config, or the VM SKU.
