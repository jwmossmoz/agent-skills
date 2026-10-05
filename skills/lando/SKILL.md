---
name: lando
description: >
  Use when checking a Mozilla Lando landing job after submission to report its
  current state, landed commit, failure reason, or cancellation from the public
  read-only API.
metadata:
  version: "1.3"
---

# Lando

Poll the public landing-job endpoint after you submit a try push or commit
through Lando.

## Prerequisites

The read-only API does not need authentication. Use `curl` and `jq`.

## Usage

```bash
curl -fsS "https://lando.moz.tools/landing_jobs/<JOB_ID>/" \
  | jq '{status, commit_id, error, updated_at}'
```

Poll at a moderate interval until `status` is `LANDED`, `FAILED`, or
`CANCELLED`. Report `commit_id` for a landed job and `error` for a failed job.

## Gotchas

- Status values are uppercase.
- The landed commit field is `commit_id`, not `landed_commit_id`.
- A job can end as `CANCELLED` as well as `FAILED` or `LANDED`.
- Use `lando.moz.tools` (instance `lando-prod-2025`, the `landoInstance` in the
  Treeherder URL that `mach try` prints). The old
  `api.lando.services.mozilla.com` host is a different instance whose job IDs
  overlap, so it returns unrelated jobs instead of an error.
- Keep the trailing slash. Without it the endpoint returns a 301 redirect.

## References

- [Lando source](https://github.com/mozilla-conduit/lando)
- [Mozilla Conduit documentation](https://moz-conduit.readthedocs.io/)
