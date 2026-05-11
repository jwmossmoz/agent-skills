---
name: lando
description: >
  Poll Mozilla's public Lando API to check the status of a landing job
  (submitted, in_progress, landed, failed) and surface the landed commit
  hash or failure reason. Use after submitting a try push or commit
  through Lando to verify whether it landed.
metadata:
  version: "1.0"
---

# Lando

Check the status of Mozilla Lando landing jobs using the public API.

## Usage

```bash
# Check landing job status
curl -s "https://lando.services.mozilla.com/api/v1/landing_jobs/<JOB_ID>" | jq

# Example
curl -s "https://lando.services.mozilla.com/api/v1/landing_jobs/173397" | jq

# Check only the status field
curl -s "https://lando.services.mozilla.com/api/v1/landing_jobs/173397" | jq -r '.status'

# Poll every 90 seconds until landed or failed
JOB_ID=173397
while true; do
  STATUS=$(curl -s "https://lando.services.mozilla.com/api/v1/landing_jobs/$JOB_ID" | jq -r '.status')
  echo "$(date): $STATUS"
  [[ "$STATUS" == "landed" || "$STATUS" == "failed" ]] && break
  sleep 90
done
```

## API Response

The API returns a JSON object with these key fields:

| Field | Description |
|-------|-------------|
| `status` | Job status: `submitted`, `in_progress`, `landed`, `failed` |
| `error` | Error message if status is `failed` |
| `landed_commit_id` | Commit hash if successfully landed |
| `created_at` | When the job was submitted |
| `updated_at` | Last status update time |

## Common Statuses

- `submitted` - Job is queued
- `in_progress` - Currently being processed
- `landed` - Successfully landed to the repository
- `failed` - Landing failed (check `error` field)

## Prerequisites

None - the API is publicly accessible. No authentication required for read operations.

## Gotchas

- The API is read-only and unauthenticated — no token plumbing needed for status polls.
- `status` values are lowercase (`landed`, not `Landed`). Match exactly when comparing.
- Failed jobs put the reason in `error`, not `status`. Always check both fields when reporting back to the user.
- The polling loop in this doc uses 90s; pick longer intervals for batched dashboards — Lando state doesn't change often.

## Documentation

- **Lando Service**: https://lando.services.mozilla.com/
- **API Base**: https://lando.services.mozilla.com/api/v1/
- **Mozilla Conduit Documentation**: https://moz-conduit.readthedocs.io/
- **Source Code**: https://github.com/mozilla-conduit/lando-api
