# Taskcluster Integration References

This document provides references to Mozilla repositories that integrate with Taskcluster, showing real-world usage patterns.

## Key Repositories

### mozilla-releng/fxci-config

**Repository**: https://github.com/mozilla-releng/fxci-config

**Purpose**: Configuration repository for Firefox CI infrastructure, including worker pool definitions, worker images, and Taskcluster settings.

**Key Files**:
- `worker-pools.yml` - Defines all Taskcluster worker pools with Azure/GCP/AWS configurations
- `worker-images.yml` - Maps worker images to worker pools
- `.taskcluster.yml` - Defines CI tasks for the repository itself

**Common Use Cases**:
1. **Adding/Modifying Worker Pools**: Edit `worker-pools.yml` to configure new worker types
2. **Updating Worker Images**: Edit `worker-images.yml` to roll out new images
3. **Configuring Queue Settings**: Modify `queueInactivityTimeout`, `maxCapacity`, etc.
4. **ARM Template Management**: Configure Azure ARM templates for worker deployment

**Example Worker Pool Configuration**:
```yaml
gecko-t/win11-64-24h2-alpha:
  providerId: azure
  config:
    minCapacity: 0
    maxCapacity: 10
    queueInactivityTimeout: 600
    capacityPerInstance: 1
    machineType: Standard_E8ads_v6
    imageRef:
      resourceGroup: fxci-prod-level-1-workers
      id: win116424h2alpha
    armDeployment:
      templateSpecId: /subscriptions/.../taskcluster-arm-template-v6-nvme/versions/1.0
```

**Workflow Integration**:
- Pull requests trigger decision tasks in Taskcluster
- Use `gh pr view <PR_NUMBER>` to see task status
- Tasks run validation, staging, and production deployments

**Related Skills**:
- Use **os-integrations** skill to test worker pools with Firefox mach try
- Use **taskcluster** skill to debug worker pool issues
- Use **jira** skill to track worker pool deployment stories

### mozilla-platform-ops/worker-images

**Repository**: https://github.com/mozilla-platform-ops/worker-images

**Purpose**: Packer templates and scripts for building Taskcluster worker images (Windows, Linux, macOS).

**Key Files**:
- `packer/` - Packer templates for building images
- `scripts/` - Provisioning scripts (install software, configure workers)
- `.taskcluster.yml` - Builds and publishes worker images via Taskcluster

**Image Types**:
1. **Windows Images**:
   - `win11-64-24h2-alpha` - Windows 11 24H2 for testing
   - `win11-64-2022-source` - Windows Server 2022 source builds
   - `win10-2009` - Windows 10 21H2

2. **Linux Images**:
   - GCP: `gw-fxci-gcp-l1-2404-amd64-gui` (Ubuntu 24.04 GUI)
   - GCP: `gw-fxci-gcp-l1-2404-amd64-headless` (Ubuntu 24.04 headless)
   - GCP: `gw-fxci-gcp-l1-2404-arm64-headless` (Ubuntu 24.04 ARM64)

3. **macOS Images**:
   - Built for macOS worker pools

**Common Use Cases**:
1. **Updating Taskcluster Version**: Edit provisioning scripts to install new taskcluster-worker version
2. **Adding Software**: Modify provisioning scripts (e.g., add podman, docker, compilers)
3. **Debugging Image Issues**: Check build logs in Taskcluster tasks

**Example Workflow**:
```bash
# 1. Make changes to provisioning scripts
vim scripts/linux/install_taskcluster.sh

# 2. Create a pull request
gh pr create --title "feat: Update taskcluster to 95.1.3"

# 3. PR triggers Taskcluster build tasks
# 4. Check task status with taskcluster skill
uv run ~/github_moz/agent-skills/skills/taskcluster/scripts/tc.py status <TASK_ID>

# 5. After images are built, update fxci-config to use new images
cd ../fxci-config
vim worker-images.yml
```

**Integration with fxci-config**:
- After building images, update `worker-images.yml` in fxci-config
- Reference images by name (e.g., `win116424h2alpha`, `gw-fxci-gcp-l1-2404-amd64-gui`)
- Deploy image updates via fxci-config pull requests

## Taskcluster Configuration Patterns

### Worker Pool Configuration

Worker pools in `fxci-config/worker-pools.yml` follow this structure:

```yaml
<provisionerId>/<workerType>:
  providerId: azure|gcp|aws
  config:
    # Capacity settings
    minCapacity: 0
    maxCapacity: 100
    capacityPerInstance: 1

    # Queue settings
    queueInactivityTimeout: 600  # seconds worker can be inactive

    # Provider-specific settings (Azure example)
    machineType: Standard_E8ads_v6
    location: westus2
    imageRef:
      resourceGroup: fxci-prod-level-1-workers
      id: win116424h2alpha

    # ARM template for Azure deployments
    armDeployment:
      templateSpecId: /subscriptions/.../versions/1.0
```

### Task Definitions

Tasks are defined in `.taskcluster.yml` files:

```yaml
version: 1
tasks:
  - taskId: {$eval: 'taskId'}
    provisionerId: proj-firefox
    workerType: ci
    payload:
      image: node:18
      command:
        - /bin/bash
        - -c
        - |
          npm install
          npm test
    metadata:
      name: Run tests
      description: Execute test suite
```

### Common Taskcluster Environment Variables

Tasks in Mozilla CI have access to these environment variables:

- `TASKCLUSTER_ROOT_URL` - Taskcluster instance URL
- `TASKCLUSTER_WORKER_POOL_ID` - Current worker pool ID
- `TASK_ID` - Current task ID
- `TASK_GROUP_ID` - Task group ID (usually equals decision task ID)
- `GECKO_HEAD_REV` - Firefox revision being tested
- `GECKO_HEAD_REPOSITORY` - Firefox repository URL

## Worker Pool Debugging

Common issues and how to debug with Taskcluster skill:

### Issue: Workers Not Starting

```bash
# 1. Check task status to see worker pool errors
uv run tc.py status <TASK_ID>

# 2. Get full task definition to check worker pool config
uv run tc.py definition <TASK_ID> | jq '.workerType, .provisionerId'

# 3. Check fxci-config for worker pool definition
cd ~/github_moz/fxci-config
yq eval '.["gecko-t/win11-64-24h2-alpha"]' worker-pools.yml

# 4. For Azure workers, check ARM template configuration
az ts show --name taskcluster-arm-template-v6-nvme --version 1.0 \
  --resource-group template-spec --query properties.mainTemplate
```

### Issue: Tasks Stuck Pending

```bash
# 1. Check if it's a capacity issue
# Look for "waiting for worker" in status
uv run tc.py status <TASK_ID> | jq '.status.runs[-1]'

# 2. Check worker pool max capacity
cd ~/github_moz/fxci-config
yq eval '.["gecko-t/win11-64-24h2-alpha"].config.maxCapacity' worker-pools.yml

# 3. See all pending tasks in the group
uv run tc.py group-list <GROUP_ID> | \
  jq '.tasks[] | select(.status.state == "pending") | .task.metadata.name'
```

### Issue: Worker Configuration Errors

```bash
# 1. Get task definition to see what was requested
uv run tc.py definition <TASK_ID> | jq '.payload'

# 2. Check worker pool configuration in fxci-config
cd ~/github_moz/fxci-config
yq eval '.["gecko-t/win11-64-24h2-alpha"]' worker-pools.yml

# 3. Compare with ARM template (for Azure)
# Look for mismatches in disk configuration, VM size, etc.
```

## Useful Commands

### Find Worker Pools Using a Specific Image

```bash
cd ~/github_moz/fxci-config
yq eval 'to_entries | .[] | select(.value.config.imageRef.id == "win116424h2alpha") | .key' worker-pools.yml
```

### List All Worker Pools by Provider

```bash
cd ~/github_moz/fxci-config
yq eval 'to_entries | .[] | select(.value.providerId == "azure") | .key' worker-pools.yml
```

### Check Taskcluster Version in Images

```bash
# For Linux images, check provisioning script
cd ~/github_moz/worker-images
grep -r "taskcluster.*version" scripts/linux/

# For Windows images
grep -r "TASKCLUSTER_VERSION" scripts/windows/
```

## Additional Resources

- **Taskcluster Docs**: https://docs.taskcluster.net/
- **Taskcluster Source**: https://github.com/taskcluster/taskcluster
- **Firefox CI**: https://firefox-ci-tc.services.mozilla.com/
- **fxci-config**: https://github.com/mozilla-releng/fxci-config
- **worker-images**: https://github.com/mozilla-platform-ops/worker-images
- **Azure ARM Templates**: https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/
