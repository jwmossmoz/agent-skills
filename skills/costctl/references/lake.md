# costctl lake reference

Data lives in `~/moz_artifacts/ci-cost/` (`parquet/<source>/` plus `lake.duckdb` views).
Override with `COSTCTL_LAKE_DIR`; config path with `COSTCTL_LAKE_CONFIG`.

## Views

| View | Grain / columns |
|---|---|
| `task_cost` | one task run: `date, cloud_provider, pool, kind, label, project, test_platform, test_suite, state, reason_resolved, run_duration, run_cost, worker_instance_id` |
| `instance_day` | instance × day: `billed_cost, attributed_cost, runs, busy_seconds, uptime, pool, name` |
| `worker_costs`, `worker_usage` | raw fxci_derived instance cost and uptime (GCP plus partial Azure) |
| `tasks`, `task_runs`, `task_run_costs` | raw fxci_derived; `tasks.task_queue_id` is the pool |
| `azure_cost` | Azure export rows with `worker_pool_id` from tags |
| `pools`, `pool_snapshots` | worker-manager config: `min_capacity, max_capacity, machine_types, regions, queue_inactivity_timeout, config` |

## Saved questions

| Question | Answers |
|---|---|
| `idle` | GCP billed minus attributed spend and zero-run instances by pool |
| `failures` | failed and exception run cost; `worker-shutdown` is a worker interruption (often spot preemption, also admin shutdown or SIGTERM) |
| `per-task` | cost per task by pool, kind, and suite (`--pool`) |
| `trend` | weekly runs, cost, and $/busy-hour: volume vs rate (`--pool`) |
| `capacity` | top GCP pools with min/max capacity, idle timeout, machine types |
| `change` | before/after a change per pool: billed, compute/storage, $/completed run, run time (`--before D --after D --days N`) |
| `daily` | daily GCP and Azure totals |
| `azure-overhead` | untagged or non-VM Azure spend |
| `azure-pools` | Azure VM cost by pool, SKU, region, pricing model (`--pool`) |

Add a question as `lake/questions/<name>.sql` in the costctl repo. The first line is
`-- description`. `$since`, `$until`, `$pool`, `$before`, `$after`, and `$days` bind when referenced. Run `make install` afterwards.

## Spot prices

`costctl azure spot current --sku Standard_D32ads_v5 --region eastus2` (Azure Retail API, no key),
`costctl azure spot history`, `costctl gcp spot current|history --machine-type n2-standard-8` (cloudprice.net key),
and `costctl worker-pool` (tc-admin JSON on stdin). These are list prices; the lake has actual spend.

## Sources and costs

- `sync` pulls fxci_derived day partitions on `mozdata` (~9 GB for two months, ~0.5 GB daily).
  It re-pulls the last 4 days and skips older days already on disk.
- Azure: per export and month, it downloads only the latest export run and replaces that month's
  Parquet file. Months whose latest run is already imported are skipped.
- Pools: a daily snapshot of the public worker-manager API.
- BigQuery auth uses the active `gcloud` account, not ADC (`--account` to override).
- Low-level Azure tool: `costctl lake azure doctor|schema|validate|sync --help`.

## Validation

`costctl lake check` runs free local sanity checks. Expected warnings: Aug 1–5 upstream gap and about
15 duplicate runs upstream.

One-off validation on 2026-10-02: lake rows and costs matched BigQuery exactly on sample days. Azure
matched the Cost Management API (Aug exact, Sep within $0.12). GCP `worker_costs` covered 92–97% of
the September bill (compute only). To re-verify GCP against the bill, query
`moz-fx-data-shared-prod.billing_syndicate.gcp_billing_export_v1_01E7D5_97288E_E2EBA0` on `mozdata`,
selecting only `project.id`, `invoice.month`, and `cost` (~186 GB, no partition pruning). Never
select `labels` (>15 TB) or use `billing_views.gcp_billing_export_v3` (17 TB).

The newest Azure day of an open month is still accruing in the export snapshot. Treat it as partial.

## Interpretation

- `runs = 0` means no runs were attributed to that instance-day, not that it never worked. Before calling it
  waste, check the instance over the whole window: zero runs on every day points at over-provisioning or boot failures.
- `worker-shutdown` means the worker was interrupted. Call it suspected preemption unless provider evidence
  (Azure spot eviction events, GCP preemption logs) confirms it.
- High `billed - attributed` with few zero-run instances points at long idle tails (`queue_inactivity_timeout`).
- Long tasks (translations GPU) appear unattributed on later instance days, because run cost is keyed
  to the task submission date.
- GCP instance names are `replace(pool, '/', '-')-<id>`. `instance_day.pool` uses this to assign zero-run instances to a pool.
