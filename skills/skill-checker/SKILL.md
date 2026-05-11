---
name: skill-checker
description: "Use when validating, auditing, or grading an agent skill against agentskills.io conventions with waza, skill-validator, and skill-check. Trigger on check this skill, validate my skill, audit SKILL.md, grade this skill, or paths containing SKILL.md."
---

# skill-checker

Run three independent validators against a skill directory and summarize the results. Use agreement across validators as the strongest signal.

```bash
scripts/check-skill.sh <skill-path>
scripts/check-skill.sh <skill-path> --json
```

## USE FOR:

Skill validation, skill audits, quality reviews, readiness checks, and diagnosing checker output.

## DO NOT USE FOR:

Running a skill, writing a new skill from scratch, or general Markdown linting.

## Validators

- `waza`: strict spec, token budget, and advisory checks.
- `skill-validator`: file structure, links, references, density, and contamination.
- `skill-check`: 0-100 quality score plus security scan.

Treat one complaint as a hint. Treat the same issue from two or more validators as a fix candidate.

## Summary Fields

- `compliance`, `status`, `score`: top-level verdicts.
- `tokens`: SKILL.md body size.
- `advisory_fails`: failed waza advisory checks.
- `contamination`: skill-validator cross-language assessment.

## Examples

- "Check the skill at `~/.claude/skills/foo`": run the script, show the three summaries, then call out overlapping issues.
- "Why is waza saying Low compliance?": inspect the saved `waza.txt` report for issue rows.
- "Is this production-ready?": expect `skill-check` at least 90, `skill-validator` passed, and waza at Medium or better with no advisory failures.

## Troubleshooting

- Missing `go`: waza and skill-validator cannot install; rerun after Go is available.
- First `npx` run is slow: skill-check is being downloaded.
- Orphaned references: link reference files with Markdown links, not backtick-only paths.
- Multi-interface contamination can be false positive; note it when scripts intentionally mix interfaces.

Detailed interpretation notes live in [references/usage.md](references/usage.md). Implementation is [scripts/check-skill.sh](scripts/check-skill.sh).
