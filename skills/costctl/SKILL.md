---
name: costctl
description: >
  Use when answering Firefox CI cost questions with costctl: syncing or querying
  the local DuckDB lake of GCP and Azure CI costs with Taskcluster context,
  finding waste, or looking up spot prices. DO NOT USE FOR live Cost Management
  API diagnosis; use azure-cost-analysis.
metadata:
  version: "2.0"
---

# costctl

Local DuckDB lake of CI costs (fxci_derived, Azure exports, worker-manager pools) plus spot prices.

## Prerequisites

`costctl` from private `jwmossmoz/costctl` (`make install`), `uv`, `gcloud` with BigQuery on
`mozdata`, Azure CLI, and `~/.config/costctl/lake.toml` from `lake/lake.toml.example`.

## Usage

```bash
costctl lake status        # run first: sources, date ranges
costctl lake sync          # incremental; --dry-run shows scan bytes
costctl lake ask           # list saved questions
costctl lake ask idle --since 2026-09-01 --until 2026-10-01   # --until exclusive
costctl lake sql "SELECT ..."
costctl azure spot current --sku Standard_D32ads_v5 --region eastus2   # list prices
```

Read [lake.md](references/lake.md) for views and questions before writing SQL,
[azure-sql.md](references/azure-sql.md) for `azure_cost`, and
[azure-exports.md](references/azure-exports.md) for export refresh. Report dollars with window and view.

## Examples

- "Which pools wasted most on idle instances last month?" → `costctl lake ask idle`.

## Gotchas And Troubleshooting

- Azure totals: `azure_cost`, not `worker_costs` (~25% coverage).
- GCP `worker_costs` is compute only; 2026-08-01..05 is broken upstream.
- Run cost is keyed to task submission date; compare billed vs attributed over weeks.
- Never pull GCP billing `labels` or `billing_views.gcp_billing_export_v3` (TB scans).
- Write `AS usd`; DuckDB rejects bare `cost` aliases.

## Related Skills

- **azure-cost-analysis** for live Cost Management API diagnosis.
