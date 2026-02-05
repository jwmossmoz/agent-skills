---
name: os-integrations
description: >
  Run Firefox mach try commands with pre-configured flags for os-integration testing
  on Windows and Linux alpha worker pools. Use when testing Firefox changes against
  Windows 10, Windows 11, Ubuntu 24.04, hardware workers, ARM64, or AMD configurations.
  Triggers on "os-integration", "mach try", "windows testing", "linux testing", "alpha image".
---

# OS Integrations

Run Firefox `mach try` commands with pre-configured worker pool overrides for testing against alpha images.

## Usage

```bash
# Run with preset (dry-run to preview)
uv run scripts/run_try.py win11-24h2 --dry-run

# Push to try server
uv run scripts/run_try.py win11-24h2 --push

# Filter to specific test types (recommended)
uv run scripts/run_try.py win11-24h2 -t xpcshell -t mochitest-browser-chrome --push
uv run scripts/run_try.py win11-24h2 -t mochitest-devtools-chrome -t mochitest-chrome-1proc --dry-run

# Override query (advanced)
uv run scripts/run_try.py win11-24h2 -q "test-windows11-64-24h2" --push
```

## Quick Validation (Skip Firefox Build)

Use `--use-existing-tasks` to reuse builds from the latest mozilla-central decision task, skipping the 45+ minute Firefox build:

```bash
# Quick validation - reuse existing Firefox builds
uv run scripts/run_try.py win11-24h2 --use-existing-tasks -t xpcshell --push

# Use a specific decision task
uv run scripts/run_try.py win11-24h2 --task-id ABC123 -t mochitest-browser-chrome --push

# Force fresh build (overrides --use-existing-tasks)
uv run scripts/run_try.py win11-24h2 --fresh-build --push
```

## Watching Test Results

Use `--watch` to automatically monitor test results with lumberjackth after pushing:

```bash
# Push and watch all test results
uv run scripts/run_try.py win11-24h2 -t xpcshell --watch

# Watch with filter (regex)
uv run scripts/run_try.py win11-24h2 --watch --watch-filter "xpcshell|mochitest"

# Combine with existing tasks for fast iteration
uv run scripts/run_try.py win11-24h2 --use-existing-tasks -t xpcshell --watch
```

## Common Test Types

Use `-t` to filter to specific test suites:

- `xpcshell` - XPCShell tests
- `mochitest-browser-chrome` - Browser chrome mochitests
- `mochitest-chrome-1proc` - Chrome mochitests (single process)
- `mochitest-devtools-chrome` - DevTools mochitests
- `mochitest-plain` - Plain mochitests
- `reftest` - Reference tests
- `crashtest` - Crash tests

## Available Presets

- `win11-24h2` - Windows 11 24H2 standard
- `win11-hw` - Windows 11 hardware workers
- `win10-2009` - Windows 10 2009
- `win11-amd` - Windows 11 AMD configuration
- `win11-source` - Source image testing
- `b-win2022` - Build worker testing
- `win11-arm64` - ARM64 architecture

## Prerequisites

- Firefox repository at `~/firefox`
- Must be on a feature branch (not main/master)
- Mozilla Auth0 authentication (for Lando-based pushes)

## Additional Documentation

- **Presets Configuration**: See `references/presets.yml`
- **Linux Worker Overrides**: See `references/linux-worker-overrides.md`
- **Pushing to Try**: See `references/pushing-to-try.md`
- **Script Help**: Run `uv run scripts/run_try.py --help`

## Official Documentation

For more information on mach try and Taskcluster:

- **Firefox Try Documentation**: https://firefox-source-docs.mozilla.org/tools/try/
- **Taskcluster Documentation**: https://docs.taskcluster.net/
- **Firefox Source Docs**: https://firefox-source-docs.mozilla.org/
