---
name: win11-files
description: >
  Query Windows 11 cumulative update file information for 24H2 and 25H2. Search
  for DLLs, drivers, and system files across all patch levels. Compare file
  versions between builds, track version history, and identify what changed in
  each update. Use when: (1) investigating which Windows build introduced a file
  version, (2) comparing file changes between patches, (3) finding DLL/driver
  versions for specific builds, (4) debugging Windows update regressions,
  (5) user asks about Windows 11 24H2 or 25H2 files, KB updates, or build
  versions.
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
