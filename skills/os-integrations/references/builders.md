# Server 2025 Builder Validation

Use the same Server 2022 builder task set on these alpha pools:

| Preset | Target pool |
| --- | --- |
| `b-win2025` | `gecko-1/b-win2025-alpha` (Desktop) |
| `b-win2025-core` | `gecko-1/b-win2025-core-alpha` |
| `b-win2025-gpu` | `gecko-1/b-win2025-gpu-alpha` |

Each preset selects exact labels assigned to `b-win2022` in the full task graph.
This includes tasks absent from the scheduled graph. Each preset runs fresh
builder tasks: reused Firefox builds would not exercise the candidate image.
Normal Taskcluster dependencies still control task order.

## Prepare and preview

Use a clean Firefox checkout at the source revision that matches one frozen
latest autoland decision. `--task-id` fixes the discovery graph; it does not
change the checkout revision for fresh builds. Use `--checkout` to select the
checkout without changing another source tree.

```bash
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
OS_TRY=~/.claude/skills/os-integrations/scripts/run_try.py
CHECKOUT=/path/to/clean/firefox
DECISION=$(taskcluster api index findTask \
  gecko.v2.autoland.latest.taskgraph.decision | jq -r .taskId)

for preset in b-win2025 b-win2025-core b-win2025-gpu; do
  uv run "$OS_TRY" "$preset" --checkout "$CHECKOUT" \
    --task-id "$DECISION" --dry-run || break
done
```

Check that all three previews select the same labels, with only the target pool
changed. Review the count and scope before submitting. Discovery failure or an
empty builder selection stops the command.

## Submit and compare

Repeat the loop with `--push` in place of `--dry-run`. Submit the pushes one at a
time because they share a checkout and try configuration. Their Taskcluster
jobs can run in parallel; no separate parallel runner is needed. Confirm the
checkout is still clean and at the intended source revision before each push.

Keep each Lando job ID and Treeherder URL. Compare candidate failures with the
corresponding Server 2022 tasks at that autoland revision. Missing baseline
results are inconclusive. Record startup, storage, driver, build, and PGO
failures separately. A successful image build is not builder validation.

## Helper tests

Run the [regression tests](../scripts/test_run_try.py) after changes to presets
or discovery. These tests do not submit tasks or change a Firefox checkout.

```bash
uv run ~/.claude/skills/os-integrations/scripts/test_run_try.py -v
```
