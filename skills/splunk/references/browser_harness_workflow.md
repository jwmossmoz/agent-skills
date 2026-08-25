# Splunk Web auth via browser-harness

How and why this skill drives Splunk through Chrome instead of `splunk-sdk`.

Upstream agent guide:
<https://github.com/browser-use/browser-harness/blob/main/AGENTS.md> — the
canonical reference for AI agents using the harness. If `js()`, `list_tabs()`,
or `switch_tab()` semantics drift, check AGENTS.md first.

## Why this is necessary

Mozilla's Splunk Cloud (`security-mozilla.splunkcloud.com`) has the management
port (8089) closed off externally. The classic SDK paths fail:

- `splunk-sdk-python` → connects to `:8089`, times out.
- `curl -H "Authorization: Bearer …" https://host:8089/...` → same.
- `curl -H "Authorization: Bearer …" https://host/services/...` → 401, the
  443 endpoint only honors **session cookies**, not bearer tokens.

What does work: the same endpoints the Splunk Web UI calls, hit from a tab
that's already SSO-authenticated.

## The endpoints

Splunk Web exposes the management API under the `__raw` mount. From an
authenticated tab on `security-mozilla.splunkcloud.com`:

| Action | Method | Path | Notes |
|---|---|---|---|
| Submit search | POST | `/en-US/splunkd/__raw/services/search/jobs` | Body: `search=<spl>&output_mode=json`. 201 + `{sid}` on success. |
| Job status | GET | `/en-US/splunkd/__raw/services/search/jobs/<sid>?output_mode=json` | `entry[0].content.dispatchState` is `QUEUED` / `RUNNING` / `DONE` / `FAILED`. |
| Results | GET | `/en-US/splunkd/__raw/services/search/jobs/<sid>/results?output_mode=json&count=N&offset=O` | Paged. Max 5000 rows per call observed; loop until `< pageSize`. |
| Indexes (probe) | GET | `/en-US/splunkd/__raw/services/data/indexes?output_mode=json&count=3` | Cheap auth probe. |

## Auth headers — what's required

Two pieces of state come from the user's logged-in tab:

1. **Session cookies** — sent automatically by `fetch(..., {credentials: "include"})`.
2. **CSRF token** — Splunk requires it on POSTs. It's stored in a cookie named
   `splunkweb_csrf_token_<port>` (e.g. `splunkweb_csrf_token_8443`) and must
   be echoed in the `X-Splunk-Form-Key` header. The `<port>` suffix varies,
   so use a `startsWith` lookup:

```js
const csrfCookie = document.cookie.split(";").map(c => c.trim())
  .find(c => c.startsWith("splunkweb_csrf_token_"));
const csrf = csrfCookie.split("=")[1];
```

Also include `X-Requested-With: XMLHttpRequest` — Splunk treats it as the
"this is a UI call" marker.

## The submit/poll/page flow

```
POST /services/search/jobs                  → 201 {sid}
GET  /services/search/jobs/<sid>            → poll until dispatchState=DONE
GET  /services/search/jobs/<sid>/results    → page count=5000 offset=N until < 5000
```

Search dispatch is async — even a small `| stats count` query takes a few
seconds to reach `DONE`. Poll every ~2s with a generous budget (10 min for
heavy queries — searches auto-expire after their lifetime, default 10 min).

## browser-harness wiring

Only three harness primitives are needed:

- `list_tabs()` — find the Splunk tab by URL substring `splunkcloud`.
- `switch_tab(target_id)` — make it the active CDP target.
- `js(code)` — run an async IIFE in that tab and get its return value.

The canonical recipe below puts all of this in one `browser-harness -c '...'`
block. Change only the `SPL` value for a normal query.

```bash
browser-harness -c '
import json

SPL = """search index=azure_audit "<RESOURCE_GROUP_OR_VM>" earliest=-2h latest=now
| table time operationName resultType resultSignature resourceId"""

tabs = list_tabs()
splunk_tab = next((t for t in tabs if "splunkcloud" in t.get("url", "")), None)
assert splunk_tab, "open Splunk Cloud in Chrome and sign in first"
switch_tab(splunk_tab["targetId"])

code = """
(async () => {
  const cookie = document.cookie.split(";").map(c => c.trim())
    .find(c => c.startsWith("splunkweb_csrf_token_"));
  if (!cookie) return JSON.stringify({error: "missing CSRF cookie"});
  const csrf = cookie.split("=")[1];
  const body = new URLSearchParams({search: %s, output_mode: "json", max_count: "0"});
  const submitted = await fetch(
    "/en-US/splunkd/__raw/services/search/jobs",
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Splunk-Form-Key": csrf,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: body.toString(),
    }
  );
  if (submitted.status !== 201) {
    return JSON.stringify({error: "submit failed", status: submitted.status});
  }
  const {sid} = await submitted.json();
  let done = false;
  for (let i = 0; i < 300; i++) {
    const status = await (await fetch(
      "/en-US/splunkd/__raw/services/search/jobs/" + sid + "?output_mode=json",
      {credentials: "include"}
    )).json();
    const state = status.entry?.[0]?.content?.dispatchState;
    if (state === "DONE") { done = true; break; }
    if (state === "FAILED") return JSON.stringify({error: "search failed", sid});
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  if (!done) return JSON.stringify({error: "search timed out", sid});

  let results = [];
  for (let offset = 0; ; offset += 5000) {
    const page = await (await fetch(
      "/en-US/splunkd/__raw/services/search/jobs/" + sid +
      "/results?output_mode=json&count=5000&offset=" + offset,
      {credentials: "include"}
    )).json();
    const rows = page.results || [];
    results = results.concat(rows);
    if (rows.length < 5000) break;
  }
  return JSON.stringify({sid, count: results.length, results});
})()
""" % json.dumps(SPL)

print(json.dumps(json.loads(js(code)), indent=2))
'
```

## Concurrency

The harness shares **one** Chrome session. Two parallel queries will fight
over the active tab and corrupt CSRF state. Two safe options:

1. Sequence calls in the shell (one `browser-harness -c` after another).
2. Loop **inside** a single `browser-harness -c "..."` block — the Python
   running there can issue `js()` calls in series, e.g. fetch results
   per-day for 60 days in one invocation. See `query_examples.md` for
   a per-day batch loop.

## Failure modes and what they mean

| Symptom | Likely cause |
|---|---|
| `error: "no Splunk tab open"` | User isn't logged in / tab closed. Open the URL and sign in via SSO. |
| `submit failed status: 403` | CSRF cookie missing or stale — refresh the Splunk tab. |
| `submit failed status: 401` | SSO session expired — re-login. |
| `error: "search failed"` | Bad SPL syntax (most common: unquoted special chars in earliest/latest). |
| `wait timeout, state: RUNNING` | Query is heavier than the poll budget; bump the loop count or simplify the SPL. |
| Empty `results` but no error | Search ran but matched nothing — verify the time window with a broader probe. |
