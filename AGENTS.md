# Repository Guidelines

## Project Structure & Module Organization

- `skills/` contains each skill as a self-contained module (for example, `skills/bugzilla/`, `skills/jira/`).
- Each skill typically includes `SKILL.md` (documentation + metadata), `scripts/` (implementation), and optional `references/` or `assets/`.
- `agents/` holds custom subagent definitions used by agent frameworks.
- Top-level docs live in `README.md`, `CLAUDE.md`, and templates like `SKILL_TEMPLATE.md`.

## Build, Test, and Development Commands

There is no global build step; skills are executed directly.

- Run a Python-based skill: `uv run skills/bugzilla/scripts/bz.py search --quicksearch "crash"`
- Run a script from its directory: `cd skills/jira/scripts && uv run extract_jira.py --help`
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

- Keep commits focused and use concise, imperative messages (for example, “Add JIRA export flag”).
- Include a short summary of changes, testing performed, and any required setup (env vars, config files).
- Link issues when applicable and add screenshots only if output formatting changes.

## Skill Authoring Notes

- Keep `SKILL.md` concise and move long procedures into `references/`.
- Use relative paths when linking between skill files.
- Prefer reusable scripts in `scripts/` over large inline code blocks in docs.
