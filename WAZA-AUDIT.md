# Waza audit — current state and follow-ups

This file captures findings from running [microsoft/waza](https://github.com/microsoft/waza)
(an Agent Skills compliance and quality auditor) against every skill in this
repo. Treat it as a TODO list, not a finished document — re-run waza after
significant skill changes and update the notes here.

## Tooling

```bash
# Install (Mac/Linux, drops binary in ~/bin or /usr/local/bin)
curl -fsSL https://raw.githubusercontent.com/microsoft/waza/main/install.sh | bash

# Audit one skill
waza check skills/<name>

# Audit all 16 in this repo
for s in skills/*/; do waza check "$s"; done

# LLM-as-judge quality scoring (clarity, completeness, trigger precision,
# scope coverage, anti-patterns)
waza quality skills/<name>

# Generate eval scaffolding (eval.yaml + tasks)
waza suggest skills/<name>
```

## What's currently passing

After the description rewrite + `metadata.version: "1.0"` addition, every
skill passes:

- `spec-frontmatter` — structure valid, required fields present
- `spec-allowed-fields` — only spec-allowed keys
- `spec-name` — lowercase + hyphens, matches dir name
- `spec-dir-match`
- `spec-description` — under 1024 chars, intent-based
- `spec-security` — no risky tokens
- `spec-version` — `metadata.version` present (optimal)

Remaining warnings (consistent across all 16 skills):

- `spec-license` — no `license` field. Optional per the agentskills.io
  spec, but waza scores it as a warning. Not addressed in this PR
  because the repo doesn't have a top-level LICENSE file yet — that's
  a policy decision separate from skill format.

## The big remaining issue: token budget

Waza enforces a strict 500-token cap on `SKILL.md` body content. Every
skill exceeds it, with overages ranging from +108 (lando) to +2247
(worker-image-investigation):

| Skill | Body tokens | Over by |
|-------|-------------|---------|
| bigquery | 1090 | +590 |
| bugzilla | 655 | +155 |
| daily-log | 905 | +405 |
| jira | 949 | +449 |
| lando | 608 | +108 |
| os-integrations | 1599 | +1099 |
| papertrail | 1399 | +899 |
| redash | 858 | +358 |
| splunk | 2684 | +2184 |
| task-discovery | 932 | +432 |
| taskcluster | 1935 | +1435 |
| treeherder | 1875 | +1375 |
| win11-files | 1799 | +1299 |
| worker-image-build | 990 | +490 |
| worker-image-investigation | 2747 | +2247 |
| writing-skills | 2317 | +1817 |

Note: this 500-token cap is waza's opinion. The agentskills.io spec
itself recommends "<5000 tokens" for `SKILL.md`, and skill-creator
suggests "<500 lines". The strict 500-token cap is closer to
Perplexity's "Load" tier in their three-tier model. We're choosing
to track it as a goal even though it's tighter than the formal spec.

### Path to compliance

Move detail into `references/`. Every skill should keep in `SKILL.md`
only:

1. Description (already in frontmatter).
2. Prerequisites (env vars, tool installs).
3. Smallest-possible canonical example.
4. Workflow / decision tree (when to use which command).
5. `## Gotchas` (highest-value content per Perplexity).
6. Pointers into `references/<topic>.md` with one-line guidance.

Move into `references/`:
- Long command catalogs (e.g. taskcluster's full CLI usage).
- Multi-page workflows (e.g. worker-image-investigation's 7-step
  investigation procedure).
- Anything domain-specific that loads only when needed (Azure CLI
  blocks, KQL recipes, SQL examples).

### Priority order (by overage size and visibility)

1. **worker-image-investigation** (+2247) — largest. Split the 7-step
   investigation workflow + Azure VM commands + debug-VM creation
   into `references/{investigation-workflow.md, azure-commands.md,
   debug-vms.md}`.
2. **splunk** (+2184) — second largest. Move the canonical SPL recipe,
   `tstats` patterns, and field references into
   `references/{spl-recipes.md, azure-audit-fields.md}`. Body keeps
   the auth model + scope-vs table + workflow skeleton.
3. **writing-skills** (+1817) — meta. Move the `agentskills.io` spec
   echo and frontmatter rules into a reference; keep house-style
   opinions in the body.
4. **taskcluster** (+1435), **treeherder** (+1375), **win11-files**
   (+1299) — large CLI catalogs. Most of the body is `--flag`
   reference; that's references/-shaped content.
5. The rest — modest overages (<1100). Address opportunistically.

## Quality scoring (waza quality)

Not yet run. The LLM-as-judge needs an `OPENAI_API_KEY` (or local
LLM endpoint) per waza docs. Plan to run it once the token-budget
cleanup above lands so we're not getting flagged on issues we already
plan to fix.

## Eval format mismatch

This repo seeds eval files in skill-creator's format
(`evals/trigger-evals.json` — top-level array of `{query,
should_trigger}`). Waza expects `eval.yaml` with tasks and graders.

Both are fine — they answer different questions:

- skill-creator's evals optimize the *description* via
  `scripts/run_loop.py`.
- Waza's evals run task-level benchmarks (what the skill *does* once
  it loads), graded with text matching, code assertions, behavior
  constraints, or LLM-as-judge.

Plan to add `waza suggest`-generated `eval.yaml` files for the 5
high-overlap skills as a follow-up — they're complementary tests.

## Re-running this audit

```bash
for s in skills/*/; do waza check "$s" --format json > /tmp/waza-$(basename "$s").json; done
```

Update the table above with the new numbers when token-budget work
lands.
