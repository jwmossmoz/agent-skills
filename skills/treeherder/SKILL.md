---
name: treeherder
description: >
  Use when querying Mozilla Treeherder for CI results, test history, revision
  comparisons, failure classifications, log patterns, artifacts, or Bugzilla
  suggestions during sheriff and image triage.
metadata:
  version: "1.1"
---

# Treeherder

Use `treeherder-cli` for revision and job analysis. Use the REST API only for
data that the CLI does not expose.

## Prerequisites

Install `treeherder-cli`. Read operations need no authentication. Run
`treeherder-cli --help` before use. The installed help is the source of truth
for supported options.

## Usage

```bash
TH_CLASSIFY=~/.claude/skills/treeherder/scripts/classification.py

treeherder-cli --help
treeherder-cli <REVISION> --repo try --json
treeherder-cli <REVISION> --compare <BASE_REVISION> --repo try --json
treeherder-cli --similar-history <JOB_ID> --similar-count 100 --repo autoland --json
uv run "$TH_CLASSIFY" get --task-id <TASK_ID> --include-notes
```

Use [api-reference.md](references/api-reference.md) for pushes, bug suggestions,
and performance alerts. Use
[similar-jobs-comparison.md](references/similar-jobs-comparison.md) for the raw
comparison API.

## Gotchas

- `--similar-history` needs a numeric Treeherder job ID, not a Taskcluster ID.
- For history by test name or across repositories, use the REST API.
- The default repository is try. Set `--repo` for other branches.
- REST calls need a `User-Agent` header. Deduplicate calls for retried jobs.

## Related Skills

Use **taskcluster** for task operations and **worker-image-investigation** for
image, SBOM, and VM evidence. A Tier 1 failure unique to a new image blocks
deployment; compare with the latest autoland baseline.

## References

[cli-reference.md](references/cli-reference.md) lists all options.
[sheriff-workflows.md](references/sheriff-workflows.md) has triage workflows.
