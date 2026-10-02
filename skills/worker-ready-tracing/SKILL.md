---
name: worker-ready-tracing
description: >
  Use when measuring Taskcluster Azure VM startup from worker request through
  boot maintenance to generic-worker readiness. DO NOT USE FOR test failure
  triage.
metadata:
  version: "1.1"
---

# Worker Ready Tracing

Separate cloud allocation time from guest-controlled startup time.

## Scope

| Source | Evidence |
|---|---|
| `tc-logview` | Worker request, registration, and task claim |
| Papertrail | Windows boot, maintenance, and `workerReady` events |
| Splunk | Azure VM and NIC activity when `--splunk` is set |
| Yardstick | Pool trends when `--yardstick` and a pool ID are set |

## Prerequisites

Install `tc-logview`, `paperctl`, and Python 3.10 or later. Configure
Papertrail. Open Splunk or Yardstick only for its optional flag.

## Usage

```bash
TRACE=~/.claude/skills/worker-ready-tracing/scripts/trace_worker_ready.py

$TRACE vm-abc123 --since 6h --papertrail-limit 500
$TRACE vm-abc123 --since 6h --splunk
$TRACE vm-abc123 --since 6h \
  --worker-pool-id gecko-t/win11-64-25h2 --yardstick
```

Use a tight absolute window for old workers. Run `$TRACE --help` for options.

## Interpretation

Use `workerReady` as the ready point. `worker-running` records worker-manager
registration and can be minutes earlier. Read
[markers.md](references/markers.md) for each marker.

## Gotchas

- Use raw Azure `time`, not Splunk `_time`, for lifecycle calculations.
- Increase `--papertrail-limit` for long windows.
- Yardstick data is aggregated by pool. It is not a per-VM trace.
- An empty queue can produce no `task-claimed` event after `workerReady`.
- Run only one Splunk browser-harness query at a time.

## Related Skills

- Use **papertrail** for an ad hoc guest-log search.
- Use **worker-image-investigation** for test or image failures.

## References

- [yardstick-prometheus.md](references/yardstick-prometheus.md): trend queries
