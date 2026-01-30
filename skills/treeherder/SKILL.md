---
name: treeherder
description: >
  Query Firefox Treeherder for CI job results using the lumberjackth CLI.
  Use after commits land to check test/build results.
  Triggers on "treeherder", "job results", "check tests", "ci status".
---

# Treeherder

Query Mozilla Treeherder for CI job results, pushes, and performance alerts using the `lumberjackth` CLI.

## Quick Start

```bash
# List jobs for a push
uvx --from lumberjackth lj jobs autoland --push-id 12345

# Watch jobs with auto-refresh (great for monitoring try pushes)
uvx --from lumberjackth lj jobs try --push-id 12345 --watch
uvx --from lumberjackth lj jobs try -r abc123 -w -i 60  # 60s refresh

# Filter jobs by platform regex
uvx --from lumberjackth lj jobs autoland --push-id 12345 -p "linux.*64"

# Query failures by bug ID
uvx --from lumberjackth lj failures 2012615 -t autoland -p "windows.*24h2"

# Fetch and search job logs
uvx --from lumberjackth lj log autoland 545896732 -p "ERROR|FAIL" -c 3

# Show errors and bug suggestions
uvx --from lumberjackth lj errors autoland 545896732

# Output as JSON
uvx --from lumberjackth lj --json jobs autoland --push-id 12345
```

## Commands

| Command | Description |
|---------|-------------|
| `repos` | List available repositories |
| `pushes <project>` | List recent pushes |
| `jobs <project>` | List jobs (supports regex filtering) |
| `job <project> <guid>` | Get job details |
| `log <project> <job_id>` | Fetch/search job logs |
| `failures <bug_id>` | Query failures by bug ID |
| `errors <project> <job_id>` | Show errors and bug suggestions |
| `perf-alerts` | List performance alerts |

## Common Filters

**jobs command:**
- `-p, --platform` - Platform regex (e.g., `"linux.*64"`)
- `-f, --filter` - Job name regex (e.g., `"mochitest"`)
- `-r, --revision` - Filter by revision
- `--duration-min` - Minimum duration in seconds
- `--result` - Filter by result (testfailed, success, etc.)
- `-w, --watch` - Watch mode with auto-refresh
- `-i, --interval` - Refresh interval in seconds (default: 30)

**log command:**
- `-p, --pattern` - Regex pattern to search
- `-c, --context` - Context lines around matches
- `--tail` / `--head` - Show last/first N lines

**failures command:**
- `-t, --tree` - Repository (autoland, mozilla-central, etc.)
- `-p, --platform` - Platform regex
- `-b, --build-type` - Build type regex (asan, debug, opt)

## Global Options

- `--json` - Output as JSON
- `-s, --server URL` - Custom Treeherder server

## Prerequisites

None - uses `uvx` for zero-install execution. No authentication required.

## References

- `references/cli-reference.md` - Complete CLI documentation with all options
- `references/sheriff-workflows.md` - Sheriff workflow examples
- `references/api-reference.md` - REST API documentation

## External Documentation

- **Treeherder**: https://treeherder.mozilla.org/
- **lumberjackth**: https://pypi.org/project/lumberjackth/
