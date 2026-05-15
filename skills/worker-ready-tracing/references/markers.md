# Lifecycle Markers

Use these markers to keep the timeline precise. Do not collapse them into one
"startup" number unless the user explicitly asks for a broad rollup.

## Single-VM Markers

| Marker | Source | Meaning |
|---|---|---|
| `worker-requested` | `tc-logview` | worker-manager created/requested a worker |
| Azure VM write `Start` | Splunk `index=azure_audit` | Azure create request started |
| Azure VM write `Accept` | Splunk `index=azure_audit` | Azure accepted VM create |
| Azure VM write `Success` | Splunk `index=azure_audit` | Azure VM write completed |
| `worker-running` | `tc-logview` | worker registered with worker-manager |
| `instanceBoot` | Papertrail `WORKER_METRICS` | observability-only log event with OS boot time reported by generic-worker host info |
| `maintain:*` | Papertrail `MaintainSystem` | Windows boot scheduled task stages |
| `workerReady` | Papertrail `WORKER_METRICS` | observability-only log event emitted when generic-worker is about to call `queue.claimWork` |
| `task-claimed` | `tc-logview` | queue observed a task claim |
| `instanceReboot` | Papertrail `WORKER_METRICS` | observability-only log event showing generic-worker requested reboot after task completion |

## Code References

Taskcluster:

- `workers/generic-worker/main.go`: `workerReady` is emitted before the first
  `queue.claimWork` call.
- `workers/generic-worker/metrics.go`: `logEvent` emits `WORKER_METRICS` JSON.
- `services/worker-manager/src/providers/provider.js`: records
  `worker_manager_worker_registration_seconds` on first `workerRunning`.
- `services/worker-manager/src/api.js`: records
  `worker_manager_worker_provision_seconds` and
  `worker_manager_worker_startup_seconds` when registration includes
  `systemBootTime`.
- `services/worker-manager/src/monitor.js`: Prometheus metric definitions.

Ronin/worker image:

- `ronin_puppet/modules/win_scheduled_tasks/files/azure-maintainsystem.ps1`:
  Azure boot path runs `Set-AzVMName`, `Run-MaintainSystem`, optional
  `Puppet-Run`, `LinkZY2D`, and `Start-WorkerRunner`.
- `ronin_puppet/modules/win_scheduled_tasks/manifests/maintain_system.pp`:
  creates the boot-triggered `maintain_system` scheduled task.
- `worker-images/scripts/windows/CustomFunctions/Bootstrap/Public/Set-RoninRegOptions.ps1`:
  initializes `HKLM:\SOFTWARE\Mozilla\ronin_puppet\inmutable` to `false`.

## Interpretation

`worker-manager worker_registration_seconds` and `tc-logview worker-running`
end at worker-manager registration. They do not prove that generic-worker is
ready to accept tasks.

`WORKER_METRICS` does not drive scheduling or provisioning. Use it only as the
in-VM timestamp source. `workerReady` is the readiness point because
generic-worker logs it immediately before the first call to `queue.claimWork`.
If there is already pending work, `workerReady`, `task-claimed`, and `taskStart`
can all land in the same second.

For post-task reboot analysis, use:

```text
instanceReboot -> next instanceBoot -> next workerReady
```

That separates the actual reboot interval from Windows boot-script and
generic-worker startup work.
