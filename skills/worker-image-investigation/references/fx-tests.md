# Firefox test history with fx-tests

Use `fx-tests` before you decide that an XPCShell or Mochitest failure is new.
The tool reads nightly published Firefox CI history.

## Install

Node 20 or later is required.

```bash
npm install -g --allow-git=root github:mozilla/aretestsfastyet
```

npm 12 blocks Git dependencies by default. Keep `--allow-git=root`.

## Start with the guide

```bash
fx-tests guide
```

The guide explains supported harnesses, configurations, and data limits.

## Triage a try push

```bash
fx-tests try <TRY_REVISION> --perma-only
```

Use this command to identify tests with persistent failures in an image
validation push.

## Check one test

```bash
fx-tests test <TEST_PATH> --config windows11-64-25h2 --history --task-ids
```

Interpret the result as follows:

- A matching failure on the same configuration before the rollout is a
  pre-existing defect or intermittent candidate. The image can still make the
  failure repeatable.
- A failure that starts at the rollout boundary is an image-regression
  candidate. Continue with task and image comparison.
- No matching record means that the history is unknown. It does not prove that
  the failure is new.

`fx-tests` does not identify worker images or VM sizes. Use Taskcluster task
data and `investigate.py compare` for that attribution. Use **treeherder** for
WPT, GTest, and unsupported harnesses.

Project: <https://github.com/mozilla/aretestsfastyet#fx-tests-the-command-line-tool>
