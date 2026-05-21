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
| `skill-validator`: `unknown directory: evals/` | Repo-local convention: eval artifacts live under `evals/` even though it is not a standard skill resource directory. Treat as an accepted warning unless the host starts rejecting the skill. | repo `writing-skills` eval guidance |
| `skill-validator`: `Contamination level: …` | Multiple competing tool interfaces in one skill. Sometimes a false positive when scripts intentionally mix. | [/skill-creation/best-practices#design-coherent-units](https://agentskills.io/skill-creation/best-practices#design-coherent-units) |
| `skill-check`: errors > 0 | Mix of spec violations and npm-side security/style heuristics. Cross-check against `skills-ref` before treating as authoritative. | n/a (npm package) |
| `eval-evidence`: `coverage=missing` or `coverage=basic` | The skill has little or no evidence that it improves behavior once loaded. Validators passing is necessary, not sufficient, for release readiness. | [Anthropic skill-creator eval loop](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md#running-and-evaluating-test-cases) |

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

Missing or weak eval evidence:

- Add `evals/evals.json` with realistic prompts. For routing-heavy skills, include positive cases and near-miss negatives.
- If tuning the description, add `evals/trigger-evals.json` and preserve `evals/loop-results.json` or `loop-results.md`.
- If checking task behavior after a skill loads, use `skill-creator` to run with-skill and baseline runs into `<skill-name>-workspace/iteration-N/`, then keep `benchmark.json`.
- If using waza's task-level evals, add root-level `eval.yaml` or `eval.yml`.

Over-specificity:

- Replace personal paths and hardcoded environment details with placeholders.
- Keep URLs only when they are stable documentation or service roots.

## Eval evidence levels

The checker inventories eval artifacts; it does not execute them.

| Coverage | Meaning | Typical next step |
| --- | --- | --- |
| `missing` | No recognized eval artifacts found. | Add `evals/evals.json` before calling the skill release-ready. |
| `basic` | Prompts or waza evals exist, but no saved run results. | Run the relevant eval loop and preserve results. |
| `trigger-loop` | Description-trigger evals and loop results exist. | Good for routing changes; still consider task benchmarks for behavior-heavy skills. |
| `benchmark` | A sibling `<skill-name>-workspace/iteration-*/benchmark.json` exists. | Review benchmark deltas and user feedback before claiming readiness. |

For full Anthropic-style task evals, the expected flow is: create realistic prompts, spawn with-skill and baseline runs in the same turn, draft objective assertions while runs are in progress, capture timing as each run completes, grade outputs, aggregate `benchmark.json`, launch the review viewer, and iterate from user feedback. Keep that orchestration in `skill-creator`; `skill-checker` should only report whether the artifacts exist.

## Artifacts

Reports are written under `${SKILL_CHECKER_OUT:-/tmp/skill-checker}/<skill-slug>/`:

- `skills-ref.txt`
- `waza.txt`
- `skill-validator.txt`
- `skill-check.txt`
- `eval-evidence.txt`

Use those files when the one-line summary is not enough.

## Setup gotchas

- Missing `go`: `waza` and `skill-validator` cannot install. Re-run after `go install` is available.
- Missing `uv`: `skills-ref` cannot run. Install with `brew install uv` or follow [uv docs](https://docs.astral.sh/uv/).
- First `npx` run is slow: `skill-check` is downloading.
- `skill-validator` "multi-interface contamination" can be a false positive when a skill intentionally bundles CLI plus library scripts; note it rather than blindly fixing.
