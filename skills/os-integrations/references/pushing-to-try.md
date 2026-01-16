# Pushing to Try

Reference documentation for pushing to Mozilla's try server.

## Overview

"Pushing to Try" enables developers to build and test changes on Mozilla's automation infrastructure without requiring code review and landing.

**Official Documentation:** https://firefox-source-docs.mozilla.org/tools/try/index.html

## Methods

### Method 1: Lando (Default, Recommended)

The modern default uses Lando, which converts Git patches to Mercurial and pushes to `hg.mozilla.org/try`.

**Requirements:**
- Official Firefox repository configured as a git remote
- Remote branch references (e.g., `origin/autoland`)
- Mozilla Auth0 account authentication

**Example:**
```bash
./mach try fuzzy -xq test-windows11-64 --preset os-integration
```

Lando handles the conversion and push automatically. No git-cinnabar needed.

### Method 2: Direct VCS Push

Using the `--push-to-vcs` flag bypasses Lando and pushes directly.

**Requirements:**
- git-cinnabar installed (`./mach vcs-setup`)
- SSH push access to `hg.mozilla.org`

**Example:**
```bash
./mach try fuzzy -xq test-windows11-64 --preset os-integration --push-to-vcs
```

## Monitoring Your Try Push

After pushing, you'll receive:
- **Treeherder URL**: `https://treeherder.mozilla.org/jobs?repo=try&revision=<REVISION>`
- **Lando Job ID**: `https://api.lando.services.mozilla.com/landing_jobs/<JOB_ID>`

## Common Commands

```bash
# Fuzzy selector with preset
./mach try fuzzy --preset os-integration

# Auto-select tasks based on changes
./mach try auto

# Specific test suite
./mach try fuzzy -xq "mochitest-chrome"

# With worker overrides for alpha testing
./mach try fuzzy --preset os-integration \
  --worker-override win11-64-24h2=gecko-t/win11-64-24h2-alpha
```

## Troubleshooting

### "Could not detect git-cinnabar"

If using `--push-to-vcs`, install git-cinnabar:
```bash
./mach vcs-setup
```

Or use the default Lando method (no flag needed).

### Auth0 Token Issues

Re-authenticate:
```bash
./mach try fuzzy --preset os-integration
# Follow the Auth0 prompts
```
