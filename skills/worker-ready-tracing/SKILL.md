---
name: worker-ready-tracing
description: >
  Use when tracing Taskcluster Azure VM startup from worker-manager request
  through in-VM boot scripts to generic-worker `workerReady` with
  tc-logview, paperctl, Splunk Web, and Yardstick Prometheus. Applies to
  Windows worker provisioning latency. DO NOT USE FOR task failure triage
  (use worker-image-investigation).
metadata:
  version: "1.0"
---

# Worker Ready Tracing

Trace the time from Taskcluster worker-manager provisioning a Windows Azure VM
to generic-worker being ready to accept tasks. Keep the output anchored to
timestamps and split cloud/platform time from guest-controlled startup work.

## Prerequisites

- `tc-logview` on `PATH` for worker-manager and queue events.
- `paperctl` v2.0 configured with `SWO_API_TOKEN` or
  `~/.config/paperctl/config.toml` for in-VM logs.
- `browser-harness` on `PATH`.
- Splunk Cloud tab open and signed in for `--splunk`:
  `https://security-mozilla.splunkcloud.com`.
- Yardstick/Grafana tab open and signed in for `--yardstick`:
  `https://yardstick.mozilla.org`.
- Python 3.10+.

## Scope vs. Log Tools

| Tool | Scope | Source |
|---|---|---|
| `tc-logview` | worker-manager request/registration and queue `task-claimed` events | GCP Cloud Logging |
| `papertrail` | In-VM Windows Application events and `worker-runner-service` logs | SolarWinds Observability |
| `splunk` | Azure activity log for VM/NIC create/delete/status | `index=azure_audit` |
| Yardstick | Pool-level Prometheus histograms and gauges | Grafana datasource `gcp-v2-prod` |
| `taskcluster` | Live task logs/artifacts/retriggers | Taskcluster API |

For a single VM timeline, use `tc-logview` + Papertrail, and add Splunk when
you need Azure VM/NIC lifecycle markers. Use Yardstick to compare one trace
against pool-level trends.

## Usage

Set a local variable to the installed helper:

```bash
TRACE=~/.claude/skills/worker-ready-tracing/scripts/trace_worker_ready.py
```

Trace a recent worker:

```bash
$TRACE vm-abc123 --since 6h --papertrail-limit 500
```

## Examples

Trace a tight absolute window and include Azure activity log markers:

```bash
$TRACE vm-abc123 \
  --since 2026-05-15T17:20:00Z \
  --until 2026-05-15T17:30:00Z \
  --papertrail-limit 200 \
  --splunk
```

Trace post-task reboot cycles and include Yardstick pool trend metrics:

```bash
$TRACE vm-abc123 \
  --since 2026-05-15T17:50:00Z \
  --until 2026-05-15T19:30:00Z \
  --papertrail-limit 1000 \
  --worker-pool-id gecko-t/win11-64-25h2 \
  --yardstick
```

## Workflow

1. Get a `workerId` and a tight UTC window from Treeherder, task logs,
   `tc-logview`, worker-manager output, or the Taskcluster task run.
2. Run the helper without Splunk first. This confirms Papertrail and
   `tc-logview` have enough data.
3. Add `--splunk` when you need Azure VM/NIC create markers. The helper uses
   the raw Azure Activity Log `time` field rather than Splunk `_time`.
4. Add `--yardstick` with `--worker-pool-id` to compare the single worker
   against pool-level p50/p95 registration, provision, and startup durations.
5. Interpret the in-VM split:
   - `Puppet-Run` is usually the largest controllable guest-side cost.
   - `Start-WorkerRunner` should be short.
   - `Start-WorkerRunner end -> workerReady` is generic-worker startup through
     first `queue.claimWork`.

## Key Markers

Primary single-VM timeline markers:

- `worker-requested`: worker-manager created/requested the worker.
- `azure-vm-write-*`: Azure VM write lifecycle, if `--splunk`.
- `worker-running`: worker registered with worker-manager.
- `instanceBoot`: observability-only `WORKER_METRICS` log event with OS boot
  time reported by generic-worker host info.
- `maintain:*`: Windows `MaintainSystem` begin/end markers.
- `workerReady`: observability-only `WORKER_METRICS` log event emitted when
  generic-worker is about to call `queue.claimWork`.
- `task-claimed`: queue observed a task claim from that worker.

The best "ready to accept tasks" marker is `workerReady`, not
`worker-running`. `worker-running` means worker-manager registration; it can
precede generic-worker readiness by minutes.

Mostly controllable inside the VM: Windows boot health, `maintain_system`,
`Puppet-Run`, `LinkZY2D`, `Start-WorkerRunner`, and generic-worker startup.
Mostly outside the VM: Azure allocation/VM writes and worker-manager loop
timing.

## References

- [references/markers.md](references/markers.md) explains lifecycle markers,
  source code locations, and the `inmutable=false` Puppet gotcha.
- [references/yardstick-prometheus.md](references/yardstick-prometheus.md) has
  the Yardstick dashboard, datasource, and PromQL examples.
- [references/trigger-evals.json](references/trigger-evals.json) lists routing
  eval prompts for this skill.

## Gotchas

- Splunk `_time` can lag raw Azure Activity Log `time` by several minutes. Use
  raw `time` for lifecycle math.
- Papertrail search results can be sparse or capped. Increase
  `--papertrail-limit` for multi-hour windows.
- Yardstick metrics are histograms aggregated by pool/provider/workerGroup.
  They are trend data, not per-VM traces.
- `workerReady -> task-claimed` can be zero when pending work exists. If the
  queue is empty, `workerReady` still proves the worker was ready even without a
  claim.
- Do not run multiple Splunk `browser-harness` jobs in parallel; they fight over
  the active browser tab.

## Troubleshooting

- `No events found`: widen `--since/--until` and confirm the worker ID exactly
  matches the Azure VM name.
- `Splunk query failed`: open Splunk in Chrome and confirm SSO before rerunning
  with `--splunk`.
- `Yardstick query failed`: open Yardstick in Chrome and confirm the dashboard
  loads before rerunning with `--yardstick`.

## Related Skills

- Use `papertrail` for ad-hoc in-VM log searches once the worker is known.
- Use `splunk` for broader Azure activity log analysis or provisioning failure
  patterns.
- Use `taskcluster` for live task logs, artifacts, and worker pool API calls.
- Use `worker-image-investigation` when a task failure looks image-caused rather
  than a worker startup timing issue.
