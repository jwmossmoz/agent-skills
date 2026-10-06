---
name: os-integrations
description: >
  Use when sending Firefox try pushes to alpha worker pools to validate Windows
  or Linux worker images, including build reuse, task selection, Lando status,
  and result watching.
metadata:
  version: "1.3"
---

# OS Integrations

Run the helper from a configured Firefox source checkout.

## Prerequisites

Install `uv`. Install `treeherder-cli` for `--watch` and `lando-cli` for
`--watch-lando`.

Use [fetch_worker_pools.py](scripts/fetch_worker_pools.py) to list current alpha
pools from `fxci-config`.

## Usage

```bash
OS_TRY=~/.claude/skills/os-integrations/scripts/run_try.py
uv run "$OS_TRY" win11-24h2 -t xpcshell --dry-run
uv run "$OS_TRY" win11-24h2 -t xpcshell --watch
```

The default reuses builds from the latest autoland decision task. Use
`--task-id` for a specific decision task or `--fresh-build` when required.
Use `--query-set` or `--query` for custom selection. Run `--help` for options.

## Validation gate

Compare candidate failures with today's equivalent tasks on autoland,
mozilla-central, or another existing pool. Matching failures already present
there are baseline noise, including Tier 1, and do not block deployment. Only
candidate failures whose equivalent tests pass elsewhere are image blockers.
Link the baseline logs; missing or unfinished results are inconclusive. Do
not require an all-green run or invent a failure-frequency gate.

## Gotchas

- Start with `--dry-run`; broad queries can schedule many tasks.
- `--watch` implies a push unless `--dry-run` is set.
- Preset validation comes from [presets.yml](references/presets.yml).
- Read [linux-worker-overrides.md](references/linux-worker-overrides.md) before
  changing Linux scopes or payload fields.

## Related Skills

Use **treeherder** for results, **worker-image-investigation** for unique
failures, and **lando** for separate landing checks. See
[pushing-to-try.md](references/pushing-to-try.md) for selector details.
