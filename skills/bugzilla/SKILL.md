---
name: bugzilla
description: Interact with Mozilla Bugzilla (bugzilla.mozilla.org) via REST API. Use when the user asks to search bugs, view bug details, create bugs, update bugs, add comments, or attach files. Triggers on "bugzilla", "bmo", "file a bug", "bug report", "mozilla bug".
---

# Bugzilla CLI

Requires: `export BUGZILLA_API_KEY="your-key"` (get from https://bugzilla.mozilla.org/userprefs.cgi?tab=apikey)

Read-only ops work without auth.

## Usage

```bash
cd scripts && uv run bz.py <command> [options]
```

Run `uv run bz.py --help` or `uv run bz.py <command> --help` for full options.

## Commands

| Command | Purpose |
|---------|---------|
| `search` | Find bugs by product, component, status, assignee, etc. |
| `get` | View bug details, comments, history |
| `create` | File a new bug (requires: product, component, summary, version) |
| `update` | Modify status, assignee, priority, add comments |
| `comment` | Add comment to a bug |
| `attachment` | Attach files to a bug |
| `needinfo` | Request or clear needinfo flags |
| `products` | List products and components |
| `whoami` | Verify authentication |
| `create-image-regression` | File a bug for a confirmed image regression |

## Quick Examples

```bash
# Search
uv run bz.py search --quicksearch "crash" --limit 10
uv run bz.py search --product Firefox --status NEW,ASSIGNED --priority P1

# View
uv run bz.py get 1234567 -v --include-comments

# Update
uv run bz.py update 1234567 --status RESOLVED --resolution FIXED
uv run bz.py needinfo 1234567 --request user@mozilla.com

# Create
uv run bz.py create --product Firefox --component General --summary "Title" --version unspecified
```

## Image Regression Template

Create a pre-filled bug for confirmed image regressions:

```bash
# Basic usage
uv run bz.py create-image-regression \
  --image-version 1.0.9 \
  --worker-pool gecko-t/win11-64-24h2-alpha

# Full example with investigation details
uv run bz.py create-image-regression \
  --image-version 1.0.9 \
  --worker-pool gecko-t/win11-64-24h2-alpha \
  --windows-build 26100.7171 \
  --production-version 1.0.8 \
  --failing-tests "test_keycodes.xhtml,mochitest-browser-media" \
  --investigation-doc ~/moz_artifacts/win11-24h2-image-1.0.9-failure-investigation.md \
  --task-group U0vOaaW-T-i5nN79edugYA

# Dry run to preview
uv run bz.py create-image-regression \
  --image-version 1.0.9 \
  --worker-pool gecko-t/win11-64-24h2-alpha \
  --dry-run
```

### Default Fields

| Field | Default Value |
|-------|---------------|
| Product | Infrastructure & Release Engineering |
| Component | General |
| Severity | S3 |
| Priority | P3 |
| Keywords | regression |

## References

- [examples.md](references/examples.md) - Workflow examples and user request mappings
- [api-reference.md](references/api-reference.md) - REST API endpoints and fields
