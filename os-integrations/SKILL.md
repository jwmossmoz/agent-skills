---
name: os-integrations
description: >
  Run Firefox mach try commands with pre-configured flags for os-integration testing
  on Windows alpha worker pools. Use when testing Firefox changes against Windows 10,
  Windows 11, hardware workers, ARM64, or AMD configurations. Triggers on
  "os-integration", "mach try", "windows testing", "try push", "worker pool",
  "taskcluster testing".
---

# OS Integrations

## Overview

This skill enables running Firefox mach try commands with pre-configured flags optimized for os-integration testing against Windows alpha worker pools in Taskcluster. Use this when testing Firefox changes on specific Windows configurations, hardware setups, or non-standard architectures.

## Quick Start

Use run_try.py to push try runs with os-integration presets:

```bash
uv run scripts/run_try.py win11-24h2
uv run scripts/run_try.py win11-hw --push
uv run scripts/run_try.py win10-2009 --dry-run
```

## Available Presets

- **win11-24h2**: Windows 11 24H2 standard (gecko-t worker pools)
- **win11-hw**: Windows 11 hardware workers (releng-hardware pools)
- **win10-2009**: Windows 10 2009 (gecko-t worker pools)
- **win11-amd**: Windows 11 AMD worker configuration
- **win11-source**: Source image testing on Windows 11
- **b-win2022**: Build worker testing on Windows Server 2022
- **win11-arm64**: ARM64 architecture testing on Windows 11

## Common Flags

- `--no-os-integration`: Skip the os-integration preset and use default filters
- `--rebuild N`: Run each task N times
- `--env KEY=VALUE`: Set environment variables for the try run
- `-q/--query`: Override the query filter for task selection
- `--push`: Automatically push to try (requires branch validation)
- `--dry-run`: Preview the generated mach try command without executing

## Pre-flight Checks

The script validates:
- Current branch is appropriate for try pushes
- Preset configuration is valid
- Worker pool availability in Taskcluster

## Discovering Worker Pools

Use `fetch_worker_pools.py` to discover available alpha worker pools from mozilla-releng/fxci-config:

```bash
uv run scripts/fetch_worker_pools.py
```

This fetches worker-pools.yml from GitHub and lists all alpha pools grouped by category (gecko-t, releng-hardware, gecko-1).
