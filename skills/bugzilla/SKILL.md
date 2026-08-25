---
name: bugzilla
description: >
  Use when a Mozilla Bugzilla task needs the local helper for issue discovery,
  lifecycle changes, reviewer coordination, evidence attachments, or a
  confirmed worker-image regression report.
metadata:
  version: "1.1"
---

# Bugzilla

The `bz.py` helper covers Bugzilla search, inspection, updates, attachments,
needinfo, and image-regression reports.

## Prerequisites

Read-only commands do not need authentication. Set `BUGZILLA_API_KEY` for
write commands. Create a key in Bugzilla account preferences.

## Usage

```bash
BZ=~/.claude/skills/bugzilla/scripts/bz.py

# Search and inspect.
uv run "$BZ" search --quicksearch "crash" --limit 10
uv run "$BZ" get 1234567 --include-comments --include-history

# Update or create.
uv run "$BZ" needinfo 1234567 --request user@mozilla.com
uv run "$BZ" create --product Firefox --component General \
  --summary "Title" --version unspecified

# Preview a confirmed image-regression report.
uv run "$BZ" create-image-regression --image-version 1.0.9 \
  --worker-pool gecko-t/win11-64-24h2-alpha --dry-run
```

Run `uv run "$BZ" --help` and the command-specific `--help` for all options.
See [examples.md](references/examples.md) for update, attachment, and image
regression examples.

## Gotchas

- Search, get, product, and identity commands are read-only. Create, update,
  comment, attachment, needinfo, and image-regression commands need an API key.
- `--quicksearch` follows Bugzilla's limited quick-search grammar. Use explicit
  product, component, status, and priority filters for structured searches.
- `create` needs product, component, summary, and version. Supply all four.

## References

- [api-reference.md](references/api-reference.md): fields and endpoints
- [scripts/bz.py](scripts/bz.py): implementation
