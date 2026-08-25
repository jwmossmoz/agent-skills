---
name: win11-files
description: >
  Use when finding Windows 11 cumulative update file versions, build changes,
  file history, or KB provenance in the local 24H2 and 25H2 SQLite database.
metadata:
  version: "1.1"
---

# Windows 11 Files

Query file metadata collected from Microsoft cumulative-update file lists.

## Prerequisites

Install `uv`. The preferred database is `~/moz_artifacts/win11_files.db`. The
scripts also accept the legacy 24H2-only database.

## Usage

```bash
WIN11=~/.claude/skills/win11-files/scripts/query.py
WIN11_UPDATE=~/.claude/skills/win11-files/scripts/update_db.py

# Refresh the combined 24H2 and 25H2 database.
uv run "$WIN11_UPDATE"

# Search, follow history, compare builds, or inspect coverage.
uv run "$WIN11" --version 25H2 search ntdll.dll
uv run "$WIN11" history ntdll.dll
uv run "$WIN11" diff 26100.6584 26100.6899
uv run "$WIN11" builds
uv run "$WIN11" stats
```

Use `sql` for questions that the standard commands do not answer. Run each
script with `--help` for database paths, exact matching, limits, and output
options.

## Gotchas

- The combined database has a `version` column. The legacy database does not,
  and ignores `--version`.
- 24H2 and 25H2 can share binaries. A 25H2 build can contain a file version
  that starts with `10.0.26100`; compare both build and file version.
- Microsoft does not publish file-information CSVs for some out-of-band KBs.
  The updater reports and skips them.
- The updater is incremental and caches each KB. Run it after Patch Tuesday or
  when the required build is absent.

## Related Skills

- Use **worker-image-investigation** to connect a file change to a CI failure.
