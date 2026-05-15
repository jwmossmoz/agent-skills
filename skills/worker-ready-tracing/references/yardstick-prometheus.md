# Yardstick Prometheus

Yardstick is useful for pool-level trend and regression analysis. It is not a
per-worker event log.

Dashboard folder:

```text
https://yardstick.mozilla.org/dashboards/f/feb0i93r1na4gf/taskcluster
```

Relevant dashboard:

```text
Taskcluster FirefoxCI metrics
uid: eep4jay0d9hxxx
```

Datasource:

```text
name: gcp-v2-prod
uid: adpvtjmrxoc1sb
type: prometheus
```

## Metrics

| Metric | Meaning |
|---|---|
| `fxci_worker_manager_worker_registration_seconds_bucket` | worker-manager request -> worker-manager registration |
| `fxci_worker_manager_worker_provision_seconds_bucket` | worker-manager request -> worker-reported system boot time |
| `fxci_worker_manager_worker_startup_seconds_bucket` | worker-reported system boot time -> worker-manager registration |
| `fxci_worker_manager_worker_lifetime_seconds_bucket` | worker lifetime |
| `fxci_worker_manager_pending_tasks` | pending tasks by worker pool |
| `fxci_worker_manager_total_idle_capacity` | idle worker capacity by worker pool |
| `fxci_worker_manager_claimed_tasks` | claimed tasks by worker pool |

## PromQL

Median registration time:

```promql
histogram_quantile(
  0.50,
  sum(rate(fxci_worker_manager_worker_registration_seconds_bucket{
    workerPoolId="gecko-t/win11-64-25h2"
  }[$__rate_interval])) by (le)
)
```

One-hour p95 startup time at a fixed point in time:

```promql
histogram_quantile(
  0.95,
  sum(increase(fxci_worker_manager_worker_startup_seconds_bucket{
    workerPoolId="gecko-t/win11-64-25h2"
  }[1h])) by (le)
)
```

Worker-manager queue pressure:

```promql
fxci_worker_manager_pending_tasks{workerPoolId="gecko-t/win11-64-25h2"}
fxci_worker_manager_total_idle_capacity{workerPoolId="gecko-t/win11-64-25h2"}
fxci_worker_manager_claimed_tasks{workerPoolId="gecko-t/win11-64-25h2"}
```

## Query Through Grafana

The bundled `trace_worker_ready.py --yardstick` path queries Grafana's
Prometheus proxy through an authenticated Yardstick browser tab:

```text
/api/datasources/proxy/uid/adpvtjmrxoc1sb/api/v1/query
```

Use this when you need a quick p50/p95 comparison next to a single-worker
trace. Use the dashboard UI when you need long time-series visualization.

## Gotchas

- Histogram quantiles are approximate and depend on bucket boundaries.
- Use `increase(...[1h])` for a fixed-window point-in-time summary. Use
  `rate(...[$__rate_interval])` in Grafana panels.
- These metrics end at worker-manager registration. They do not include
  `worker-running -> workerReady`.
