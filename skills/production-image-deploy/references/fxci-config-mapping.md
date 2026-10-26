# worker-images config → fxci-config mapping

`worker-images.yml` (in `mozilla-releng/fxci-config`) is keyed by an
opaque image alias that doesn't always match the worker-images config
filename. This is the single most common source of mistakes during a
bump. Don't trust the alias to be obvious — look it up.

The most reliable way is to grep for the underlying `name:` field, which
echoes the worker-images config filename:

```bash
cd ~/github_moz/fxci-config
grep -B1 -A4 'name: <worker-images-config-name>' worker-images.yml
```

Example: `worker-images@config/win11-64-25h2.yaml` corresponds to:

```yaml
win116425h2:
  azure2:
    version: 1.0.13
    resource_group: rg-packer-worker-images
    deployment_id: "29172b6"
    name: win11_64_25h2          # ← matches config/<this>.yaml
```

Note the underscores: the `name` field in fxci-config swaps hyphens for
underscores. The mapping is otherwise straightforward.

## Windows mapping (azure2 / azure_trusted)

| worker-images config | fxci-config key | Provider |
|---|---|---|
| `win10-64-2009` | `ronin_t_windows10_64_2009_prod` | azure2 |
| `win10-64-2009-alpha` | `ronin_t_windows10_64_2009_alpha` | azure2 |
| `win11-64-25h2` | `win116425h2` | azure2 |
| `win11-64-25h2-alpha` | `win116425h2alpha` | azure2 |
| `win11-a64-24h2-builder` | `ronin_b1_windows11_a64_24h2_builder` | azure2 |
| `win11-a64-24h2-builder-alpha` | `ronin_b1_windows11_a64_24h2_builder_alpha` | azure2 |
| `win11-a64-24h2-tester` | `ronin_t_windows11_a64_24h2_tester` | azure2 |
| `win11-a64-24h2-tester-alpha` | `ronin_t_windows11_a64_24h2_tester_alpha` | azure2 |
| `win11-a64-25h2-builder` | `win11a6425h2builder` | azure2 |
| `win11-a64-25h2-builder-alpha` | `win11a6425h2builderalpha` | azure2 |
| `win11-a64-25h2-tester` | `win11a6425h2tester` | azure2 |
| `win11-a64-25h2-tester-alpha` | `win11a6425h2testeralpha` | azure2 |
| `win2022-64-2009` | `ronin_b1_windows2022_64_2009` | azure2 |
| `win2022-64-2009-alpha` | `ronin_b1_windows2022_64_2009_alpha` | azure2 |
| `trusted-win11-a64-24h2-builder` | `ronin_b3_windows11_a64_24h2_builder` | azure_trusted |
| `trusted-win11-a64-25h2-builder` | `trusted_win11_a64_25h2_builder` | azure_trusted |
| `trusted-win2022-64-2009` | `ronin_b3_windows2022_64_2009` | azure_trusted |

The `ronin_b{1,3}_*` and `ronin_t_*` keys are legacy naming from when the
provisioner names were exposed in the alias. New configs (`win11a6425h2*`,
`win116425h2*`) use a flatter convention. Both are stable; don't rename.

## Linux mapping (fxci-level1-gcp / fxci-level3-gcp)

Linux entries are keyed by image-purpose alias and reference one or two
GCE image paths directly. The relationship between worker-images config
and fxci-config alias is by image content, not config filename:

| worker-images config family | fxci-config alias | level-1 path | level-3 path |
|---|---|---|---|
| `gw-fxci-gcp-l1-2404-headless-alpha` + `trusted-gw-fxci-gcp-l3-2404-headless-alpha` | `ubuntu-2404-headless` | `taskcluster-imaging` | `fxci-production-level3-workers` |
| `gw-fxci-gcp-l1-2404-arm64-headless-alpha` + `trusted-gw-fxci-gcp-l3-2404-arm64-headless-alpha` | `ubuntu-2404-arm64-headless` | `taskcluster-imaging` | `fxci-production-level3-workers` |
| `gw-fxci-gcp-l1-2404-gui-alpha` | `ubuntu-2404-wayland` | `taskcluster-imaging` | _(none)_ |

Aliases ending in `-alpha` (`ubuntu-2404-headless-alpha`,
`ubuntu-2404-arm64-headless-alpha`, `ubuntu-2404-headless-alpha-tc`,
`relsre-gw-fxci-gcp-2404-amd64-alpha`,
`relsre-gw-fxci-gcp-2404-amd64-gui-alpha`) point to images named with an
`-alpha` suffix and are not part of a production rollout.

`monopacker-*` and `handbuilt-*` aliases reference legacy hand-built
images and are out of scope for this skill — leave them alone.

## Sanity check before committing

After editing, run a diff and check that:

1. Every changed entry has `version` + `deployment_id` updated together
   (Windows) or both `fxci-level1-gcp` and `fxci-level3-gcp` updated
   together where the entry has both (Linux).
2. The number of changed entries matches the user's expectation and the
   current `images.production` list, including rebuilt trusted variants.
   Do not count retired configs. If the diff size surprises you, re-check
   against the SBOMs.
3. No alpha entries (`*_alpha` keys with `version: 1.0.0` and
   `deployment_id: alpha`, or `*-alpha` Linux aliases) were changed.
