# Azure activity log format in Splunk

What's actually in `index=azure_audit` at Mozilla, based on real query results
against `RG-TC-GECKO-T-WIN11-64-25H2` and similar pool RGs.

## Index

- **`azure_audit`** — Azure activity log (control plane), forwarded by the
  Azure → Splunk connector. ~60 days of retention (March of any given year
  is at the edge of what's queryable in early May).
- Other indexes exist but this skill only targets `azure_audit`.

## Top-level fields the skill leans on

| Field | Example | Notes |
|---|---|---|
| `_time` | epoch | Splunk-indexed timestamp |
| `operationName` | `MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE` | Always uppercase. |
| `resultType` | `Start`, `Success`, `Failure` | Filter as `resultType="Start"` (quoted) — bare `=Start` sometimes returns 0. |
| `resultSignature` | `Started`, `Accepted.Created`, `Failed.Conflict`, `Failed.OSProvisioningTimedOut` | More granular than `resultType`. |
| `resourceId` | `/SUBSCRIPTIONS/<sub>/RESOURCEGROUPS/RG-TC-GECKO-T-WIN11-64-25H2/PROVIDERS/MICROSOFT.COMPUTE/VIRTUALMACHINES/VM-A2NWLRI4Q3MTZETCJNFAQAGK2HWSTSQGNO1` | Use `rex` to extract sub / rg / vm. |

## Common operation names

Compute / VM lifecycle:
- `MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE` — create or update VM.
- `MICROSOFT.COMPUTE/VIRTUALMACHINES/DELETE` — terminate VM.
- `MICROSOFT.COMPUTE/VIRTUALMACHINES/START/ACTION`
- `MICROSOFT.COMPUTE/VIRTUALMACHINES/DEALLOCATE/ACTION`
- `MICROSOFT.COMPUTE/DISKS/WRITE`, `.../DELETE`

Network (NIC / IP attached at provisioning):
- `MICROSOFT.NETWORK/NETWORKINTERFACES/WRITE`, `.../DELETE`
- `MICROSOFT.NETWORK/PUBLICIPADDRESSES/WRITE`

## Resource-group conventions for Firefox CI

One RG per worker pool (post-migration, ≥ 2026-04-13):

```
RG-TC-GECKO-T-WIN11-64-25H2          # Win11 25H2 cloud test pool
RG-TC-GECKO-T-WIN11-64-24H2          # Win11 24H2 cloud test pool
RG-TC-GECKO-T-WIN11-64-25H2-GPU      # GPU variant
RG-TC-GECKO-T-WIN11-64-25H2-LARGE
RG-TC-GECKO-T-WIN11-64-25H2-SOURCE
RG-TC-GECKO-T-WIN11-64-25H2-WEBGPU
RG-TC-GECKO-A64-WIN11-64-25H2        # ARM64 25H2
```

Pre-migration (March 2026 and earlier) workers landed in the aggregate RG:
- `RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION` (and a similar `RG-TC-ENG-...`).

That naming change matters when comparing pre/post cost surges — pull both
sets of RG patterns and add them together.

## Extracting structure from `resourceId`

`resourceId` is the canonical join key. The two extractions used everywhere:

```spl
| rex field=resourceId "(?i)resourcegroups/(?<rg>[^/]+)"
| rex field=resourceId "(?i)virtualmachines/(?<vm>vm-[a-z0-9]+)"
| rex field=resourceId "(?i)subscriptions/(?<sub>[^/]+)"
```

VMs created by worker-manager are named `vm-<base32-ish hash>` — matching
`vm-[a-z0-9]+` (case-insensitive) pulls them cleanly.

## Time format

Splunk accepts both relative and absolute time:
- Relative: `earliest=-1h`, `earliest=-7d@d`
- Absolute: `earliest="04/16/2026:00:50:00" latest="04/16/2026:01:30:00"` —
  format is `MM/DD/YYYY:HH:MM:SS`, **always quoted**.

## Quirks worth knowing

- `resultType=Start` (bare) sometimes produces zero results in `stats by` even
  when the events exist. Always use `resultType="Start"` with quotes.
- `tstats` is dramatically faster than `stats` for cardinality counts over
  long windows: `| tstats count where index=azure_audit by _time span=1d`.
  But `tstats` cannot use `rex`-extracted fields, so it's only useful for
  index-time fields.
- A single VM provisioning generates ~5-15 audit events (NIC, disk, VM write,
  start, etc.). Filter on `operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE"`
  with `resultType="Start"` to count one event per provisioning attempt.
