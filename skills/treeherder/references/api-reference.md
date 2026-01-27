# Treeherder REST API Reference

This document describes the Treeherder REST API endpoints used by the skill.

## Base URL

```
https://treeherder.mozilla.org/api/
```

## Authentication

Most endpoints are read-only and require no authentication. A custom User-Agent header is required for all requests.

## Endpoints

### Push Endpoints

#### List Pushes
```
GET /api/project/{repo}/push/
```

Query parameters:
- `count` - Number of results (default: 10)
- `author` - Filter by author email
- `revision` - Filter by revision hash
- `id` - Filter by push ID

Response:
```json
{
  "meta": {"count": 10, "repository": "autoland"},
  "results": [
    {
      "id": 1816157,
      "revision": "069b4737e402...",
      "author": "user@mozilla.com",
      "push_timestamp": 1769540665,
      "revisions": [...]
    }
  ]
}
```

#### Push Health
```
GET /api/project/{repo}/push/health/
```

Query parameters:
- `revision` - Revision hash (required)

Response includes:
- Overall result (pass/fail/indeterminate)
- Metrics for tests, builds, linting
- Jobs needing investigation

#### Push Health Summary
```
GET /api/project/{repo}/push/health_summary/
```

Query parameters:
- `revision` - Revision hash (required)

Lightweight summary of push health status.

### Job Endpoints

#### List Jobs
```
GET /api/project/{repo}/jobs/
```

Query parameters:
- `push_id` - Filter by push ID
- `result` - Filter by result (success, testfailed, busted, etc.)
- `tier` - Filter by tier (1, 2, 3)
- `failure_classification_id` - Filter by classification
- `count` - Number of results

Response:
```json
{
  "results": [
    {
      "id": 545710769,
      "job_type_name": "test-linux2404-64/debug-reftest-swr-6",
      "result": "success",
      "state": "completed",
      "platform": "linux2404-64",
      "tier": 1,
      "task_id": "XNdFrwh1SkKp9Xtu6yx0HA",
      "failure_classification_id": 1
    }
  ]
}
```

#### Job Log URLs
```
GET /api/project/{repo}/job-log-url/
```

Query parameters:
- `job_id` - Job ID
- `job_guid` - Job GUID

Returns URLs for job logs (live_backing_log, errorsummary_json, etc.)

#### Bug Suggestions
```
GET /api/project/{repo}/jobs/{job_id}/bug_suggestions/
```

Returns suggested bugs for error lines in a failed job:
```json
[
  {
    "search": "ERROR: AddressSanitizer: SEGV...",
    "line_number": 2417,
    "failure_new_in_rev": true,
    "bugs": {
      "open_recent": [...],
      "all_others": [...]
    }
  }
]
```

#### Text Log Errors
```
GET /api/project/{repo}/jobs/{job_id}/text_log_errors/
```

Returns parsed error lines from job log:
```json
[
  {
    "id": 55592483,
    "line": "ERROR - ==1402==ERROR: AddressSanitizer: SEGV...",
    "line_number": 2417,
    "new_failure": true,
    "job": 545634438
  }
]
```

#### Job Notes
```
GET /api/project/{repo}/note/
```

Query parameters:
- `job_id` - Job ID

Returns classification notes for a job:
```json
[
  {
    "id": 1705131,
    "job_id": 545634438,
    "failure_classification_id": 3,
    "created": "2026-01-27T13:02:34.587278",
    "who": "sheriff@mozilla.com",
    "text": ""
  }
]
```

### Reference Data Endpoints

#### Repositories
```
GET /api/repository/
```

Returns list of all Treeherder repositories with metadata.

#### Failure Classifications
```
GET /api/failureclassification/
```

Returns list of failure classification types:
```json
[
  {"id": 1, "name": "not classified"},
  {"id": 2, "name": "fixed by commit"},
  {"id": 3, "name": "expected fail"},
  {"id": 4, "name": "intermittent"},
  {"id": 5, "name": "infra"},
  {"id": 6, "name": "new failure not classified"},
  {"id": 7, "name": "autoclassified intermittent"},
  {"id": 8, "name": "intermittent needs bugid"}
]
```

#### Machine Platforms
```
GET /api/machineplatforms/
```

Returns list of available machine platforms with OS info.

### Performance Endpoints

#### Performance Frameworks
```
GET /api/performance/framework/
```

Returns list of performance testing frameworks:
```json
[
  {"id": 1, "name": "talos"},
  {"id": 4, "name": "awsy"},
  {"id": 10, "name": "raptor"},
  {"id": 13, "name": "browsertime"}
]
```

#### Performance Alert Summaries
```
GET /api/performance/alertsummary/
```

Query parameters:
- `framework` - Framework ID
- `repository` - Repository name
- `status` - Alert status (0-8)
- `limit` - Number of results

Status values:
- 0: untriaged
- 1: downstream
- 2: reassigned
- 3: invalid
- 4: acknowledged
- 5: investigating
- 6: wontfix
- 7: fixed
- 8: backedout

## Python Client

The `treeherder-client` library provides a Python interface:

```python
from thclient import TreeherderClient

client = TreeherderClient()

# Get pushes
pushes = client.get_pushes('autoland', count=10)

# Get jobs
jobs = client.get_jobs('autoland', push_id=1816157)

# Get repositories
repos = client.get_repositories()

# Get failure classifications
classifications = client.get_failure_classifications()
```

## Rate Limiting

The API has rate limiting. For bulk operations, add delays between requests.

## External Documentation

- [Treeherder ReadTheDocs](https://treeherder.readthedocs.io/)
- [treeherder-client on PyPI](https://pypi.org/project/treeherder-client/)
- [Treeherder Source Code](https://github.com/mozilla/treeherder)
