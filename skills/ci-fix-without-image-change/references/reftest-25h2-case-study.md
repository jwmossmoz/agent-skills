# Case Study: Windows 11 25H2 Reftest Without an Image Change

Use this only as a pattern for evidence and reasoning. Re-check current
Bugzilla, Treeherder, Taskcluster, and source code before making claims in a
new investigation.

## Problem Shape

Firefox reftest tasks were being migrated from Windows 11 24H2 GPU workers to
Windows 11 25H2 GPU workers. The migration was backed out after frequent
reftest timeouts. The constraint for the follow-up work was explicit: make the
tests work on the current 25H2 worker pool without changing the Windows image or
alpha image.

The visible failure was a reftest timeout waiting for `MozAfterPaint`. Logs
showed:

- `g.windowUtils.isWindowFullyOccluded true`
- `g.windowUtils.isCompositorPaused true`

That signature mattered more than the initial theory that "some other window is
in front." A screenshot helps identify the desktop state, but the fix needs to
explain why painting stops.

## Investigation Pattern

1. Read the latest Bugzilla comments and treat older notes as leads only.
2. Identify the active production label rather than validating a nearby label.
3. Query similar-job history to understand intermittency.
4. Compare recent failing logs on the current pool with passing logs.
5. Trace the source path behind the failure state.
6. Create a narrow fix that preserves product behavior.
7. Validate the fix with both normal reruns and a stress run that forces the old
   precondition.

## Root-Cause Chain

The key source path was in `CanonicalBrowsingContext::RecomputeAppWindowVisibility()`:

- Windows reports the top-level reftest chrome window as fully occluded.
- Gecko marks the top-level app window inactive.
- The widget pauses the compositor.
- Reftest waits for `MozAfterPaint`.
- No paint arrives while the compositor is paused.

Reftest already used `manualactiveness` for the content browser, but that did
not keep the top-level chrome window's compositor active.

## Fix Direction

The successful fix direction was to set the top-level reftest chrome browsing
context `forceAppWindowActive` on Windows automation, and clear it on unload.

Why this was preferable to other options:

- It uses an existing Gecko mechanism.
- Picture-in-Picture already uses this path for occluded originating windows.
- It does not change the worker image.
- It does not disable Windows occlusion tracking globally.
- It keeps the compositor alive for this harness while preserving the ability
  to detect real occlusion behavior elsewhere.

## Validation Pattern

Normal validation:

- Run the active failing label/chunk on the current worker pool.
- Use multiple rebuilds, but keep the selection narrow.
- Confirm the task definition uses the target worker pool.
- Count the old failure signature in logs.

Stress validation:

- Add a try-only, env-gated change that deliberately recreates the precondition
  of the old failure.
- In this case, the stress run forced the reftest window to be fully occluded.
- The fixed task passed with many `isWindowFullyOccluded true` warnings, zero
  `isCompositorPaused true` warnings, zero persistent occlusion errors, and
  `Unexpected: 0`.

That was stronger than a green try run because it proved the fatal transition
from full occlusion to compositor pause had been broken by the fix.

## Lessons to Reuse

- A screenshot is evidence, not a fix.
- A green run on a nearby label does not validate the original failure.
- If the failure is intermittent, use similar-job history to set expectations.
- If a prerequisite build fails, say the push produced no test signal.
- Keep try-only stress code separate from the landing candidate.
- Cancel side jobs after taskgraph expansion, but preserve required dependency
  chains.
- The best evidence is a log counter that shows the old trigger happened while
  the fatal state did not.
