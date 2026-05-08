---
name: bugzilla
description: >
  Search, view, create, update, comment on, or attach files to Mozilla
  Bugzilla (bugzilla.mozilla.org) tickets via the bz.py CLI. Use whenever
  the task involves a Bugzilla bug — filing a regression, triaging a crash,
  needinfo'ing a reviewer, or following up on assigned bugs.
---

# Bugzilla CLI

Requires: `export BUGZILLA_API_KEY="your-key"` (get from https://bugzilla.mozilla.org/userprefs.cgi?tab=apikey)

Read-only ops work without auth.

Run via the installed skill path:

```bash
BZ=~/.claude/skills/bugzilla/scripts/bz.py
```

## Usage

```bash
uv run "$BZ" <command> [options]
```

Run `uv run "$BZ" --help` for full options.

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

## Quick Examples

```bash
# Search
uv run "$BZ" search --quicksearch "crash" --limit 10
uv run "$BZ" search --product Firefox --status NEW,ASSIGNED --priority P1

# View
uv run "$BZ" get 1234567 -v --include-comments
uv run "$BZ" get 1234567 --include-comments --full-comments
uv run "$BZ" get 1234567 --include-comments --include-history --format json

# Update
uv run "$BZ" update 1234567 --status RESOLVED --resolution FIXED
uv run "$BZ" needinfo 1234567 --request user@mozilla.com

# Create
uv run "$BZ" create --product Firefox --component General --summary "Title" --version unspecified
```

## Gotchas

- Read-only ops (`search`, `get`, `whoami`, `products`) work without `BUGZILLA_API_KEY`; write ops (`create`, `update`, `comment`, `attachment`, `needinfo`) need it.
- `--quicksearch` only honors what BMO's quicksearch grammar supports. For structured filters use `--product`, `--component`, `--status`, `--priority`.
- `create` requires `--product`, `--component`, `--summary`, and `--version` together — missing any of them produces a confusing 400, not a useful error.

## References

- [examples.md](references/examples.md) - Workflow examples and user request mappings
- [api-reference.md](references/api-reference.md) - REST API endpoints and fields
