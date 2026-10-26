# Windows image deploy reference

## Azure subscriptions

- Untrusted: `"FXCI Azure DevTest Subscription"`
- Trusted: `"Trusted FXCI Azure DevTest Subscription"`

## Where the version number comes from

The "version" of a Windows image is an Azure Compute Gallery (Shared Image
Gallery / SIG) version — three numeric components that the Packer build
publishes to the gallery. There is no fixed mapping from OS family to
`MAJOR.MINOR`; both numbers evolve over time and **only the gallery is
authoritative**. Don't assume any particular version is "current" — go
look it up.

To find the next target version for a config:

1. Open `worker-images/config/<config-name>.yaml`. Its
   `sharedimage.image_version` field is the version that build will try to
   publish.
2. If it has not yet been bumped past the latest published version, bump
   it (typically the trailing component) in a worker-images PR before
   dispatching the build. Packer fails fast if the version already exists
   in the gallery.
3. Cross-check with the gallery itself if you want to be certain:
   ```bash
   az sig image-version list \
     --resource-group rg-packer-worker-images \
     --gallery-name <gallery_name> \
     --gallery-image-definition <image_name> \
     --query "[].name" -o tsv | sort -V
   ```
   The gallery and image-definition names are in the same config file.

Configs in the same OS family usually move their trailing component in
lockstep so the fxci-config diff is one coherent step, but that's a
convention, not a constraint of the gallery. Trusted variants
(`config/trusted-*.yaml`) are tracked in their own gallery and bump
independently of their untrusted twins.

## Pre-flight: comparing Marketplace base image versions

Microsoft republishes Marketplace images on its own cadence and the new
image can regress something puppet relies on. Before dispatching,
compare the latest available Marketplace version against the
`OS Version` line in the previous successful SBOM for that config.

Publisher / offer / sku come from the `marketplace_image:` block in
`worker-images/config/<config>.yaml`. Example for `win11-a64-25h2-*`:

```bash
az vm image list \
  --publisher MicrosoftWindowsDesktop \
  --offer windows-11 --sku win11-25h2-ent \
  --all \
  --query "[?starts_with(version,'26100')].{version:version}" \
  -o table
```

If the latest version is newer than the SBOM's `OS Version`, expect
potential regressions. The May 7 republish of `win11-24h2-ent` ARM64
moved the OS build from `26100.8246` to `26100.8457` and broke NetFx3
install intermittently — see "Pinning to last known good" below.

### Pinning to last known good

If a republished Marketplace image is causing build failures, pin
the config's base image version to the last known-good version in
`worker-images/config/<config>.yaml`:

```yaml
marketplace_image:
  publisher: MicrosoftWindowsDesktop
  offer: windows-11
  sku: win11-25h2-ent
  version: 26100.8246.250407  # pinned; was `latest`
```

The exact version string is whatever the `az vm image list` query
above returned for the known-good build. Land the pin as a small
worker-images PR, then re-dispatch.

## The `azure.build_location` knob

Per-config override for the Azure region the Packer build runs in.
The wrapper script defaults to `Central US`; setting
`azure.build_location: <region>` (a single string like `westus2`)
overrides it. Useful when a per-region Microsoft Update CDN issue
is suspected — switch regions and retry. The field lives alongside
the other `azure:` keys in `config/<config>.yaml`.

Confirm Packer honored the override by listing live `pkrvm*` VMs in
the target region:

```bash
az vm list --query "[?location=='<region>' && starts_with(name, 'pkrvm')]" -o table
```

## Where the ronin_puppet commit comes from

Windows configs read `vm.tags.deploymentId` (a ronin_puppet commit hash)
from `worker-images/config/windows_production_defaults.yaml`. Per-config
files can override it; if they do, that override wins.

To bump:

1. Note the current default in
   `worker-images/config/windows_production_defaults.yaml`.
2. Confirm the new ronin_puppet commit is on `master` (Packer hard-codes
   `sourceBranch: master`).
3. Land a small worker-images PR that updates the default `deploymentId`
   and bumps each per-config `image_version` you want rebuilt. Trusted
   configs (`config/trusted-*.yaml`) need their `image_version` bumped
   explicitly; their `deploymentId` follows the default.
4. Then dispatch the build workflow.

## Verifying a published version

The most reliable signal is the per-config `Run Packer` step in the
Action log:

```bash
gh run view --job <JOB_ID> --repo mozilla-platform-ops/worker-images \
  --log 2>&1 | grep -E "(SIG image version|Shared Gallery Image Version ID|DeploymentId|OS Version)"
```

Look for two lines:

```
==> azure-arm.sig:  -> SIG image version : '1.3.3'
==> azure-arm.sig:  -> Shared Gallery Image Version ID : '/subscriptions/.../galleries/<gallery>/images/<image>/versions/1.3.3'
```

If those land but the `Upload release notes` job failed, the SIG image is
still published; the failure just means the SBOM didn't get committed
back to the repo. That's acceptable to ship — note it in the PR body or
fix it in a follow-up.

## SBOMs

`worker-images/sboms/<config>-<version>.md` is generated during the build
and committed by the `Upload release notes` job. The files are UTF-16LE
encoded — read with:

```bash
iconv -f UTF-16LE -t UTF-8 sboms/win11-64-25h2-1.0.3.md | head -40
```

Useful fields it captures:

- `OS Version` — Windows build number (e.g. `26100.8246` for the April
  2026 cumulative on 24H2).
- `DeploymentId` — the ronin_puppet hash actually baked in. Cross-check
  this against what you set in `windows_production_defaults.yaml`.
- `Taskcluster Packages Installed` — generic-worker / livelog /
  start-worker / proxy versions.

If a SBOM is missing for a config that the run claims to have built, look
at the `Upload release notes` job log; the most common failure is
`untracked working tree files would be overwritten by merge` when two
runs race to commit. The image itself is published regardless.

## Range filtering for the PR body

The ronin_puppet commit table in the PR body is filtered to
**Windows-relevant** commits in `<prev_deploymentId>..<new_deploymentId>`.
The cheap filter is:

```bash
cd ~/github_moz/ronin_puppet
git log --oneline <prev>..<new>
git show --stat <commit>  # for each, decide
```

Heuristics for Windows-relevance:

- `data/os/Windows.yaml` change → Windows
- `modules/win_*/` → Windows
- `data/common.yaml` (scriptworker/cot bumps) → usually macOS, skip
  unless verified
- `modules/macos_*` / `tcc_perms` / `osx`/`mac` → macOS, skip
- `roles/gecko_*_b_osx_*` → macOS, skip
- ruby/dependabot bumps → typically skip unless the user asks

When in doubt, include the commit and let review prune. The point is to
give the reviewer a quick read of what's in the bump, not an exhaustive
audit.

## Common pitfalls

- **Forgetting to bump trusted alongside untrusted.** Trusted galleries
  are separate workflows and configs (`config/trusted-*.yaml`,
  `FXCI - Azure - Trusted`). The fxci-config keys `ronin_b3_*` and
  `trusted_win11_a64_25h2_builder` map to trusted images. PR #955 caught
  one of these late — check both halves.
- **Stale alpha entries.** Alpha pools (`*_alpha` keys with
  `deployment_id: alpha`) are not part of a prod rollout. Don't touch
  them in a prod-bump PR.
- **Config dropped from production list.** Before editing, scan
  `worker-images/config/windows_production_defaults.yaml`'s
  `images.production` list. If a config was removed
  (e.g. `win11-64-2009` in worker-images@`9bbca89`), its fxci-config
  entry is frozen at the last shipped version — don't bump it.
- **Re-using a `deploymentId` across families when ranges differ.** The
  Windows families can be at different prior `deploymentId`s.
  Compute the compare range from each family's prior baseline; if they
  resolve to the same range, collapse to one table.

## Troubleshooting: NetFx3 / DXSDK install on fresh ARM64 VMs

The puppet class `dxsdk_jun10::install_net_framework3.5` calls
`Enable-WindowsOptionalFeature -Online -FeatureName NetFx3 -All` and fails
intermittently on fresh ARM64 VMs:

- The DISM call returns non-zero; the feature stays in
  `DisabledWithPayloadRemoved`.
- Packer's `Start-AzRoninPuppet` step fails with `Error code 6`.
- Failures cluster on certain configs / OS versions and on specific reruns
  — partly per-OS-build, partly random.

Recovery, in escalating order:

1. Rerun the failed config up to ~3 times. The failure flips on retry often
   enough that this is worth trying first.
2. Pin the Marketplace base image `version` in the failing config YAML to
   the last known-good version (see "Pinning to last known good" above).
3. Source the Win11 ARM64 NetFx3 SxS cab from a Features-on-Demand ISO,
   stage it in the `roninpuppetassets` blob, and patch
   `dxsdk_jun10::install_net_framework3.5` in ronin_puppet to use
   `-Source <local-path> -LimitAccess` so DISM never fetches from Windows
   Update.

Cap step (1) at ~3 attempts before escalating. One config burning 7 reruns
at ~95 min on Standard_E8pds_v5 is ~16 hours of ARM64 compute for no new
signal — escalate sooner.

## Debugging a failing build from the live VM

The GitHub Actions log only shows what Packer's WinRM session captures. It
lags in-VM activity by 25+ minutes for slow DISM calls and often omits the
real HRESULT. The authoritative source is the in-VM puppet/CBS/DISM logs
while the build VM still exists.

While the build VM is still running (before `cleanup_provisioner` fires),
use `az vm run-command invoke` against the transient packer resource group
(named like `<CONFIG>-<DEPLOYMENT_ID>-<N>-PKRTMP`) to run a PowerShell
payload that reads logs and process state. Locate the VM with `az vm list`.
Hand off the actual PowerShell to a `helper` agent — the right script
depends on what's being investigated.

Things worth knowing before the helper runs:

- Puppet's log path on these images is non-obvious. Start with
  `C:\Windows\Logs\DISM\dism.log` and `C:\Windows\Logs\CBS\CBS.log` — both
  are reliable for Windows-feature install failures.
- DISM at `/LogLevel:4` is verbose enough to surface HRESULTs but slow;
  expect 20+ minutes before a failing DISM call returns.
- Spot-check anything an agent quotes from a specific path — investigators
  can confabulate file content; verify by re-reading from the claimed
  location before acting on it.
- The transient packer resource group is deleted ~60s after the build
  state transitions in GHA (success or failure). Capture anything you need
  before the run completes; otherwise re-dispatch and re-investigate.
