---
name: worker-image-build
description: >
  Trigger GitHub Actions workflows in mozilla-platform-ops/worker-images
  to build Firefox CI Windows worker images (FXCI Azure trusted and
  untrusted, win10-2009 / win11-24h2 / win11-a64 / win2022). Use to start
  an image build or check the status of a triggered run. DO NOT USE FOR
  debugging an existing image's failures (use worker-image-investigation).
metadata:
  version: "1.0"
---

# Worker Image Build

Build Firefox CI worker images by triggering GitHub Actions workflows.

## Supported Workflows

| Workflow | Name | Purpose |
|----------|------|---------|
| `sig-nontrusted.yml` | FXCI - Azure | Build untrusted Windows images |
| `sig-trusted.yml` | FXCI - Azure - Trusted | Build trusted Windows images |

## Available Configs

### Untrusted (FXCI - Azure)

```
win10-64-2009-alpha       win10-64-2009
win11-64-2009-alpha       win11-64-2009
win11-64-24h2-alpha       win11-64-24h2
win11-64-24h2-alpha-v6
win11-a64-24h2-tester-alpha    win11-a64-24h2-tester
win11-a64-24h2-builder-alpha   win11-a64-24h2-builder
win2022-64-2009-alpha          win2022-64-2009
win2022-64-2009-alpha-v6
```

### Trusted (FXCI - Azure - Trusted)

```
trusted-win11-a64-24h2-builder
trusted-win2022-64-2009
```

## Trigger a Build

```bash
# Untrusted image
gh workflow run "FXCI - Azure" \
  --repo mozilla-platform-ops/worker-images \
  -f config=<CONFIG_NAME>

# Trusted image
gh workflow run "FXCI - Azure - Trusted" \
  --repo mozilla-platform-ops/worker-images \
  -f config=<CONFIG_NAME>
```

Example:
```bash
gh workflow run "FXCI - Azure" \
  --repo mozilla-platform-ops/worker-images \
  -f config=win11-64-24h2-alpha
```

## Check Build Status

After triggering, get the run URL:

```bash
# Get latest run for untrusted
gh run list --repo mozilla-platform-ops/worker-images \
  --workflow "FXCI - Azure" --limit 1 \
  --json databaseId,url,status,createdAt

# Get latest run for trusted
gh run list --repo mozilla-platform-ops/worker-images \
  --workflow "FXCI - Azure - Trusted" --limit 1 \
  --json databaseId,url,status,createdAt
```

Watch a specific run:

```bash
gh run watch <RUN_ID> --repo mozilla-platform-ops/worker-images
```

View run logs:

```bash
gh run view <RUN_ID> --repo mozilla-platform-ops/worker-images --log
```

## Build Process

1. Access check against `.github/relsre.json`
2. Azure login with FXCI credentials
3. Packer build (30-60 min)
4. SBOM generation
5. Release notes PR created

## Naming Conventions

- `-alpha` suffix: Test/staging images
- No suffix: Production images
- `trusted-` prefix: Trusted pool images
- `-a64-`: ARM64 architecture
- `-64-`: x64 architecture
- `tester`/`builder`: Pool role

## More Examples

See [references/examples.md](references/examples.md) for additional command examples.

## Gotchas

- Access is gated by `.github/relsre.json` in mozilla-platform-ops/worker-images — if your gh user isn't on that list, the workflow rejects the trigger immediately.
- Builds take 30-60 min (Packer). Use `gh run watch` rather than polling `gh run list` in a tight loop.
- `-alpha` configs build to staging galleries; non-suffixed configs go to production. Always validate image changes through `-alpha` first.
- `trusted-` prefixed configs require the trusted workflow (`FXCI - Azure - Trusted`); they fail if you trigger them on the untrusted workflow and vice versa.
- After a successful build, a release-notes PR is opened automatically — don't merge it until the alpha image has been validated through `os-integrations`.

## Repository

https://github.com/mozilla-platform-ops/worker-images
