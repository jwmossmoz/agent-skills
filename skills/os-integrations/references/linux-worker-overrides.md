# Linux Worker Overrides for Marionette Integration Testing

## Overview

This guide covers testing marionette-integration tests on specific Linux worker images using worker overrides in `mach try`. This is useful when testing new Ubuntu worker images before deploying them to production.

## Common Issues with Marionette Integration Tests

Marionette integration tests may fail with different worker images. Common issues include:
- Missing gecko.log file causing test harness to fail
- Missing tests tagged with `os_integration`
- Image configuration issues (missing dependencies, wrong Taskcluster version, etc.)

## Testing with Alpha Images

To test marionette-integration tests against alpha worker images (e.g., testing new Ubuntu 24.04 images with updated Taskcluster or new dependencies):

### ASAN Variant Test

```bash
cd ~/firefox
./mach try fuzzy \
  --query "test-linux2404-64-asan/opt-marionette-integration" \
  --worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha
```

### Debug Variant Test

```bash
cd ~/firefox
./mach try fuzzy \
  --query "test-linux2404-64/debug-marionette-integration" \
  --worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha
```

### Opt Variant Test

```bash
cd ~/firefox
./mach try fuzzy \
  --query "test-linux2404-64/opt-marionette-integration" \
  --worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha
```

## Understanding Worker Overrides

### Format

```bash
--worker-override <alias>=<worker-pool>
```

- **alias**: The worker alias used in taskcluster config (e.g., `t-linux-docker-noscratch-amd`)
- **worker-pool**: The full worker pool name including provisioner (e.g., `gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha`)

### Finding Worker Aliases

Worker aliases are defined in `~/firefox/taskcluster/config.yml` under the `workers.aliases` section. For Linux docker workers:

```yaml
t-linux-docker(|-noscratch|-noscratch-amd|-16c32gb-amd|-amd):
    provisioner: '{trust-domain}-t'
    implementation: docker-worker
    os: linux
    worker-type: '{alias}'
```

This pattern means tests can use these aliases:
- `t-linux-docker`
- `t-linux-docker-noscratch`
- `t-linux-docker-noscratch-amd`
- `t-linux-docker-16c32gb-amd`
- `t-linux-docker-amd`

### Worker Pool Naming Convention

Worker pools are defined in the fxci-config repository in `worker-images.yml`. The format is:

```
<provisioner>/<worker-type-prefix>-<image-name>
```

For alpha images:
- Provisioner: `gecko-t` (for test workers)
- Worker type: `t-linux-docker-noscratch-amd`
- Image name: `ubuntu-2404-headless-alpha` (from worker-images.yml)

Full pool: `gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha`

## Common Worker Pool Names

### Ubuntu 24.04 Docker Images

**Production:**
```bash
--worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless
```

**Alpha (for testing):**
```bash
--worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha
```

### Ubuntu 24.04 Wayland Images

**Production:**
```bash
--worker-override t-linux-2404-wayland-snap=gecko-t/t-linux-2404-wayland-snap
```

**Alpha:**
```bash
--worker-override t-linux-2404-wayland-snap=gecko-t/t-linux-2404-wayland-snap-ubuntu-2404-wayland-alpha
```

## Multiple Worker Overrides

You can override multiple worker aliases in a single try push:

```bash
./mach try fuzzy \
  --query "marionette" \
  --worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha \
  --worker-override t-linux-docker=gecko-t/t-linux-docker-ubuntu-2404-headless-alpha
```

## Testing Other Linux Test Suites

The same pattern works for other test suites:

```bash
# Web platform tests
./mach try fuzzy \
  --query "test-linux2404-64/opt-web-platform-tests" \
  --worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha

# Mochitest
./mach try fuzzy \
  --query "test-linux2404-64/opt-mochitest-plain" \
  --worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha

# XPCShell
./mach try fuzzy \
  --query "test-linux2404-64/opt-xpcshell" \
  --worker-override t-linux-docker-noscratch-amd=gecko-t/t-linux-docker-noscratch-amd-ubuntu-2404-headless-alpha
```

## Verifying Results

After pushing to try, monitor results using:

```bash
treeherder-check
```

Or visit Treeherder directly and search for your try push.

## Troubleshooting

### Worker override not working

Check:
1. The worker alias matches what's in `taskcluster/config.yml`
2. The worker pool exists in the fxci-config deployment
3. The alpha image has been built and deployed to Taskcluster
4. You have permissions to use the worker pool (alpha pools may be restricted)

### Finding the right worker alias

If unsure which worker alias a test uses:

```bash
cd ~/firefox
rg "worker-type\|worker-alias" taskcluster/kinds/test/
```

Or check the task definition on Treeherder by clicking on a job and viewing the "Task Definition" tab.

## Related Files

- `~/firefox/taskcluster/config.yml` - Worker alias definitions
- `~/github_moz/fxci-config/worker-images.yml` - Worker image mappings
- `~/firefox/taskcluster/kinds/test/marionette.yml` - Marionette test definitions
- `~/firefox/taskcluster/kinds/test/kind.yml` - General test kind configuration
