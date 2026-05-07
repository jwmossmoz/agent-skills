---
name: ci-fix-without-image-change
description: >
  Fix Firefox CI failures, worker-pool migration blockers, image rollout blockers,
  or test-suite regressions when the user says the worker image must not be
  changed. Use this skill for "fix this without updating the image", "make this
  work on the current worker pool", "do not change the alpha image", "green up
  this pool migration", "why does this pass/fail on the new pool", or when a
  bug is blocked on Taskcluster/Treeherder evidence and the right fix must be in
  Gecko, test harness code, task configuration, or expectations rather than the
  VM image.
argument-hint: "[bug, task, push, label, worker pool, or failure description]"
---

# CI Fix Without Image Change

Resolve Firefox CI blockers when the worker image is off limits. The goal is to
find a code, harness, task configuration, or test-expectation fix that works on
the current worker pool, then prove it with Treeherder/Taskcluster data.

Use this skill as an investigation playbook, not as permission to paper over a
real product behavior. Preserve useful coverage whenever possible.

## Ground Rules

- Treat "do not change the worker image" as a hard constraint.
- Validate on the target production pool unless the user explicitly asks for an
  alpha/predeploy pool.
- Do not conclude "fixed upstream" from a small green sample. Check current
  Bugzilla, Treeherder, and Taskcluster data.
- Use old notes only as leads. Final claims must come from current logs,
  task definitions, code, or Bugzilla comments.
- Avoid disabling user-facing behavior or broad prefs just to make CI green
  unless a reviewer explicitly endorses that tradeoff.
- Keep try usage focused. Cancel side tasks that are clearly unnecessary.
- Save commands, task IDs, links, logs, screenshots, and conclusions in the
  user's requested artifact location when one is specified.

If the task resembles the Windows 11 25H2 reftest occlusion investigation, read
`references/reftest-25h2-case-study.md` for a concrete example of the evidence
standard.

## Workflow

### 1. Frame the Actual Blocker

Collect the durable facts before changing code:

- Bug IDs and the latest relevant comments.
- Exact failing job label, platform, variant, chunk, and task ID.
- Target worker pool and whether the job already runs there.
- Failure signature from logs, not just Treeherder job color.
- Whether the failure is permanent, frequent intermittent, or rare intermittent.
- Prior backouts and rejected fixes.

Useful commands and sources:

```bash
qmd query "<bug id> <suite> <pool> failure notes" -c moz -n 5
treeherder-cli <revision> --repo try --json
taskcluster task def <TASK_ID> | jq '.provisionerId, .workerType, .metadata.name'
taskcluster task status <TASK_ID>
taskcluster task artifacts <TASK_ID>
```

When working in Firefox source, prefer `searchfox-cli` for code history and
identifier search. Use Bugzilla and primary source code/docs for final claims.

### 2. Build a Baseline

Before testing a fix, establish what "broken" means on the current pool:

- Query similar-job history for the failing job. Record pass/fail/retry rates.
- Compare at least one failing log and one passing log on the same label when
  available.
- Confirm the worker pool from the task definition, not from the job name.
- Check whether a green try run sampled the same label/chunk as the failure.
- If the old failure is intermittent, say so explicitly.

Strong baseline evidence looks like:

- "Latest 120 similar jobs: 104 success, 4 testfailed, 4 retry."
- "Recent failing logs still contain `<signature>` on `<pool>`."
- "This push did not validate the original shape because the prerequisite build
  busted before tests scheduled."

### 3. Find a Root-Cause Path

Trace the failure from symptom to mechanism:

- For harness timeouts, identify what event or state is being waited on.
- For image-looking failures, identify whether the image exposed an existing
  product/harness assumption.
- For occlusion, focus, GPU, audio, codec, and policy failures, find the Gecko
  or harness code path that reacts to the environment.
- Look for existing narrow mechanisms in Gecko before adding new knobs.

Prefer fixes that are:

- Narrow to the affected suite or automation mode.
- Explainable from source code.
- Compatible with production/user behavior.
- Testable with a targeted stress or control run.

Be suspicious of fixes that only hide the signal, such as disabling broad
tracking, skipping large test groups, or moving the failure to another pool.

### 4. Design Cheap Try Pushes

Always dry-run exact selections before pushing:

```bash
./mach try fuzzy --no-push --show-chunk-numbers \
  -q '^test-...exact-label...$'
```

Use `--show-chunk-numbers` for chunked suites and anchor exact labels with
`^...$` when validating a specific failure. Do not put `DONTBUILD` in the try
message when builds are required.

Choose the cheapest valid build strategy:

- Use `--use-existing-tasks task-id=<decision-task>` when the patch does not
  need new build artifacts.
- Use artifact builds for JS/Python/harness-only experiments when they are valid
  for the suite.
- Use a normal build for final validation when task configuration, packaging,
  compiled code, or shipped artifacts are involved.
- Use small rebuild counts first, then expand only if the signal is ambiguous.

Example targeted push:

```bash
./mach try fuzzy --no-artifact --show-chunk-numbers --rebuild 3 \
  -q '^test-windows11-32-25h2/opt-reftest-wr-dc3-c-2$' \
  -m 'Bug N - validate targeted fix on current pool'
```

For diagnostics, keep try-only instrumentation opt-in through env vars or a
temporary commit. Do not mix try-only stress code into the landing candidate.

### 5. Control CI Cost

After the decision task expands, inspect the job list and cancel unrelated
source/lint/verification jobs while preserving the needed dependency chain.

```bash
curl -sS -A 'Mozilla/5.0' \
  'https://treeherder.mozilla.org/api/project/try/jobs/?push_id=<PUSH_ID>&count=300' \
  -o /tmp/jobs.json

python3 - <<'PY' > /tmp/cancel-side.sh
import json
jobs = json.load(open('/tmp/jobs.json')).get('results', [])
for job in jobs:
    name = job['job_type_name']
    task_id = job.get('task_id')
    if task_id and name.startswith('source-test-'):
        print(f'taskcluster task cancel {task_id}')
PY
sh /tmp/cancel-side.sh
```

Only cancel tasks you understand. Keep decision tasks, required builds,
generate-profile tasks, signing/package dependencies, and the selected tests.

### 6. Handle Treeherder Delays Correctly

Treeherder/Lando timing often looks confusing:

- A Lando try job can be landed before Treeherder indexes the push.
- A push may show only the decision task until taskgraph expansion finishes.
- Tests can be `unscheduled` until build/profile dependencies complete.
- `pending` means waiting for capacity; it is not active worker runtime cost.
- `live_backing.log` and screenshots may return 404 until a task has produced
  the artifact.
- A build bustage before tests schedule is not a test result.

Use Lando status for new try submissions when Treeherder has not indexed yet:

```bash
curl -sSL 'https://lando.moz.tools/landing_jobs/<LANDO_JOB_ID>/' | jq
```

Use task definitions to explain unscheduled/pending tests:

```bash
taskcluster task def <TEST_TASK_ID> | jq '.dependencies'
```

### 7. Prove or Disprove the Fix

A good fix validation has more than green jobs:

- It runs the exact active failing label/chunk on the target worker pool.
- It records task IDs, revision, push ID, and worker pool.
- It counts the old failure signature in logs.
- It includes a control or stress run when a simple green result is not enough.
- It separates diagnostic screenshot/video work from the root-cause fix.

The strongest pattern is to force the old precondition while showing the fatal
state no longer occurs. Example: a reftest run can report thousands of
`isWindowFullyOccluded true` warnings, but if `isCompositorPaused true` stays at
zero and the suite passes, that directly validates the compositor-pause fix.

Download and summarize artifacts:

```bash
taskcluster task artifacts <TASK_ID>
curl -sSfL '<artifact-url>/public/logs/live_backing.log' -o live_backing.log
```

Count signatures directly:

```bash
python3 - <<'PY'
from pathlib import Path
text = Path('live_backing.log').read_text(errors='replace')
for needle in [
    'TEST-UNEXPECTED',
    'isWindowFullyOccluded true',
    'isCompositorPaused true',
    'persistent g.windowUtils',
    'Result: SUCCEEDED',
    'Result: FAILED',
]:
    print(f'{needle}: {text.count(needle)}')
PY
```

### 8. Leave a Useful Record

Write notes as you go. Include:

- Bug IDs and latest relevant comments.
- The root-cause chain.
- Rejected approaches and why they were rejected.
- Exact try commands.
- Treeherder links, revisions, push IDs, decision/build/test task IDs.
- Worker pool proof from task definitions.
- Log counters and artifact links.
- Which side tasks were cancelled.
- Residual risk and what still needs reviewer confirmation.

Keep Bugzilla comments concise. Link the evidence and state the theory in a few
sentences; avoid pasting the whole investigation.

## Completion Checklist

Before calling the issue solved, verify:

- The fix uses the current requested worker pool.
- No worker image or alpha image changes were made.
- The exact failing label/chunk was validated, or the gap is explicitly stated.
- The old failure signature is absent or transformed in the expected way.
- Any screenshot/video evidence is tied to a task artifact, not just Treeherder UI.
- Side tasks that were known to be wasteful were cancelled.
- Notes are saved where the user asked.
- No Phabricator patch was submitted unless the user explicitly approved it.

## Related Skills

- `treeherder` — query jobs, similar history, logs, artifacts.
- `taskcluster` — inspect task definitions, status, dependencies, artifacts, and cancel tasks.
- `os-integrations` — run targeted OS/pool validation try pushes.
- `bugzilla` — read/update bug context.
- `worker-image-investigation` — compare image versions and pool details when image history is relevant, even if the final fix cannot be an image change.
