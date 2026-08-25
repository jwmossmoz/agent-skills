---
name: splunk
description: >
  Use when querying Mozilla Splunk Cloud Azure activity logs for Taskcluster VM,
  disk, and NIC lifecycle or provisioning failures. DO NOT USE FOR in-VM or
  worker-manager logs.
metadata:
  version: "1.1"
---

# Splunk

Query `index=azure_audit` through an authenticated Splunk Web tab. SDK and
bearer-token calls do not work.

## Scope

| Tool | Use it for |
|---|---|
| **splunk** | Azure VM, disk, NIC, write, delete, and provisioning outcomes |
| **taskcluster-worker-lifecycle-logs** | Worker-manager requests, registration, removal, errors, and scanner events |
| **papertrail** | Logs from inside a worker that started |
| **taskcluster** | Task logs, artifacts, state, and retriggers |

## Prerequisites

Open <https://security-mozilla.splunkcloud.com> in Chrome and sign in with SSO.
Install `browser-harness`.

## Usage

1. Get a narrow UTC window and resource group or worker ID.
2. Build the SPL with examples from
   [query_examples.md](references/query_examples.md).
3. Run the submit, poll, and page recipe in
   [browser_harness_workflow.md](references/browser_harness_workflow.md).
4. Use raw Azure `time` for event order and compare a second log source.

Start with a bounded query:

```spl
search index=azure_audit "<RESOURCE_GROUP_OR_VM>" earliest=-2h latest=now
| table time operationName resultType resultSignature resourceId
```

## Gotchas

- Run one browser-harness query at a time. Calls share one Chrome session.
- Quote `resultType="Start"`; an unquoted value can return no matches.
- A `Start` event is an attempt. Pair it with its `Success` or `Failure` event.
- Splunk `_time` can lag the raw Azure `time` field by several minutes.
- Use a tight time range. Dispatched jobs expire and broad searches are slow.

## References

- [azure_log_format.md](references/azure_log_format.md): fields and resource groups
- [worker_lifecycle.md](references/worker_lifecycle.md): Azure failure signatures
