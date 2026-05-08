---
name: splunk
description: >
  Query Mozilla Splunk Cloud for Azure activity logs (VM lifecycle,
  NIC/disk writes, deletes, OSProvisioningTimedOut) on Taskcluster worker
  pools — driving Splunk Web through `browser-harness` against an
  authenticated Chrome tab because the REST API is disabled at Mozilla.
  Use for VM-side provisioning failures and worker lifespan on
  `index=azure_audit`. DO NOT USE FOR in-VM logs (use papertrail) or
  worker-manager service decisions (use tc-logview).
---

# Splunk

Query Mozilla's Splunk Cloud (`security-mozilla.splunkcloud.com`) for Azure
activity logs covering Taskcluster worker VM lifecycle.

## Auth model: Splunk REST API is disabled

Mozilla's Splunk Cloud has port 8089 / token auth turned off, so `splunk-sdk`
and curl-with-bearer-token both fail. This skill instead drives **Splunk Web**
via `browser-harness`: it fetches `/en-US/splunkd/__raw/services/search/jobs`
from the user's already-authenticated Chrome tab, using the
`splunkweb_csrf_token_*` cookie + `X-Splunk-Form-Key` header.

> Prerequisite: the user must have **`https://security-mozilla.splunkcloud.com`
> open in Chrome and signed in via SSO**. The skill auto-switches to that tab.

`browser-harness` is the upstream tool. The canonical guide for AI agents is
**<https://github.com/browser-use/browser-harness/blob/main/AGENTS.md>** —
read that for the current helper API (`js`, `list_tabs`, `switch_tab`, etc.),
invocation patterns, and gotchas. Locally it's installed as `browser-harness`
on PATH.

## Usage pattern

Inline the SPL into a `browser-harness -c "..."` invocation. The block
below is the canonical recipe — copy, change the SPL line, run.

```bash
browser-harness -c '
import json, time

SPL = """search index=azure_audit "RG-TC-GECKO-T-WIN11-64-25H2"
earliest="04/16/2026:00:50:00" latest="04/16/2026:01:30:00"
| stats count by operationName resultType resultSignature"""

# 1. Switch to the Splunk tab (must already be open + signed in).
tabs = list_tabs()
st = next((t for t in tabs if "splunkcloud" in t.get("url", "")), None)
assert st, "open https://security-mozilla.splunkcloud.com in Chrome and sign in first"
switch_tab(st["targetId"])

# 2. Submit the search, poll until DONE, page through results.
JS = """
(async () => {
  const csrf = document.cookie.split(";").map(c=>c.trim())
    .find(c=>c.startsWith("splunkweb_csrf_token_")).split("=")[1];
  const body = new URLSearchParams({search: %s, output_mode: "json", max_count: "0"});
  const r = await fetch("/en-US/splunkd/__raw/services/search/jobs", {
    method: "POST", credentials: "include",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Splunk-Form-Key": csrf, "X-Requested-With": "XMLHttpRequest",
    },
    body: body.toString(),
  });
  if (r.status !== 201) return JSON.stringify({error:"submit", status:r.status});
  const {sid} = await r.json();
  for (let i = 0; i < 300; i++) {                    // ~10 min poll budget
    const sj = await (await fetch(
      "/en-US/splunkd/__raw/services/search/jobs/"+sid+"?output_mode=json",
      {credentials:"include"})).json();
    const c = (sj.entry?.[0]?.content) || {};
    if (c.dispatchState === "DONE") break;
    if (c.dispatchState === "FAILED") return JSON.stringify({error:"failed", sid});
    await new Promise(rs => setTimeout(rs, 2000));
  }
  let out = [], offset = 0;
  while (true) {                                      // page in 5000-row chunks
    const j = await (await fetch(
      "/en-US/splunkd/__raw/services/search/jobs/"+sid+
      "/results?output_mode=json&count=5000&offset="+offset,
      {credentials:"include"})).json();
    const rows = j.results || [];
    out = out.concat(rows);
    if (rows.length < 5000) break;
    offset += 5000;
  }
  return JSON.stringify({sid, count: out.length, results: out});
})()
""" % json.dumps(SPL)

result = json.loads(js(JS))
print(json.dumps(result, indent=2)[:3000])
'
```

To save full results to a file instead of printing, replace the last line with:

```python
open("/tmp/spl.json", "w").write(json.dumps(result))
print(f"saved /tmp/spl.json: count={result.get('count', 0)} error={result.get('error')}")
```

## Probe (sanity check)

Before a real query, verify the tab is open and CSRF round-trips:

```bash
browser-harness -c '
import json
tabs = list_tabs()
st = next((t for t in tabs if "splunkcloud" in t.get("url","")), None)
assert st, "no Splunk tab open"
switch_tab(st["targetId"])
print(js("""
(async () => {
  const csrf = document.cookie.split(";").map(c=>c.trim())
    .find(c=>c.startsWith("splunkweb_csrf_token_"));
  const r = await fetch("/en-US/splunkd/__raw/services/data/indexes?count=3&output_mode=json",
    {credentials:"include"});
  return JSON.stringify({csrf: !!csrf, status: r.status});
})()
"""))'
# Expect: {"csrf":true,"status":200}
```

## Scope vs. other log tools

| Tool | Scope | Source |
|---|---|---|
| **splunk** (this skill) | **Azure activity log** — control-plane events for VMs/disks/NICs (writes, deletes, failures with `resultType`/`resultSignature`). ~60 days retention. | Azure → Splunk forwarder, `index=azure_audit` |
| `tc-logview` | Taskcluster's view of provisioning: `worker-requested`, `worker-running`, `worker-removed`, `worker-error`, `scan-seen`. | worker-manager + worker-scanner GCP logs |
| `papertrail` (skill) | In-VM events forwarded from the running Windows worker. | SolarWinds Observability |
| `taskcluster` (skill) | Live task logs, artifacts, retriggers — not VM lifecycle. | Taskcluster API |

For provisioning regressions, query at least **two** of these — they corroborate
or contradict each other. Splunk tells you what Azure did to the VM; tc-logview
tells you what worker-manager asked Azure to do.

## Primary index and key fields

- **`index=azure_audit`** — the only index this skill cares about.
- `operationName` — e.g. `MICROSOFT.COMPUTE/VIRTUALMACHINES/WRITE`,
  `MICROSOFT.COMPUTE/VIRTUALMACHINES/DELETE`,
  `MICROSOFT.NETWORK/NETWORKINTERFACES/WRITE`.
- `resultType` — `Start`, `Success`, `Failure`. **Note**: filter on
  ``resultType="Start"`` (quoted) — bare `resultType=Start` sometimes returns
  zero matches.
- `resultSignature` — granular outcome, e.g. `Started`, `Accepted.Created`,
  `Failed.Conflict`, `Failed.OSProvisioningTimedOut`.
- `resourceId` — full ARM ID. Use `rex` to extract:
  ```spl
  | rex field=resourceId "(?i)resourcegroups/(?<rg>[^/]+)"
  | rex field=resourceId "(?i)virtualmachines/(?<vm>vm-[a-z0-9]+)"
  ```
- Resource group naming: `RG-TC-GECKO-T-WIN11-64-25H2`,
  `RG-TC-GECKO-T-WIN11-64-24H2`, etc. — one RG per worker pool.
  Pre-migration pools used the aggregate `RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION`.

See `references/azure_log_format.md` for the full field map and
`references/query_examples.md` for SPL recipes used in real investigations.

## Workflow: investigate VM-side provisioning failures

1. Open Splunk in Chrome (`https://security-mozilla.splunkcloud.com`) and
   sign in. Run the probe above to confirm.
2. Find the failure window from `tc-logview` (`worker-error` events) or
   Treeherder. Pin a tight window — Splunk slows down on multi-day searches.
3. Pull the Azure-side resultSignatures for that window/RG using the canonical
   recipe (replace `SPL`):
   ```
   search index=azure_audit "RG-TC-GECKO-T-WIN11-64-25H2"
     earliest="04/16/2026:00:50:00" latest="04/16/2026:01:30:00"
     resultType=Failure
   | stats count by operationName resultType resultSignature
   ```
4. Trace one VM end-to-end:
   ```
   search index=azure_audit "VM-A2NWLRI4Q3MTZETCJNFAQAGK2HWSTSQGNO1"
     earliest=-2d latest=now
   | sort _time | table _time operationName resultType resultSignature
   ```
5. If you find `Failed.OSProvisioningTimedOut`, that's the bootstrap script
   not finishing in Azure's window — pivot to **papertrail** for in-VM logs
   on that worker ID.

## Caveats and gotchas

- **One Chrome session, one query at a time.** Don't run two `browser-harness`
  Splunk invocations in parallel — they fight over the active tab and CSRF
  state. Sequence them, or batch in a single Python loop inside one
  `browser-harness -c "..."` block.
- **Time format** in earliest/latest: `MM/DD/YYYY:HH:MM:SS`, e.g.
  `"04/02/2026:12:00:00"`. Relative forms (`-1h`, `-7d`) also work.
- **`resultType="Start"` is the create-attempt event**, not the success.
  Pair it with the corresponding `Success`/`Failure` event for outcomes.
- **`tstats` is much faster than `stats`** for high-cardinality counts over
  long windows: `| tstats count where index=azure_audit by _time span=1d`.
- **Search lifetime ≈ 10 minutes**: dispatched jobs auto-expire. The poll
  budget in the canonical recipe is 300 × 2s = 10 min. Bump it for heavy
  queries (e.g. multi-day `stats by vm`).
- **CSRF cookie is per-app**: the cookie name is
  `splunkweb_csrf_token_8443` (or similar suffix) — that's why the recipe
  uses a `startsWith` lookup instead of an exact name.

## Resources

- **Upstream agent guide**: <https://github.com/browser-use/browser-harness/blob/main/AGENTS.md>
  — canonical source for the harness API as it should be used by AI agents.
  If `js()`, `list_tabs()`, or `switch_tab()` semantics drift, check
  AGENTS.md before adapting this skill.
- `references/azure_log_format.md` — `index=azure_audit` field map and RG patterns.
- `references/query_examples.md` — SPL recipes from real investigations.
- `references/browser_harness_workflow.md` — auth mechanics + Splunk Web endpoints.
- `references/worker_lifecycle.md` — failure signatures (OSProvisioningTimedOut,
  spot eviction, conflict, etc.) and what to do next.
