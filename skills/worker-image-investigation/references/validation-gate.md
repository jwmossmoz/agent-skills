# Baseline-aware image validation

Before treating a candidate failure as an image blocker, check today's
equivalent tasks on autoland, mozilla-central, or another existing pool.
Compare the test, platform, build, and configuration where possible, and read
the full task logs.

- A matching failure signature already present in the baseline is shared
  noise, including Tier 1, and does not block the candidate change.
- Only candidate failures whose equivalent tests pass elsewhere are image
  blockers. A version difference alone does not establish the root cause.
- Match individual tests and error signatures, not just two red job results.
  A baseline job failing an unrelated test does not explain the candidate's
  failure.
- Missing history and pending or running baseline jobs are inconclusive.
  Obtain completed equivalent results rather than assuming a pass or failure.
- Passing retries can hide an earlier hang or harness bookkeeping failure.
  Link the baseline task and the matching log evidence, not only final test
  pass counts.

Do not require every Tier 1 job to be green, invent a failure-frequency gate,
or keep investigating a shared failure as a candidate-only image regression.
Report shared baseline failures separately from candidate-only regressions.
