---
name: worker-image-investigation
description: >
  Investigate Taskcluster task failures related to worker images.
  Compare passing vs failing tasks, extract image versions, find running workers,
  and debug Windows VMs via Azure CLI. Use when debugging CI failures after
  image upgrades, investigating intermittent test failures, or comparing
  worker configurations. Triggers on "image investigation", "worker image",
  "compare tasks", "why is this failing", "image regression", "worker debug".
---

# Worker Image Investigation

Investigate Taskcluster task failures by comparing worker images, extracting SBOM info, and debugging Azure VMs.

## Prerequisites

- `taskcluster` CLI: `brew install taskcluster`
- `az` CLI (for VM debugging): `brew install azure-cli && az login`
- `uv` for running scripts

## Usage

```bash
# Investigate a failing task - get worker pool, image version, status
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py investigate <TASK_ID>
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py investigate https://firefox-ci-tc.services.mozilla.com/tasks/<TASK_ID>

# Compare two tasks (e.g., passing vs failing on same revision)
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py compare <PASSING_TASK_ID> <FAILING_TASK_ID>

# List running workers in a pool (for Azure VM access)
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py workers gecko-t/win11-64-24h2

# Get SBOM/image info for a worker pool
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py sbom gecko-t/win11-64-24h2

# Get Windows build and GenericWorker version from Azure VM
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py vm-info <VM_NAME> <RESOURCE_GROUP>
```

## Investigation Workflow

### 1. Initial Task Analysis

```bash
# Get task info including worker pool and image
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py investigate <FAILING_TASK_ID>
```

Output includes: taskId, taskLabel, workerPool, workerId, images (version), status.

### 2. Find Comparison Task

Use Treeherder to find a passing run of the same test on the same revision or a recent revision:
- Check if test passed on an older image version
- Look for passing runs on mozilla-central vs autoland

### 3. Compare Tasks

```bash
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py compare <PASSING_TASK_ID> <FAILING_TASK_ID>
```

Look for differences in image versions (e.g., 1.0.8 vs 1.0.9).

### 4. Debug Running Worker (Azure)

```bash
# Find running workers
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py workers gecko-t/win11-64-24h2

# Get VM details - extract VM name from workerId (e.g., vm-xyz...)
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py vm-info vm-xyz RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION
```

### 5. Direct Azure VM Commands

For deeper investigation, use Azure CLI directly:

```bash
# Get Windows build number
az vm run-command invoke --resource-group RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION \
  --name <VM_NAME> --command-id RunPowerShellScript \
  --scripts "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').CurrentBuild"

# Get GenericWorker version
az vm run-command invoke --resource-group RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION \
  --name <VM_NAME> --command-id RunPowerShellScript \
  --scripts "Get-Content C:\\generic-worker\\generic-worker-info.json"

# Get recent Windows updates
az vm run-command invoke --resource-group RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION \
  --name <VM_NAME> --command-id RunPowerShellScript \
  --scripts "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10"

# Check for file system filters (AppLocker, etc.)
az vm run-command invoke --resource-group RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION \
  --name <VM_NAME> --command-id RunPowerShellScript \
  --scripts "fltMC"
```

## Common Resource Groups

- **Production:** `RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION`
- **Staging:** `RG-TASKCLUSTER-WORKER-MANAGER-STAGING`

## Common Worker Pools

| Pool | Description |
|------|-------------|
| `gecko-t/win11-64-24h2` | Windows 11 24H2 64-bit production |
| `gecko-t/win11-64-24h2-alpha` | Windows 11 24H2 64-bit alpha (os-integration) |
| `gecko-t/win11-32-24h2` | Windows 11 24H2 32-bit |

## Stage Taskcluster

For CI tasks on fxci-config PRs:

```bash
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py --root-url https://stage.taskcluster.nonprod.cloudops.mozgcp.net \
  investigate <TASK_ID>
```

## Output Format

All commands return JSON for easy parsing with `jq`:

```bash
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py investigate <TASK_ID> | jq '.images[0].version'
uv run ~/.claude/skills/worker-image-investigation/scripts/investigate.py workers gecko-t/win11-64-24h2 | jq '.workers[0].workerId'
```

## Related Skills

- **taskcluster**: Query task status, logs, artifacts
- **treeherder**: Find tasks by revision and job type
- **os-integrations**: Run mach try commands for testing

## References

- Worker image configs: `fxci-config/worker-images/`
- SBOM files: Check Azure Shared Image Gallery
- ronin_puppet: Worker configuration management
