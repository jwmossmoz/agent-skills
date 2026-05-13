---
name: skill-checker
description: "Use when validating, auditing, or grading an agent skill against the agentskills.io spec and best practices. Trigger on check this skill, validate my skill, audit SKILL.md, grade this skill, or paths containing SKILL.md."
---

# skill-checker

Run four independent validators against a skill directory and summarize the results. Use agreement across validators as the strongest signal.

```bash
scripts/check-skill.sh <skill-path>
scripts/check-skill.sh <skill-path> --json
scripts/check-skill.sh --help
```

## USE FOR:

Skill validation, skill audits, quality reviews, readiness checks, and diagnosing checker output.

## DO NOT USE FOR:

Running a skill, writing a new skill from scratch, or general Markdown linting.

## Validators

- `skills-ref`: official reference validator from `agentskills/agentskills`. Hard spec rules — frontmatter, name format, description length.
- `waza`: strict spec, token budget, and advisory checks.
- `skill-validator`: file structure, links, references, density, and contamination.
- `skill-check`: 0-100 quality score plus security scan.

Treat one complaint as a hint. Treat the same issue from two or more validators as a fix candidate.

## Summary Fields

- `result` (skills-ref): `passed` means frontmatter conforms to the spec; `failed` means a hard rule is violated.
- `compliance`, `status`, `score`: top-level verdicts from waza / skill-validator / skill-check.
- `tokens`: SKILL.md body size — spec recommends < 5000.
- `advisory_fails`: failed waza advisory checks.
- `contamination`: skill-validator cross-language assessment.

## Examples

- "Check the skill at `~/.claude/skills/foo`": run the script, show the four summaries, then call out overlapping issues.
- "Why is waza saying Low compliance?": inspect the saved `waza.txt` report for issue rows.
- "Is this production-ready?": expect `skills-ref` passed, `skill-check` at least 90, `skill-validator` passed, and waza at Medium or better with no advisory failures.

## Gotchas

- `skills-ref`, `waza`, `skill-validator`, and `skill-check` are all pulled from `@latest` on first install. Verdicts can drift between runs — distrust a single-validator regression unless `skills-ref` also flips.
- `skills-ref` is fetched via `uvx` from the `agentskills/agentskills` git repo (subdirectory `skills-ref`). First run clones and builds; subsequent runs hit the uvx cache.
- `skills-ref passed` and `skill-validator Result: passed` mean different things. `skills-ref` is hard spec rules (`name`, `description` length, parent-dir match). `skill-validator` is style and density. A skill can fail one and pass the other.
- waza counts the YAML frontmatter against the SKILL.md token budget — large `compatibility` strings and `allowed-tools` lists chew into the < 5000 token recommendation.
- The script removes stale `.skill-check.*.txt` files from the skill directory each run — older `skill-check` versions wrote artifacts in-place rather than to `/tmp`.

Detailed interpretation notes and validator-finding → spec-rule mapping live in [references/usage.md](references/usage.md). Implementation is [scripts/check-skill.sh](scripts/check-skill.sh).
