# Repository Guidelines

## Project Structure & Module Organization

- `skills/` contains each skill as a self-contained module (for example, `skills/bugzilla/`, `skills/taskcluster/`).
- Each skill typically includes `SKILL.md` (documentation + metadata), `scripts/` (implementation), and optional `references/` or `assets/`.
- `agents/` holds custom subagent definitions used by agent frameworks.
- Top-level docs live in `README.md` and `AGENTS.md`. `CLAUDE.md`, when present, should only include `@AGENTS.md`.

## Jira

Use the Atlassian MCP for Jira work. This repository does not provide a Jira skill.

## Build, Test, and Development Commands

There is no global build step; skills are executed directly.

- Run a Python-based skill: `uv run skills/bugzilla/scripts/bz.py search --quicksearch "crash"`
- Run a script from its directory: `cd skills/taskcluster/scripts && uv run tc.py --help`
- Run a tool via `uvx` (zero-install): `uvx --from lando-cli lando check-job <job_id>`

`uv` is the standard runner for Python dependencies; `uv.lock` files are committed for reproducibility.

## Coding Style & Naming Conventions

- Use 4-space indentation for Python.
- Keep scripts and modules in `skills/<skill-name>/scripts/` with descriptive, lowercase, snake_case filenames.
- Skill directories are lowercase with hyphens (for example, `skills/os-integrations/`).
- Every `SKILL.md` must start with YAML frontmatter; `name` must match the folder name.
- Prefer `.example` config files and keep real configs out of git.

## Testing Guidelines

There is no automated test suite today. Validate changes by running the relevant script with real or read-only operations:

- `uv run skills/taskcluster/scripts/tc.py --help`
- `uv run skills/treeherder/scripts/query.py --revision <hash> --repo try`

## Commit & Pull Request Guidelines

- Keep commits focused and use concise, imperative messages (for example, “Add Taskcluster status command”).
- Include a short summary of changes, testing performed, and any required setup (env vars, config files).
- Link issues when applicable and add screenshots only if output formatting changes.

## Skill Authoring Notes

- Treat the description as a routing rule. Start it with `Use when`, keep it
  between 150 and 300 characters when practical, and stay below 50 words.
- Name the wrapped tool and the user's intent. Add `DO NOT USE FOR` with the
  alternative when two skills overlap. Do not add trigger keyword lists.
- Aim for at most 500 tokens in the `SKILL.md` body. Keep only routing,
  prerequisites, one runnable path, decisions, and verified gotchas there.
- Put command catalogs, API details, and variant procedures in `references/`.
  Link each reference from `SKILL.md` and state when to read it.
- Include `## Prerequisites`, `## Usage`, and `## Gotchas`. Add
  `## Related Skills` when another skill is a realistic alternative.
- A log skill must include a scope table that distinguishes Taskcluster service
  logs, worker guest logs, Azure control-plane logs, and task logs.
- Use `~/.claude/skills/<name>/...` in examples. Do not use `/Users/<name>` or a
  local checkout path.
- Prefer one reusable script over repeated inline procedures. Do not add a
  dependency when the standard library or an existing helper is sufficient.
- Keep task evals and trigger evidence under `evals/`. Use `skill-creator` for
  changes and eval work. Run `skill-checker` after each change group and before
  handoff.
- Treat one validator complaint as a hint. Treat the same issue from two or
  more validators as a fix candidate. Document accepted tool disagreements.
