---
name: skill-checker
description: "Use when validating, auditing, grading, or checking an agent skill, SKILL.md, validator report, eval coverage, or production-readiness claim against agentskills.io and repo conventions. Checks spec, style, links, references, and eval evidence. DO NOT USE FOR creating or iterating skills; use skill-creator."
---

# skill-checker

Audit a skill directory with validators and eval-artifact inventory. Eval evidence is advisory; use `skill-creator` for the actual eval loop.

```bash
~/.claude/skills/skill-checker/scripts/check-skill.sh <skill-path> [--json]
```

## USE FOR:

Skill validation, quality audits, readiness checks, and diagnosing checker output.

## DO NOT USE FOR:

Running evals, creating or iterating skills, or Markdown linting.

## Checks

- `skills-ref`: hard spec.
- `waza`: token budget/advisories.
- `skill-validator`: structure, links, density, contamination.
- `skill-check`: quality/security.
- `eval-evidence`: detects `evals/evals.json`, trigger-loop files, `eval.yaml`, and sibling benchmark workspaces.

Treat one complaint as a hint. Treat the same issue from two or more validators as a fix candidate.

## Examples

- "Check `skills/taskcluster`": run the script and summarize overlapping issues.
- "Is this production-ready?": require validator health plus eval evidence.

## Readiness

For production-ready substantive skills, expect hard validators to pass, accepted warnings explained, waza Medium or better, and `evals/evals.json` plus trigger-loop results or benchmark evidence.

## Troubleshooting / Gotchas

- Validator versions drift; distrust a single-tool regression unless `skills-ref` also flips.
- `skill-validator` may warn that `evals/` is unknown. This repo intentionally keeps eval files there.
- The checker reports missing or weak eval evidence, but it never spawns runs, grades assertions, aggregates benchmarks, or launches the viewer.

Detailed interpretation notes and validator-finding → spec-rule mapping live in [references/usage.md](references/usage.md). Read [references/waza.md](references/waza.md) for waza-specific workflows and `WAZA-AUDIT.md` guidance. Implementation is [scripts/check-skill.sh](scripts/check-skill.sh).
