# Build and verify (phases 1–2)

Read this when you dispatch worker-images builds, choose a validation surface, or verify what was published.

## Repos and phase order

End-to-end skill for promoting a new worker image into Firefox CI: trigger
the build in `mozilla-platform-ops/worker-images`, verify the published
artifact, bump `worker-images.yml` in `mozilla-releng/fxci-config`, open the
rollout PR, announce it, confirm the pools roll over, and record the completed
Windows deployment in Bugzilla.

| Repo | Role |
|---|---|
| `mozilla-platform-ops/ronin_puppet` | Source of truth for what's provisioned inside the image. A `master` commit hash is baked in as the image's `deploymentId`. |
| `mozilla-platform-ops/worker-images` | Packer + Action workflows that build images. Per-config YAML (`config/<name>.yaml`) carries the target version + `deploymentId`. SBOMs land in `sboms/`. |
| `mozilla-releng/fxci-config` | Worker-pool definitions. `worker-images.yml` is the "what gets booted in CI" map; bumping it is what puts a new image into rotation. |

Treat the phases below as a checklist. Skip phase 1 if the user already
triggered the build — verify what's published before editing fxci-config.
Phase 5 (post-merge health) always happens. Phase 6 applies to Windows
production rollouts.

## Validation surfaces

Integration tests run at three surfaces; which apply depends on the cloud
and configs rebuilt.

| Surface | What it is | Coverage |
|---|---|---|
| 1 — in-build | Azure non-trusted workflows auto-chain `os-integration.yml` after `packer`; results show as `OS Integration Tests - <config>` jobs in the same run. | Skips all `win2022*`, all trusted builds, all Linux, and (alpha-parallel only) `win11-a64-*-builder`. |
| 2 — fxci-config PR | Comment `/taskcluster integration` on the bump PR; runs every `integration`-tagged task against the pool+image binding in the PR's diff. Reports via `checks-v1`. | Carries the load for whatever surface 1 skips. Wired up in phase 3. |
| 3 — mach try | Fallback via the `os-integrations` skill when 1 and 2 don't cover what you need (perf/talos/browsertime, broader candidate iteration, reproducing a specific failure). | On demand. Watch in Treeherder; new Tier-1 reds → fix in ronin_puppet and rebuild. |

## Phase 1 — Trigger the build

Pick the workflow by cloud + image kind. Files live in
`worker-images/.github/workflows/`; all require membership in
`.github/relsre.json`.

### Windows (Azure SIG)

| Workflow name | Use when |
|---|---|
| `FXCI - Azure` | Single untrusted config (`win10-*`, `win11-*`, `win2022-*`, alphas). Most common. |
| `FXCI - Azure - Trusted` | Trusted gallery only: `trusted-win11-a64-25h2-builder`, `trusted-win2022-64-2009`. |
| `FXCI - Azure Prod Parallel Images` | Every production Windows config in one matrix (6 untrusted + 2 auto-discovered Azure `trusted-*`). For ronin_puppet bumps affecting all families. |
| `FXCI - Azure Alpha Parallel Images` | Same, alpha pools only. |

### Linux (GCP)

| Workflow name | Use when |
|---|---|
| `FXCI - GCP` | Single alpha Ubuntu 24.04 config (untrusted, level-1). |
| `FXCI - GCP Production` | Single production Ubuntu 24.04 config. |
| `FXCI - GCP Prod Parallel Images` | Every production Linux config (L1 + L3) in one matrix. |
| `FXCI - GCP Alpha Parallel Images` | Same, alpha. |

### Before dispatching (Windows)

- **Set the ronin_puppet pin.** Windows builds deploy the `deploymentId` in
  `config/windows_production_defaults.yaml` (commit must be on `master`). If
  it doesn't match the desired hash, land a small worker-images PR bumping it
  (and each config's `image_version`) first. Latest master:
  `gh api repos/mozilla-platform-ops/ronin_puppet/commits/master --jq '.sha[0:7]'`.
  Version semantics + bump steps: `references/windows.md`.
- **Check the Marketplace base image** for a regressing republish, and use
  `azure.build_location` to retry in another region if a CDN issue is
  suspected — both in `references/windows.md`.
- Linux builds are date-stamped (no `deploymentId`), so these don't apply.

### Alpha-first sequence (Windows)

The expected order for a ronin_puppet bump is **alpha then production**, gated
on the alpha builds' surface-1 os-integration passing. Dispatch
`FXCI - Azure Alpha Parallel Images`, confirm its `OS Integration Tests`
jobs are green, then dispatch the prod parallel workflow.

Caveat: alpha configs don't auto-track master — several pin `sourceBranch` to
a relops feature branch with `deploymentId: NA`. To validate a *master*
commit on alpha, set the prod-defaults `deploymentId` **and** switch each
alpha config to `sourceBranch: master` + `deploymentId: default`. That
overwrites whatever feature branch the alpha was testing — **confirm with the
user first.** Note the surface-1 gaps (`win11-a64-25h2-builder-alpha` is
commented out of `images.alpha`; a64 builders and `win2022*` aren't
auto-chained) and lean on surface 2/3 for those.

A config that fails 5+ reruns can be removed from `images.production` so
parallel prod runs stay clean while you fix it; add it back after.

### Dispatching

```bash
# Windows single config
gh workflow run "FXCI - Azure" --repo mozilla-platform-ops/worker-images -f config=win11-64-25h2
# Windows trusted single config
gh workflow run "FXCI - Azure - Trusted" --repo mozilla-platform-ops/worker-images -f config=trusted-win11-a64-25h2-builder
# Full prod rollout (no inputs — builds the matrix)
gh workflow run "FXCI - Azure Prod Parallel Images" --repo mozilla-platform-ops/worker-images
# Linux production single / full
gh workflow run "FXCI - GCP Production" --repo mozilla-platform-ops/worker-images -f config=gw-fxci-gcp-l1-2404-headless-alpha
gh workflow run "FXCI - GCP Prod Parallel Images" --repo mozilla-platform-ops/worker-images
```

Surface the run URL and hand off — builds take a while; don't poll tightly:

```bash
gh run list --repo mozilla-platform-ops/worker-images --workflow "<name>" --limit 1 \
  --json databaseId,url,status,createdAt
```

`gh run watch` follows only one run; for parallel dispatches poll `gh run
list` or rely on the per-run GHA email.

## Phase 2 — Verify what was published

Job badges lie in both directions: a "failure" job can still have published
to SIG, and a "success" job can publish the wrong version if `image_version`
wasn't bumped. **The gallery and SBOM are authoritative, not the badge.**

For each rebuilt config:

1. Inspect job conclusions (`gh run view <RUN_ID> --json jobs`), including any
   `OS Integration Tests - <config>` job (surface 1).
2. **(Windows) Confirm the version exists in the SIG** — the authoritative
   check that worker-manager can reach it:
   ```bash
   az sig image-version list --resource-group rg-packer-worker-images \
     --gallery-name <gallery_name> --gallery-image-definition <image_name> \
     --query "[].{name:name, state:provisioningState}" -o table
   ```
   `provisioningState` should be `Succeeded`. If absent, the build didn't
   publish.
3. Cross-check the baked-in `deploymentId` via the gallery version tags or
   the SBOM (`sboms/<config>-<version>.md`, UTF-16LE).
4. **(Linux)** Capture the published GCE image name (with date suffix) from
   the deploy step's log — that's what goes into fxci-config. Confirm the
   matching production SBOM landed in `worker-images/sboms/`, and save its
   `blob/main` URL for the fxci-config PR and Slack changelog.

Detailed verify recipes, SBOM parsing, and missing-SBOM recovery:
`references/windows.md` and `references/linux.md`.
