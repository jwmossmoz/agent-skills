# Repository Guidelines

## Project Structure

- `skills/` contains the maintained skills. Each is self-contained and may include references, scripts, or evals.
- `README.md` documents the collection and installation.
- `CLAUDE.md` points to this file.

## Skill Authoring

- Every `SKILL.md` starts with YAML frontmatter, and `name` matches its directory.
- Treat the description as a routing rule. Start with `Use when`, keep it below 50 words, and name the user's intent and tool. Add `DO NOT USE FOR` when a realistic overlap needs a boundary.
- Aim for at most 500 tokens in the body. Keep routing, prerequisites, one runnable path, decisions, and verified gotchas. Put longer details in linked references.
- Include `Prerequisites`, `Usage`, and `Gotchas` sections. Add `Related Skills` when another skill is a realistic alternative.
- Do not hard-code a user's checkout path. Use `~/.claude/skills/<name>/...` in examples.
- Prefer one reusable script over repeated inline procedures. Do not add dependencies when the standard library or an existing helper is enough.
- Preserve real commands and behaviors seen in session evidence.

## Style and Validation

- Use four spaces in Python and keep scripts under the skill's `scripts/` directory.
- Use `uv`/`uvx` for isolated Python dependencies. Keep real configuration out of git; provide `.example` files when needed.
- There is no global build step or test suite. Run the changed skill's examples and check its frontmatter, links, and commands. Keep evals and trigger evidence under that skill's `evals/` directory.

## Commits and Pull Requests

Use a conventional commit with an imperative summary. Keep the PR description short and in simple English, with a one-sentence summary, validation, and any important notes or setup.
