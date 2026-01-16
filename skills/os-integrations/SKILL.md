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

# Override query
uv run scripts/run_try.py win11-24h2 -q "-xq 'mochitest-chrome'" --push
```

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
