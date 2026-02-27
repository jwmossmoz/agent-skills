---
name: sheriff-triage
description: >
  Comprehensive failure triage tool for sheriffs and image maintainers.
  Automatically determines if a failure is caused by code changes, image changes,
  or is a known intermittent. Combines data from Taskcluster, Treeherder, and
  worker image analysis. Triggers on "triage", "sheriff", "why did this fail",
  "is this an image regression", "failure analysis".
---

# Sheriff Triage

Comprehensive failure triage that automatically determines the likely cause of CI failures.

## Usage

```bash
cd /Users/jwmoss/github_moz/agent-skills/skills/sheriff-triage/scripts

# Full triage for a failing task
uv run triage.py <TASK_ID>

# Triage with Taskcluster URL
uv run triage.py https://firefox-ci-tc.services.mozilla.com/tasks/Xcac5C8gRqiOT13YsVRX8A

# JSON output for scripting
uv run triage.py <TASK_ID> --json

# Skip cross-branch search (faster)
uv run triage.py <TASK_ID> --skip-treeherder
```

## What It Does

The triage command performs a comprehensive analysis:

1. **Task Analysis**: Gets task info from Taskcluster (worker pool, status, labels)
2. **Image Comparison**: Compares alpha vs production image versions
3. **Cross-Branch Search**: Searches for similar failures on autoland/mozilla-central
4. **Classification Check**: Gets failure classification from Treeherder (if available)
5. **Verdict**: Determines the likely cause based on all signals

## Verdicts

| Verdict | Meaning | Evidence |
|---------|---------|----------|
| `CODE_REGRESSION` | Likely caused by code change | Same failure on production branches |
| `IMAGE_REGRESSION` | Likely caused by image change | Only fails on alpha, different image version |
| `INTERMITTENT` | Known flaky test | Classified as intermittent in Treeherder |
| `INFRA` | Infrastructure issue | Classified as infra in Treeherder |
| `NEEDS_INVESTIGATION` | Unclear cause | No strong signals either way |

## Example Output

```
## Triage Report: Xcac5C8gRqiOT13YsVRX8A

**Test**: mochitest-chrome-1proc
**Status**: failed

### Signals

| Signal | Value | Implication |
|--------|-------|-------------|
| Alpha Pool | Yes | Using new/staging image |
| Image Version Differs | Yes (1.0.9 vs 1.0.8) | Image change detected |
| Similar Failures on autoland | 0 | Not failing on production |
| Similar Failures on mozilla-central | 0 | Not failing on production |
| Treeherder Classification | not classified | No prior triage |

### Verdict: IMAGE_REGRESSION

**Confidence**: High
**Rationale**: Task failed on alpha pool with different image version than production,
and no similar failures found on production branches.

### Recommended Actions

1. Notify image maintainer
2. Check SBOM for image changes
3. Consider rolling back image
```

## Prerequisites

- `taskcluster` CLI: `brew install taskcluster`
- `uv` for running scripts
- Network access to Treeherder API

## Related Skills

- **treeherder**: Cross-branch failure search and classification lookup
- **worker-image-investigation**: Image version comparison and SBOM analysis
- **taskcluster**: Task status and logs
- **bugzilla**: File bugs for confirmed regressions

## References

- Mozilla Sheriffing Wiki: https://wiki.mozilla.org/Sheriffing
- Job Visibility Policy: https://wiki.mozilla.org/Sheriffing/Job_Visibility_Policy
- Test Disabling Policy: https://wiki.mozilla.org/Sheriffing/Test_Disabling_Policy
