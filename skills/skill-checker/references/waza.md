# Waza Usage

Use this reference when interpreting waza output, deciding whether a waza finding should block a skill, or deciding what to do with a repo-level waza audit note.

## Role in this repo

Waza is useful, but it is one signal. Prefer `skill-checker` as the front door because it combines waza with the official validator, `skill-validator`, `skill-check`, and eval-evidence inventory.

```bash
~/.claude/skills/skill-checker/scripts/check-skill.sh skills/<skill-name>
waza check skills/<skill-name>
```

Treat these waza findings as strong signals:

- Spec failures: invalid frontmatter, name mismatch, bad links.
- Token pressure: `SKILL.md` is carrying reference-shaped detail.
- Missing waza eval suite: no `eval.yaml`/`eval.yml` where waza expects one.
- Repeated body-structure advisories: missing examples, gotchas, or usage clarity.

Treat these as contextual, not absolute:

- The 500-token `SKILL.md` limit. It is useful pressure, but tighter than the agentskills.io guidance and the Anthropic skill-creator guidance.
- `Evaluation Suite: Not Found` when the skill has `evals/evals.json`, trigger-loop results, or benchmark workspaces. Waza only understands its own `eval.yaml` format.
- `unknown directory: evals/` from `skill-validator`. This repo intentionally stores skill-creator eval artifacts under `evals/`.

## WAZA-AUDIT.md

`WAZA-AUDIT.md` is not operationally required. It is a historical audit snapshot and TODO list. If it is kept, treat it as time-stamped notes that must be refreshed after meaningful skill changes. If it is not actively maintained, remove it or move it to an audit archive such as `docs/audits/waza-YYYY-MM.md`.

Prefer fresh command output over the audit file:

```bash
waza check skills/<skill-name>
waza coverage . -f markdown
```

## Effective workflows

Before editing a skill:

```bash
waza check skills/<skill-name>
waza tokens profile skills/<skill-name>
waza tokens suggest skills/<skill-name>
```

Use token output to decide what belongs in `SKILL.md` versus `references/`. Move command catalogs, long workflows, schema details, and one-off examples into references.

For repo-wide hygiene:

```bash
waza coverage . -f markdown
for s in skills/*/; do waza check "$s" --format json > "/tmp/waza-$(basename "$s").json"; done
```

For waza-native evals:

```bash
waza new eval <skill-name>
waza run <path-to-eval.yaml> --baseline --output-dir /tmp/waza-results
```

Review generated evals before committing them. Waza evals are complementary to `skill-creator` evals: waza checks task behavior through `eval.yaml`; skill-creator evals check trigger quality and with-skill versus baseline behavior through `evals/evals.json`, loop results, and benchmark workspaces.

## Copilot-dependent commands

These commands require Copilot authentication and a usable `copilot` executable in `PATH`:

```bash
waza quality skills/<skill-name>
waza suggest skills/<skill-name>
waza dev skills/<skill-name> --copilot
```

If they fail with `copilot failed to start`, use non-Copilot commands or fix the local Copilot CLI/auth setup first.
