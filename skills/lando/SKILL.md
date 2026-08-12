---
name: lando
description: >
  Poll Mozilla's public Lando API to check the status of a landing job
  (submitted, in_progress, landed, failed) and surface the landed commit
  hash or failure reason. Use when you need to verify a try push or
  commit after you submit it through Lando.
metadata:
  version: "1.1"
---

# Lando

Check the status of Mozilla Lando landing jobs using the public API.

## Usage

```bash
# Check landing job status
curl -fsS "https://api.lando.services.mozilla.com/landing_jobs/<JOB_ID>" | jq

# Example
curl -fsS "https://api.lando.services.mozilla.com/landing_jobs/173397" | jq

# Check only the status field
curl -fsS "https://api.lando.services.mozilla.com/landing_jobs/173397" | jq -r '.status'

# Poll every 90 seconds until landed or failed
JOB_ID=173397
while true; do
  STATUS=$(curl -fsS "https://api.lando.services.mozilla.com/landing_jobs/$JOB_ID" | jq -r '.status')
  echo "$(date): $STATUS"
  [[ "$STATUS" == "LANDED" || "$STATUS" == "FAILED" || "$STATUS" == "CANCELLED" ]] && break
  sleep 90
done
```

## API Response

The API returns a JSON object with these key fields:

| Field | Description |
|-------|-------------|
| `status` | Job status, such as `SUBMITTED`, `IN_PROGRESS`, `LANDED`, or `FAILED` |
| `error` | Error message if status is `FAILED` |
| `commit_id` | Commit hash if the job landed successfully |
| `created_at` | When the job was submitted |
| `updated_at` | Last status update time |

## Common Statuses

- `SUBMITTED` - Job is queued
- `IN_PROGRESS` - Job is being processed
- `LANDED` - Job landed successfully
- `FAILED` - Job failed (check the `error` field)
- `CANCELLED` - User cancelled the job

## Prerequisites

None - the API is publicly accessible. No authentication required for read operations.

## Gotchas

- The API is read-only and unauthenticated — no token plumbing needed for status polls.
- `status` values are uppercase (`LANDED`, not `landed`). Match them exactly.
- Failed jobs put the reason in `error`, not `status`. Always check both fields when reporting back to the user.
- The polling loop in this doc uses 90s; pick longer intervals for batched dashboards — Lando state doesn't change often.

## Documentation

- **Lando Service**: https://lando.services.mozilla.com/
- **Landing Job API example**: https://api.lando.services.mozilla.com/landing_jobs/173397
- **Mozilla Conduit Documentation**: https://moz-conduit.readthedocs.io/
- **Source Code**: https://github.com/mozilla-conduit/lando
