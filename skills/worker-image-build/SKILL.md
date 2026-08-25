---
name: worker-image-build
description: >
  Use when discovering, starting, or monitoring Firefox CI Windows worker-image
  GitHub Actions builds. DO NOT USE FOR failure investigation or a complete
  production rollout.
metadata:
  version: "1.1"
---

# Worker Image Build

Trigger a configured build in `mozilla-platform-ops/worker-images` with the
authenticated `gh` CLI.

## Prerequisites

Install `gh`, authenticate it, and confirm that your account is allowed by
`.github/relsre.json` in the worker-images repository.

## Usage

```bash
REPO=mozilla-platform-ops/worker-images

# Read the dispatchable configuration names from the workflow input.
gh workflow view "FXCI - Azure" --repo "$REPO" --yaml
gh workflow view "FXCI - Azure - Trusted" --repo "$REPO" --yaml

# Start one untrusted build.
gh workflow run "FXCI - Azure" --repo "$REPO" -f config=<CONFIG_NAME>

# Find and watch the new run.
gh run list --repo "$REPO" --workflow "FXCI - Azure" --limit 1 \
  --json databaseId,url,status,createdAt
gh run watch <RUN_ID> --repo "$REPO"
```

Use `FXCI - Azure - Trusted` for a trusted configuration. Read
[examples.md](references/examples.md) for complete commands.

## Gotchas

- Workflow input options are authoritative. A YAML file can exist without a
  dispatch option.
- A trusted configuration must use the trusted workflow.
- Build an `-alpha` image before production. A build usually takes 30 to 60
  minutes and opens a release-notes pull request.
- Do not merge release notes or recommend production deployment until
  **os-integrations** shows that all Tier 1 tasks pass against the latest
  autoland decision baseline.

## Related Skills

- Use **worker-image-investigation** for failures in an existing image.
- Use **production-image-deploy** for a complete production rollout.
