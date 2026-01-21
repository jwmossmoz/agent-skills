# Bugzilla REST API Reference

Base URL: `https://bugzilla.mozilla.org/rest/`

Full documentation: https://bmo.readthedocs.io/en/latest/api/

## Authentication

Use the `X-BUGZILLA-API-KEY` header with your API key.

Generate an API key at: https://bugzilla.mozilla.org/userprefs.cgi?tab=apikey

## Common Endpoints

### Bugs

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get bug | GET | `/rest/bug/{id}` |
| Search bugs | GET | `/rest/bug?{params}` |
| Create bug | POST | `/rest/bug` |
| Update bug | PUT | `/rest/bug/{id}` |

### Comments

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get comments | GET | `/rest/bug/{id}/comment` |
| Add comment | POST | `/rest/bug/{id}/comment` |

### Attachments

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get attachments | GET | `/rest/bug/{id}/attachment` |
| Add attachment | POST | `/rest/bug/{id}/attachment` |
| Get attachment | GET | `/rest/bug/attachment/{attachment_id}` |

### Other

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Who am I | GET | `/rest/whoami` |
| Get products | GET | `/rest/product/{name}` |
| Bug history | GET | `/rest/bug/{id}/history` |

## Search Parameters

Common search parameters for `GET /rest/bug`:

- `product` - Product name
- `component` - Component name
- `status` - Bug status (NEW, ASSIGNED, RESOLVED, VERIFIED, CLOSED)
- `resolution` - Resolution (FIXED, INVALID, WONTFIX, DUPLICATE, WORKSFORME, INCOMPLETE)
- `assigned_to` - Assignee email
- `reporter` - Reporter email
- `priority` - P1, P2, P3, P4, P5, --
- `severity` - blocker, critical, major, normal, minor, trivial, enhancement
- `keywords` - Keyword search
- `status_whiteboard` - Whiteboard contains
- `summary` - Summary contains
- `creation_time` - Created after (YYYY-MM-DD)
- `last_change_time` - Changed after (YYYY-MM-DD)
- `quicksearch` - Quick search text
- `limit` - Max results

## Bug Fields

Standard bug fields:

- `id` - Bug ID
- `summary` - Bug summary/title
- `status` - Current status
- `resolution` - Resolution (if resolved)
- `product` - Product name
- `component` - Component name
- `version` - Product version
- `priority` - Priority level
- `severity` - Severity level
- `assigned_to` - Assignee email
- `creator` - Reporter email
- `creation_time` - When created
- `last_change_time` - When last modified
- `keywords` - List of keywords
- `depends_on` - Bug IDs this depends on
- `blocks` - Bug IDs this blocks
- `see_also` - Related URLs
- `cc` - CC list emails
- `whiteboard` - Status whiteboard text

## Create Bug Required Fields

- `product` - Product name
- `component` - Component name
- `summary` - Bug summary
- `version` - Product version

## Update Bug Fields

All fields are optional. For array fields (cc, keywords, blocks, depends_on), use add/remove syntax:

```json
{
  "cc": {"add": ["user@example.com"]},
  "keywords": {"remove": ["keyword1"]}
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 100 | Invalid bug ID |
| 101 | Bug does not exist |
| 102 | Access denied |
| 104 | Invalid field value |
| 51 | Invalid parameter |

## Rate Limits

BMO does not publish specific rate limits but requests should be reasonable. Avoid:
- Rapid-fire requests
- Bulk operations without delays
- Polling at high frequency
