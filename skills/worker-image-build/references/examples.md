# Example Commands

## Trigger Builds

### Untrusted Windows 11 24H2 (alpha)
```bash
gh workflow run "FXCI - Azure" \
  --repo mozilla-platform-ops/worker-images \
  -f config=win11-64-24h2-alpha
```

### Untrusted Windows 11 24H2 (production)
```bash
gh workflow run "FXCI - Azure" \
  --repo mozilla-platform-ops/worker-images \
  -f config=win11-64-24h2
```

### Untrusted Windows 10 (alpha)
```bash
gh workflow run "FXCI - Azure" \
  --repo mozilla-platform-ops/worker-images \
  -f config=win10-64-2009-alpha
```

### Untrusted Windows Server 2022 (alpha)
```bash
gh workflow run "FXCI - Azure" \
  --repo mozilla-platform-ops/worker-images \
  -f config=win2022-64-2009-alpha
```

### Untrusted Windows 11 ARM64 tester (alpha)
```bash
gh workflow run "FXCI - Azure" \
  --repo mozilla-platform-ops/worker-images \
  -f config=win11-a64-24h2-tester-alpha
```

### Untrusted Windows 11 ARM64 builder (alpha)
```bash
gh workflow run "FXCI - Azure" \
  --repo mozilla-platform-ops/worker-images \
  -f config=win11-a64-24h2-builder-alpha
```

### Trusted Windows Server 2022
```bash
gh workflow run "FXCI - Azure - Trusted" \
  --repo mozilla-platform-ops/worker-images \
  -f config=trusted-win2022-64-2009
```

### Trusted Windows 11 ARM64 builder
```bash
gh workflow run "FXCI - Azure - Trusted" \
  --repo mozilla-platform-ops/worker-images \
  -f config=trusted-win11-a64-24h2-builder
```

## Check Build Status

### Get latest untrusted run
```bash
gh run list --repo mozilla-platform-ops/worker-images \
  --workflow "FXCI - Azure" --limit 1 \
  --json databaseId,url,status,createdAt,displayTitle
```

### Get latest trusted run
```bash
gh run list --repo mozilla-platform-ops/worker-images \
  --workflow "FXCI - Azure - Trusted" --limit 1 \
  --json databaseId,url,status,createdAt,displayTitle
```

### Watch a run in progress
```bash
gh run watch <RUN_ID> --repo mozilla-platform-ops/worker-images
```

### View run details
```bash
gh run view <RUN_ID> --repo mozilla-platform-ops/worker-images
```

### View run logs
```bash
gh run view <RUN_ID> --repo mozilla-platform-ops/worker-images --log
```

### List recent runs for a specific config
```bash
gh run list --repo mozilla-platform-ops/worker-images \
  --workflow "FXCI - Azure" --limit 10 \
  --json databaseId,url,status,createdAt,displayTitle | \
  jq '.[] | select(.displayTitle | contains("win11-64-24h2-alpha"))'
```

## List Available Workflows

```bash
gh workflow list --repo mozilla-platform-ops/worker-images
```

## View Workflow Details

```bash
gh workflow view "FXCI - Azure" --repo mozilla-platform-ops/worker-images
```
