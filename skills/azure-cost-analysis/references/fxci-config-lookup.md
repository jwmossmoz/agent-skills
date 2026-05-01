# fxci-config Worker Pool Lookup

`mozilla-releng/fxci-config/worker-pools.yml` is the source of truth for what Azure VM SKU each pool uses, what regions it runs in, and how it's weighted. Verify here before claiming "pool X uses VM Y" or "regions changed".

## Repo and file

- Repo: `https://github.com/mozilla-releng/fxci-config` (public)
- File: `worker-pools.yml`
- Raw URL: `https://raw.githubusercontent.com/mozilla-releng/fxci-config/main/worker-pools.yml`

Cache it locally for grep-friendly access:
```bash
curl -sL "https://raw.githubusercontent.com/mozilla-releng/fxci-config/main/worker-pools.yml" -o worker-pools.yml
```

## Pool definition structure

Each Azure pool entry looks roughly like:

```yaml
- pool_id: '{pool-group}/win11-64-24h2-{suffix}'
  provider_id: azure2
  variants:
    - pool-group: gecko-t
    - pool-group: gecko-t
      suffix: gpu
    # ... more variants
  config:
    image:
      by-suffix:
        default: <image-name>
    locations:
      by-pool-group:
        default:
          by-suffix:
            default: [<region-1>, <region-2>, ...]
    maxCapacity:
      by-pool-group:
        gecko-t:
          by-suffix:
            '': <max>
            alpha: <max>
            gpu: <max>
            default: <max>
    spot: true
    vmSizes:
      - vmSize:
          by-suffix:
            source-alpha: <SKU>
            .*large.*:    <SKU>
            alpha:        <SKU>
            webgpu:       <SKU>
            gpu:          <SKU>
            default:      <SKU>
    worker-manager-config:
      capacityPerInstance: 1
      initialWeight:
        by-vmSize:
          <SKU>:
            by-location:
              <region>: <weight>
              # ...
```

## Looking up a specific pool's VM SKU

The `vmSizes.by-suffix` block resolves the suffix to a VM size. For a pool ID like `gecko-t/win11-64-24h2-gpu`:
- pool_id template: `{pool-group}/win11-64-24h2-{suffix}` with `pool-group=gecko-t`, `suffix=gpu`
- Match `gpu` in the relevant `vmSizes.by-suffix` block → that SKU value

For the same pool with no suffix (default variant):
- Match `default` in `vmSizes.by-suffix` → default SKU

## Common verifications

### "Do two pools (e.g. 24H2 and 25H2 variants) use the same SKU?"
Look at both pool definitions side by side. Compare the resolved `vmSizes.by-suffix` value for the suffix of interest. Don't assume — sometimes related pools use the same SKU for default/regular workers but different SKUs for GPU variants.

### "Which regions does this pool run in?"
Find the pool's `locations` block. Note the `by-suffix` and `by-pool-group` patterns can override based on variant.

### "How many concurrent VMs can this pool spin up?"
Find the `maxCapacity` block. Check both base and any `by-suffix` overrides.

### "What's the per-region weight (which regions get used first)?"
Find `worker-manager-config.initialWeight.by-vmSize.<SKU>.by-location`. Higher weight = higher priority for new VMs.

## Worker defaults

Top of the file. Most relevant for cost:

```yaml
worker-defaults:
  lifecycle:
    queueInactivityTimeout:
      by-provider:
        azure.*: <seconds>
        default: <seconds>
    registrationTimeout: <seconds>
    reregistrationTimeout: <seconds>
```

`queueInactivityTimeout` for Azure (multi-hour by default) means if a VM has no tasks in queue for that long, it gets shut down. Lower = faster deallocation = less idle billing, but more VM churn. This is a structural cost knob.

## Git history — who changed what when

The GitHub commit history for `worker-pools.yml` is essential context for cost investigations. List recent commits:

```bash
curl -s "https://api.github.com/repos/mozilla-releng/fxci-config/commits?path=worker-pools.yml&since=YYYY-MM-DDT00:00:00Z&per_page=30" \
  | python3 -c "import json,sys; [print(c['commit']['committer']['date'][:10], c['sha'][:8], c['commit']['message'].split(chr(10))[0]) for c in json.load(sys.stdin)]"
```

Get a specific commit's diff:
```bash
curl -sL "https://github.com/mozilla-releng/fxci-config/commit/<sha>.diff"
```

## Cost-relevant change types to grep for in commit titles

| Pattern | Meaning |
|---|---|
| `maxCapacity` | Concurrent VM ceiling — directly affects how many VMs can be billed simultaneously |
| `initialWeight` | Region preference — affects which (and how many) regions provision new VMs |
| `vmSize` / `Standard_*` | VM SKU change — directly changes hourly rate |
| `add region` / `add location` | New region added — different spot prices, different availability |
| `add ... pool` / `chore(azure): add` | New pool — additive cost |
| `headless` | Headless task variant — different VM lifecycle |

## Investigation workflow

When investigating a cost anomaly with a known approximate date:

1. List commits to `worker-pools.yml` around that date (1-2 weeks before to capture deployment lag)
2. Identify any cost-relevant changes (see patterns table above)
3. Pull the diff for each candidate commit
4. Map the changed pool/SKU/region to the cost meter that moved in your data
5. Note: a config change merged on day N may take some additional time to fully propagate through TC worker-manager — allow 1-2 days lag when correlating
