# skill-checker Usage Notes

## Mapping validator output to the agentskills.io spec

Each complaint below is keyed back to the spec section it implements. When two validators flag the same underlying issue, the cited spec section is the source of truth.

| Validator output | Spec rule | Reference |
| --- | --- | --- |
| `skills-ref`: `Validation error: name` | `name` is 1–64 lowercase `a-z0-9-`, no leading/trailing/consecutive hyphens, must match parent directory. | [/specification#name-field](https://agentskills.io/specification#name-field) |
| `skills-ref`: `Validation error: description` | `description` is 1–1024 characters, non-empty. | [/specification#description-field](https://agentskills.io/specification#description-field) |
| `skills-ref`: `Validation error: compatibility` | `compatibility`, if present, is 1–500 characters. | [/specification#compatibility-field](https://agentskills.io/specification#compatibility-field) |
| `waza`: `Token Budget … Exceeds limit by …` | `SKILL.md` body should stay under ~5000 tokens / 500 lines. Move bulk to `references/`. | [/specification#progressive-disclosure](https://agentskills.io/specification#progressive-disclosure) |
| `waza`: advisory `[gotchas]` or `[examples]` failure | Spec patterns: Gotchas sections, worked examples, validation loops are high-value. | [/skill-creation/best-practices](https://agentskills.io/skill-creation/best-practices) |
| `waza`: advisory `[description-imperative]` | Descriptions should use imperative phrasing ("Use when …") and list explicit triggers. | [/skill-creation/optimizing-descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) |
| `skill-validator`: `Result: failed` with orphaned reference | Link `references/*.md` files from `SKILL.md` with Markdown links, not backtick-only paths. | [/specification#file-references](https://agentskills.io/specification#file-references) |
| `skill-validator`: `Contamination level: …` | Multiple competing tool interfaces in one skill. Sometimes a false positive when scripts intentionally mix. | [/skill-creation/best-practices#design-coherent-units](https://agentskills.io/skill-creation/best-practices#design-coherent-units) |
| `skill-check`: errors > 0 | Mix of spec violations and npm-side security/style heuristics. Cross-check against `skills-ref` before treating as authoritative. | n/a (npm package) |

## Common fixes

Token budget over the limit:

- Move long examples, query templates, schema details, or procedures into `references/`.
- Link those files from `SKILL.md` with standard Markdown links so `skill-validator` does not mark them orphaned.
- Tell the agent *when* to load each reference file rather than a generic "see references/".

Description warnings:

- Start with "Use when".
- Include trigger phrases real users would type.
- Add a "Do not use for" section when adjacent skills could false-trigger.
- Stay under 1024 characters.

Missing examples or troubleshooting:

- Add 2–4 short examples that map user requests to actions.
- Add a Gotchas section with concrete, non-obvious environment facts.

Over-specificity:

- Replace personal paths and hardcoded environment details with placeholders.
- Keep URLs only when they are stable documentation or service roots.

## Artifacts

Reports are written under `${SKILL_CHECKER_OUT:-/tmp/skill-checker}/<skill-slug>/`:

- `skills-ref.txt`
- `waza.txt`
- `skill-validator.txt`
- `skill-check.txt`

Use those files when the one-line summary is not enough.

## Setup gotchas

- Missing `go`: `waza` and `skill-validator` cannot install. Re-run after `go install` is available.
- Missing `uv`: `skills-ref` cannot run. Install with `brew install uv` or follow [uv docs](https://docs.astral.sh/uv/).
- First `npx` run is slow: `skill-check` is downloading.
- `skill-validator` "multi-interface contamination" can be a false positive when a skill intentionally bundles CLI plus library scripts; note it rather than blindly fixing.
