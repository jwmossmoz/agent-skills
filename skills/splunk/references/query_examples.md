# SPL recipes for Azure VM-lifecycle investigations

Real queries that worked against `index=azure_audit`. Drop the `SPL` value
from `SKILL.md`'s canonical recipe with one of these and run.

All time ranges are absolute (`MM/DD/YYYY:HH:MM:SS`). Bump the JS poll budget
(`for (let i = 0; i < 300; ...)`) for queries that span multi-day windows.

## Failure breakdown for a window

```spl
search index=azure_audit "RG-TC-GECKO-T-WIN11-64-25H2"
  earliest="04/16/2026:00:50:00" latest="04/16/2026:01:30:00"
  resultType=Failure
| stats count by operationName resultType resultSignature
```

Useful first cut. Group by `resultSignature` to see which Azure-side reason
(`Failed.Conflict`, `Failed.OSProvisioningTimedOut`, etc.) dominates.

## VM lifespan distribution (create → delete)

Buckets every VM in a window by how long it lived. Indicates whether a pool
is healthily ephemeral or has VMs getting stuck.

```spl
search index=azure_audit "RG-TC-GECKO-T-WIN11-64-25H2"
  earliest="04/20/2026:00:00:00" latest="04/22/2026:00:00:00"
  (operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE"
   OR operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/DELETE")
  resultType="Start"
| rex field=resourceId "(?i)virtualmachines/(?<vm>vm-[a-z0-9]+)"
| rex field=resourceId "(?i)resourcegroups/(?<rg>[^/]+)"
| search rg="RG-TC-GECKO-T-WIN11-64-25H2"
| stats earliest(_time) AS t_first latest(_time) AS t_last
        values(operationName) AS ops by vm
| where mvcount(ops) >= 2
| eval lifespan = t_last - t_first
| eval bucket = case(
    lifespan < 600,  "00_0-10min",
    lifespan < 1800, "01_10-30min",
    lifespan < 3600, "02_30-60min",
    lifespan < 7200, "03_1-2hr",
    lifespan < 14400,"04_2-4hr",
    lifespan < 28800,"05_4-8hr",
    true(),          "06_8hr+")
| stats count by bucket
| sort bucket
```

Pair with the same query against the comparison pool (`-WIN11-64-24H2`) to
see if a regression is pool-specific.

## Find stuck VMs (lifespan > 4 hours)

```spl
search index=azure_audit "RG-TC-GECKO-T-WIN11-64-25H2"
  earliest="04/20/2026:00:00:00" latest="04/22/2026:00:00:00"
  (operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE"
   OR operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/DELETE")
  resultType="Start"
| rex field=resourceId "(?i)virtualmachines/(?<vm>vm-[a-z0-9]+)"
| stats earliest(_time) AS t_first latest(_time) AS t_last
        values(operationName) AS ops by vm
| where mvcount(ops) >= 2
| eval lifespan = t_last - t_first
| where lifespan > 14400
| head 10
| table vm t_first t_last lifespan
```

Then trace each `vm-*` end-to-end (next recipe).

## Trace one VM end-to-end

```spl
search index=azure_audit "VM-A2NWLRI4Q3MTZETCJNFAQAGK2HWSTSQGNO1"
  earliest="04/19/2026:00:00:00" latest="04/22/2026:00:00:00"
| sort _time
| table _time operationName resultType resultSignature
```

Note: VM names match case-insensitively. The example above is the upper-case
form Splunk indexes; the harness query string can use either case.

## Count specific failure signatures

```spl
search index=azure_audit "RG-TC-GECKO-T-WIN11-64-25H2"
  "OSProvisioningTimedOut"
  earliest="04/13/2026:00:00:00" latest="05/01/2026:00:00:00"
| rex field=resourceId "(?i)resourcegroups/(?<rg>[^/]+)"
| search rg="RG-TC-GECKO-T-WIN11-64-25H2"
| stats count
```

Run the same query against `-24H2` to compare.

## Per-day VM-create totals (cost-surge analysis)

```spl
search index=azure_audit operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE"
  resultType="Start" "RG-TC-GECKO"
  earliest="04/15/2026:00:00:00" latest="04/16/2026:00:00:00"
| rex field=resourceId "RESOURCEGROUPS/(?<rg>[^/]+)"
| stats count by rg
```

Loop this in Python inside one `browser-harness -c "..."` block to get a
per-day series for 30-60 days. Sequencing inside one harness invocation
avoids the multi-process tab fight.

## Resource-group inventory (which RGs exist)

```spl
search index=azure_audit operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE"
  resultType="Start"
  earliest="04/01/2026:12:00:00" latest="04/01/2026:12:10:00"
| rex field=resourceId "SUBSCRIPTIONS/(?<sub>[^/]+)/RESOURCEGROUPS/(?<rg>[^/]+)"
| stats count by sub rg
```

Useful for spotting the migration window — pre-2026-04-13 events sit in
`RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION`, post-migration in
`RG-TC-GECKO-T-WIN11-64-*`.

## Sample one raw event (when discovering field shape)

```spl
search index=azure_audit
  operationName="MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE"
  resultType="Start"
  earliest="04/01/2026:12:00:00" latest="04/01/2026:12:01:00"
| head 1
```

In the result, inspect `result["_raw"]` (full event JSON) to find tag fields
or other indexed metadata not surfaced as named columns.

## Index-wide cardinality (cheap)

```spl
| tstats count where index=azure_audit by _time span=1d
```

`tstats` skips the search heads and answers in a few seconds even for 60-day
windows. Use this to verify retention and spot data gaps before launching
heavy `stats` queries.

## Tips

- **Filter early, group late.** Put the RG and time window first, the `stats`
  last. Splunk evaluates left to right.
- **Avoid `head N` before `stats`** — it caps input rows, not output rows,
  and gives misleading totals. `head` belongs at the very end.
- **`resultType="Start"` (quoted)** — the unquoted form silently misses rows
  in some `stats by` patterns. Always quote.
- **Don't rely on `head 1`** for "any event in this window" — Splunk may pick
  the most recent 1 row, which can be a `Failure` even if `Success` exists.
  Use `| stats count` instead.
- **VM names are case-flexible** in search terms but uppercase in
  `resourceId`. Use `(?i)` in `rex` patterns.
