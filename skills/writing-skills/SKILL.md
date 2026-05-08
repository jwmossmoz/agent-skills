---
name: writing-skills
description: >
  House style for authoring and maintaining Mozilla CI agent-skills in
  this repo. Use when creating, editing, or reviewing a SKILL.md, the
  description frontmatter, references/, or scripts/ — covers description
  style, gotchas convention, scope-vs tables for log tools, hard-coded
  paths, and mozdata: handoffs.
---

# Writing Skills

House style for the skills in this repo. The agentskills.io spec covers the
mechanics (frontmatter fields, file layout); this guide is the *opinionated*
layer that comes from running these skills against real Mozilla CI work.

When in doubt, reach for `/skill-creator` — it covers the eval loop
(`scripts/run_loop.py`) which this guide deliberately does not duplicate.

## Description style

The description is a routing trigger, not documentation. It's loaded into
every session, so every word costs the user every time. Aim for ≤50 words.

**Required shape:**

1. One sentence on *what* the skill does and *what tool* it wraps. Be
   concrete — "via paperctl v2.0", "using the bq CLI", "via
   browser-harness against an authenticated Chrome tab" — not "queries
   logs" or "uses the API".
2. One sentence on *when to load* it. Phrase as user intent, not
   keywords.
3. If the skill overlaps with another skill in this repo (or with an
   external tool like `tc-logview`), one sentence starting with **DO NOT
   USE FOR** that names the alternative. Negative routing matters more
   than positive routing — adjacent skills that share keywords will
   mistrigger without it.

**Forbidden patterns:**

- `Triggers on "x", "y", "z"...` keyword bags. They look helpful and
  are not. Keywords belong in the description prose if they're load-
  bearing, otherwise they're noise.
- "Use when the user says: ..." with quoted phrases. Same problem.
- Multiple paragraphs. One block, ≤50 words, ≤300 characters.

**Example — bad:**

```yaml
description: >
  Query logs from SolarWinds (formerly Papertrail) using paperctl.
  Use when: (1) downloading logs (2) searching log entries
  (3) investigating CI failures. Triggers: "papertrail", "pull logs",
  "worker logs", "download logs", "search logs"
```

**Example — good:**

```yaml
description: >
  Query and download in-VM Taskcluster worker logs from SolarWinds
  Observability (formerly Papertrail) using paperctl v2.0. Use when
  investigating what a worker process or its OS reported on-host. DO NOT
  USE FOR provisioning failures where no worker started (use tc-logview)
  or Azure-side VM lifecycle events (use splunk).
```

## Required sections in SKILL.md body

Every skill's `SKILL.md` must include:

- **Prerequisites** — Tools, env vars, auth setup. Be explicit ("requires
  `BUGZILLA_API_KEY` env var; read-only ops work without auth").
- **Usage** — At least one runnable example. Use full installed paths:
  `~/.claude/skills/<skill-name>/scripts/<script>.py`. Never hardcode
  `~/github_moz/agent-skills/...` — that breaks for anyone else and
  breaks if the checkout moves.
- **Gotchas** — Failure modes, surprises, things that bit you once. This
  is the *highest-value* section. Even one bullet beats none. See below.
- **Related Skills** (when applicable) — Cross-references to adjacent
  skills with one-line "use X when Y" pointers. The disambiguation in
  the description is the routing layer; this is the human-readable
  expansion.

Optional but encouraged:

- **References** — Pointers into `references/` for detail that doesn't
  need to be in the always-loaded body.
- **Scope vs. <other tool>** table or blockquote — see "Log tools" below.

## Gotchas: what goes there

A gotcha is something that would surprise a reader who knows the tool
but doesn't know this skill's quirks. Examples that earned their place:

- "Never use `taskcluster task retrigger` for Firefox CI — it clears
  upstream dependencies." (taskcluster)
- "VM names must be ≤ 15 chars (Windows NetBIOS limit)."
  (worker-image-investigation)
- "`treeherder-cli --similar-history` takes a job ID (numeric), not a
  task ID." (treeherder, worker-image-investigation)
- "Some Windows SBOM artifacts are UTF-16LE encoded — pipe through
  iconv." (worker-image-investigation)

Each gotcha should be checkable: a future reader could verify it, or it
points at a specific symptom and remedy. Don't put generic best-
practice advice here ("always test your queries"); that's noise.

## Log tools — Scope-vs tables are mandatory

Mozilla has four overlapping log surfaces, and they're easy to confuse:

| Tool | Scope | Source |
|---|---|---|
| `splunk` skill | Azure activity log — control-plane events for VMs/disks/NICs | `index=azure_audit` |
| `papertrail` skill | In-VM events from the running worker | SolarWinds Observability |
| `tc-logview` (CLI, not a skill) | Taskcluster's worker-manager + worker-scanner views | GCP Cloud Logging |
| `taskcluster` skill | Live task logs and artifacts | Taskcluster API |

Any skill that touches one of these surfaces must include a similar
table in its body so readers (and agents) understand the boundary.
Without it, an agent will pick the wrong tool and waste a turn.

## Hard-coded paths

Don't reference `/Users/jwmoss/...` or `~/github_moz/...` anywhere in
SKILL.md or scripts. Use either:

- `~/.claude/skills/<skill-name>/scripts/<script>` — the symlinked
  install path (Claude Code reads from `~/.claude/skills/`).
- A local variable scoped to the doc:
  ```bash
  TC=~/.claude/skills/taskcluster/scripts/tc.py
  ```

`~/.agents/skills/` is the canonical install location (`npx skills`
manages it); `~/.claude/skills/` is the symlinked view. SKILL.md
should reference the symlinked view because that's where Claude Code
runtime resolves paths.

## mozdata: handoffs

When telemetry-adjacent skills (bigquery, redash, daily-log) need to
find probes or write production-quality SQL, hand off to the
`mozdata:` plugin skills rather than duplicating their content:

- `mozdata:probe-discovery` — find Glean metrics and probes
- `mozdata:query-writing` — production-quality BigQuery SQL
- `mozdata:airflow-debugging` — DAG failures

Reference them in `## Related Skills`, not the description. They live
in a separate plugin and shouldn't be assumed to exist; describe them
as "if available" when they're optional.

## Progressive disclosure

`SKILL.md` is loaded in full whenever the skill triggers. Keep it
under 500 lines. When you exceed that, split into `references/`:

- `references/REFERENCE.md` — long-form technical reference
- `references/<topic>.md` — domain-specific (e.g. `tc-logview.md`,
  `azure-commands.md`, `presets.yml`)

Link from the body with one-line guidance: *"See `references/x.md`
when you need <X>."* Don't make the reader hunt for context.

For skills with multiple variants (e.g. multi-cloud, multi-OS),
organize references by variant:

```
worker-image-build/
├── SKILL.md (workflow + which config picks which variant)
└── references/
    ├── azure-trusted.md
    ├── azure-untrusted.md
    └── examples.md
```

Skill body picks the variant; the agent only reads the relevant
reference file.

## Frontmatter

Required fields per the agentskills.io spec:

- `name` — lowercase letters, numbers, hyphens. Must match the parent
  directory name. ≤ 64 chars.
- `description` — see "Description style" above. ≤ 1024 chars (hard
  limit), ≤ 50 words (this repo's soft cap).

Optional and worth using:

- `metadata.version` — bump on substantive changes. Helps diffs.
- `metadata.author` — for skills authored by someone other than the
  repo owner.

Avoid non-spec fields (`when_to_use`, `argument-hint` outside `metadata`,
custom keys at root). They're silently ignored by some hosts and trip
spec validators.

## Evals

Every substantive skill should ship `evals/evals.json` with a mix of
positive and negative trigger cases. The negatives matter more — they
catch over-triggering, which is the more common failure mode for
keyword-heavy skills.

`/skill-creator` covers the full eval loop and the `scripts/run_loop.py`
description optimizer. Don't reinvent that here. Minimum viable:

```json
{
  "skill_name": "<name>",
  "evals": [
    {"id": 1, "prompt": "...", "should_trigger": true},
    {"id": 2, "prompt": "...", "should_trigger": false}
  ]
}
```

Aim for 8-10 positive + 8-10 negative near-misses. Generic queries
("write a fibonacci function" as a negative for a PDF skill) don't
test anything; the valuable negatives are queries that share
vocabulary with the skill but actually need a different tool.

## When in doubt

Ask the same question on every paragraph: *would the agent get this
wrong without this content?* If no, cut it.

## Checklist

Before merging a skill change:

- [ ] Description is ≤ 50 words, intent-based, no `Triggers on` lists.
- [ ] Description names alternative skills with `DO NOT USE FOR` if
      there's overlap.
- [ ] No hardcoded `/Users/` or `~/github_moz/` paths.
- [ ] `## Gotchas` section exists with at least one bullet (or is
      labeled "no known gotchas yet — please add as they come up").
- [ ] References split out when SKILL.md > 500 lines.
- [ ] `evals/evals.json` exists for skills shipping to multiple users.
- [ ] Frontmatter uses only spec fields plus `metadata.*`.
- [ ] README skill list (top-level repo README) updated for
      added/removed skills.
