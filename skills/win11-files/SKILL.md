---
name: win11-files
description: >
  Query a local SQLite database of Windows 11 24H2 and 25H2 cumulative-
  update file information — DLLs, drivers, and system files across all
  KB releases. Use when investigating which build introduced a file
  version, comparing files between patches, tracking a file's version
  history, or debugging Windows update regressions in CI worker images.
metadata:
  version: "1.0"
---

# Windows 11 Files

Query file entries across Windows 11 cumulative updates for 24H2 and 25H2.

## Database

Preferred location: `~/moz_artifacts/win11_files.db` (combined, has `version` column)
Legacy fallback: `~/moz_artifacts/win11_24h2_files.db` (24H2 only, no `version` column)

Schema (combined):
```
files(version, kb_number, release_date, build, update_type, file_name, file_version, date, time, file_size)
```

Schema (legacy 24H2-only):
```
files(kb_number, release_date, build, update_type, file_name, file_version, date, time, file_size)
```

Indexes: `file_name`, `kb_number`, `build`, `file_version`

## Quick Start

```bash
# Refresh combined 24H2 + 25H2 database
uv run ~/.claude/skills/win11-files/scripts/update_db.py

# Search for files (all versions)
uv run ~/.claude/skills/win11-files/scripts/query.py search ntdll.dll

# Search within a specific Windows version
uv run ~/.claude/skills/win11-files/scripts/query.py --version 24H2 search ntdll.dll

# Version history for specific file
uv run ~/.claude/skills/win11-files/scripts/query.py history ntdll.dll

# Compare two builds
uv run ~/.claude/skills/win11-files/scripts/query.py diff 26100.6584 26100.6899

# List all patches
uv run ~/.claude/skills/win11-files/scripts/query.py builds

# Database stats
uv run ~/.claude/skills/win11-files/scripts/query.py stats

# Custom SQL
uv run ~/.claude/skills/win11-files/scripts/query.py sql "SELECT DISTINCT file_version FROM files WHERE file_name='kernel32.dll' ORDER BY build"
```

## Refresh Data

Update `~/moz_artifacts/win11_files.db` from Microsoft release history and
support KB file-info CSVs:

```bash
uv run ~/.claude/skills/win11-files/scripts/update_db.py
```

Optional paths:

```bash
uv run ~/.claude/skills/win11-files/scripts/update_db.py --legacy-db ~/moz_artifacts/win11_24h2_files.db --output-db ~/moz_artifacts/win11_files.db
```

### How 25H2 ingest works

24H2 and 25H2 share the same servicing branch — Microsoft typically ships one
KB that updates both versions, with build `26100.x` for 24H2 and `26200.x`
for 25H2. The KB's file-info CSV usually contains a single
`Windows 11, version 24H2` section because the underlying binaries are
identical.

The updater fetches each KB's CSV once (cached by KB number), then for each
release entry it tries to find the matching `Windows 11, version <ver>`
section. If MS doesn't publish a 25H2-specific section, the parser falls
back to the 24H2 section. So 25H2 rows reflect what MS actually publishes:
build `26200.x`, but file_version `10.0.26100.x` whenever the binaries are
shared. If MS later starts publishing 25H2-specific sections, they'll be
picked up automatically with no script change.

Some out-of-band (OOB) KBs (e.g. KB5070881, KB5072359, KB5086672) have no
file-info CSV; the updater logs a warning and skips them.

## Global Options

### --version

Filter results by Windows 11 version. Accepted values: `24H2`, `25H2`. Omit to query all versions.

```bash
uv run ~/.claude/skills/win11-files/scripts/query.py --version 25H2 search kernel32.dll
uv run ~/.claude/skills/win11-files/scripts/query.py --version 24H2 builds
```

When using the legacy 24H2-only database, this flag is ignored (all data is 24H2).

## Commands

### search
Find files by name pattern (case-insensitive contains match by default).
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py search kernel          # contains "kernel"
uv run ~/.claude/skills/win11-files/scripts/query.py search kernel32.dll --exact  # exact match
uv run ~/.claude/skills/win11-files/scripts/query.py search .sys --limit 100
```

### history
Track how a file's version changed across all patches. Shows `*` marker when version changed.
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py history ntdll.dll
uv run ~/.claude/skills/win11-files/scripts/query.py history tcpip.sys
```

### diff
Compare file changes between two builds. Shows added, removed, and changed files.
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py diff 26100.6584 26100.6899
uv run ~/.claude/skills/win11-files/scripts/query.py diff 26100.2894 26100.7705 --limit 20
```

### builds
List all available patches with file counts.
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py builds
```

### sql
Run arbitrary SQL queries for complex analysis.
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py sql "SELECT file_name, COUNT(DISTINCT file_version) as versions FROM files GROUP BY file_name ORDER BY versions DESC LIMIT 20"
```

### stats
Show database statistics.
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py stats
```

## Common Queries

Find files that changed most frequently:
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py sql "SELECT file_name, COUNT(DISTINCT file_version) as ver_count FROM files GROUP BY file_name HAVING ver_count > 10 ORDER BY ver_count DESC LIMIT 30"
```

Find all kernel-mode drivers (.sys) in a specific build:
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py sql "SELECT file_name, file_version FROM files WHERE build='26100.6584' AND file_name LIKE '%.sys' ORDER BY file_name"
```

Check if a specific file version exists:
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py sql "SELECT kb_number, build, release_date FROM files WHERE file_name='ntoskrnl.exe' AND file_version='10.0.26100.6584'"
```

Compare a file across Windows versions (requires combined database):
```bash
uv run ~/.claude/skills/win11-files/scripts/query.py sql "SELECT version, build, file_version FROM files WHERE file_name='ntdll.dll' ORDER BY version, build"
```

## Gotchas

- Two databases coexist: `win11_files.db` (combined, has `version` column) and the legacy `win11_24h2_files.db` (no `version`). Scripts pick the combined DB when present; `--version` filters become no-ops on the legacy DB.
- 25H2 file versions often look like 24H2 (`10.0.26100.x`) because Microsoft ships shared binaries — only the build differs (`26100.x` vs `26200.x`). Don't read identical file versions as "no change".
- Some out-of-band KBs (e.g. KB5070881, KB5072359, KB5086672) don't publish file-info CSVs and are skipped during ingest with a warning. Check `references/` or the run logs if a KB is missing.
- `update_db.py` is incremental — re-run it weekly (or after a Patch Tuesday) to pick up new releases. The fetch is cached per-KB so it's cheap.
