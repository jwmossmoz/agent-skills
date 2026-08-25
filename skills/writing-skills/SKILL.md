---
name: writing-skills
description: >
  Use when editing or reviewing Mozilla CI skill frontmatter, SKILL.md files,
  references, scripts, or evals in this repository according to its house
  rules.
metadata:
  version: "1.1"
---

# Writing Skills

Use the nearest repository `AGENTS.md` as the source of truth. It contains the
house rules because contributors need them before any skill triggers.

## Prerequisites

Read `AGENTS.md`, the complete target `SKILL.md`, and each referenced file that
the change affects. Use **skill-creator** for the edit and evaluation loop.

## Usage

```bash
~/.claude/skills/skill-checker/scripts/check-skill.sh skills/<skill-name>
```

Keep the entry file focused on routing, one runnable path, decisions, and
gotchas. Put detailed command catalogs and variant procedures in references.

## Gotchas

- Preserve real commands and behaviors seen in session evidence.
- Do not use keyword bags in descriptions.
- Do not hard-code a user's checkout path.
- A log skill needs a scope table that distinguishes guest, Taskcluster, Azure,
  and task logs.
- Treat one validator warning as a hint. Fix an issue when independent checks
  agree or the repository rule is explicit.

## Related Skills

- Use **skill-creator** to create or improve a skill and its evals.
- Use **skill-checker** after each change group and before handoff.
