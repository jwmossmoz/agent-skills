---
name: skill-checker
description: Use when the user wants to validate, audit, or grade a Claude / agent skill against the agentskills.io spec. Runs three validators in one pass — microsoft/waza, agent-ecosystem/skill-validator, and thedaviddias/skill-check — and emits a unified scorecard. Trigger on phrases like "check this skill", "validate my skill", "audit a SKILL.md", "is this skill any good", "grade this skill", or any path containing a SKILL.md.
---

# skill-checker

Runs three independent agent-skill validators against a target skill directory and reports the consolidated verdict. Each validator inspects different things, so the **intersection** of complaints is the highest-confidence signal.

## When to use

The user points at a skill directory (something like `~/.claude/skills/<name>/` or a repo with a `SKILL.md` at its root) and asks for a check, validation, audit, score, or quality review.

## Do not use for

- Running an agent skill (that is the host's job)
- Authoring a brand-new skill from scratch (use `skill-creator` for that)
- Linting Markdown generally (use `markdownlint`)

## What each validator covers

| Validator | Strength | Weakness |
|---|---|---|
| [microsoft/waza](https://github.com/microsoft/waza) | Strictest. Spec compliance + token budget (default 500) + advisory checks (over-specificity, body structure, cross-model density) | Token cap is opinionated; can flag a fine skill as "Low" |
| [agent-ecosystem/skill-validator](https://github.com/agent-ecosystem/skill-validator) | Static analysis: link resolution, file hygiene, content density, cross-language contamination | "Contamination: medium" is often a false positive on multi-interface skills |
| [thedaviddias/skill-check](https://github.com/thedaviddias/skill-check) | DX: 0–100 quality score, deterministic `--fix`, security scan, GitHub Action | Most lenient — easy 100/100 |

Run all three. Treat any single tool's complaint as a hint; treat issues flagged by **two or more** as real problems to fix.

## How to run

```bash
scripts/check-skill.sh <skill-path>          # human-readable
scripts/check-skill.sh <skill-path> --json   # machine-readable
```

The script:

1. Lazily installs each validator if missing (`go install` for waza + skill-validator, `npx` for skill-check).
2. Runs all three, writing full output to `/tmp/skill-checker/<slug>/`.
3. Prints a one-line summary per validator and the cross-validator agreement.

Override the artifact dir with `SKILL_CHECKER_OUT=/some/path`.

## Reading the summary

```
waza:              compliance=Low tokens=1260/500 advisory_fails=1
skill-validator:   result=passed tokens=1,157 contamination=medium
skill-check:       score=100 / 100  Excellent status=PASS errors=0 warnings=0
```

- **compliance / status / score**: top-line verdict from each tool
- **tokens**: the SKILL.md body token count (waza compares to its own budget; skill-validator just reports)
- **advisory_fails**: count of waza advisory checks that failed (over-specificity, body structure, etc.)
- **contamination**: skill-validator's assessment of cross-language mixing in scripts/queries

## Common fixes (most-cited across validators)

If the summary shows trouble, these are the highest-leverage edits:

1. **Token budget over the limit** — extract long sections (query templates, full examples, schema reference) into `references/<topic>.md` and link with proper Markdown link syntax — square-bracketed label followed by parens around the relative path. Backtick-only paths trigger waza's "orphaned file" warning.
2. **Description too short / missing triggers** — start the description with "Use when..." and list trigger phrases the agent should match. Add a "Do not use for" clause to cut false positives.
3. **No examples section** — add `## Examples` with 2–4 short scenarios mapping user prompts to the action your skill should take. Waza checks for this explicitly.
4. **No troubleshooting / error handling** — add `## Troubleshooting` covering the failure modes you've hit (auth expired, rate limited, schema drift, empty results).
5. **Over-specificity** — strip absolute paths (`C:\Users\...`, `/home/me/...`) and hardcoded URLs with paths from instructions. Use placeholders or env vars.

## Artifacts

Full per-validator output lives at `/tmp/skill-checker/<skill-slug>/{waza,skill-validator,skill-check}.txt`. Read these when the summary line isn't enough — they contain the specific rule IDs and line numbers each tool flagged.

## Examples

**"Check the skill at ~/.claude/skills/foo"**
Run `scripts/check-skill.sh ~/.claude/skills/foo`. Show the three-line summary, then point out which checks failed across multiple validators.

**"Why is waza saying Low compliance?"**
Read `/tmp/skill-checker/<slug>/waza.txt` and look for the `❌` rows under "Issues found" and "Advisory Checks". Token budget and missing routing markers (`DO NOT USE FOR:`, `INVOKES:`) are the two most common.

**"Is this skill production-ready?"**
Production bar: skill-check ≥ 90, skill-validator passed, waza compliance Medium or better with 0 advisory fails. Token budget over the waza default (500) is acceptable if the body has clear progressive disclosure into `references/`.

## Troubleshooting

**`go: command not found`** — install Go (`brew install go`) or skip waza/skill-validator. The script will continue with whichever tools are available.

**`npx` hangs on first run** — first invocation downloads the skill-check package. Subsequent runs are fast (~1s).

**waza flags a `references/*.md` file as orphaned** — your SKILL.md references the file with backticks instead of a Markdown link. Change the backtick reference to a proper Markdown link.

**skill-validator reports "contamination: medium" but the skill is intentionally multi-interface (e.g., GraphQL + bash)** — false positive. Note it and move on.

**Validator versions differ from your last run** — `go install ...@latest` and `npx skill-check@latest` always pull the newest. Pin a version in the script if you need reproducible CI.
