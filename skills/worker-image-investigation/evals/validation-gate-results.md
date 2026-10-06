# Baseline-aware validation gate smoke test

Checked on 2026-10-06 after replacing the all-green Tier 1 gate.

A tools-disabled Claude Haiku run received the updated skill, its linked
validation gate, and the four prompts in `evals.json`, without their expected
answers. All four returned the
expected disposition:

| Case | Disposition |
| --- | --- |
| Matching failure on today's autoland; central has a pass | Shared baseline; not an image blocker |
| Candidate failure against passing equivalent tests | Candidate blocker |
| Both jobs red, but different tests/signatures | Different signature; not shared baseline evidence |
| Equivalent jobs pending and test history missing | Inconclusive |

This is a four-case policy smoke test, not a statistical benchmark or evidence
that a particular image is safe to deploy.

`check-skill.sh` passed the hard skills-ref checks for worker-image-investigation,
os-integrations, and worker-image-build. Skill-check passed all three with no
errors or warnings. Skill-validator passed os-integrations and worker-image-build;
worker-image-investigation retained three advisory warnings.
Waza reported Low compliance for all three with one advisory each; all entry
files are within its 500-token budget (investigation 498, os-integrations 481,
worker-image-build 451). These remaining advisory findings are not claimed to
be fixed by this narrowly scoped policy correction. The change adds
four task eval prompts; it does not add a full benchmark or task eval suites for
the other two skills.
