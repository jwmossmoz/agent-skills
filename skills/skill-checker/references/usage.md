# skill-checker Usage Notes

## Common Fixes

Token budget over the limit:

- Move long examples, query templates, schema details, or procedures into `references/`.
- Link those files from `SKILL.md` with normal Markdown links.

Description warnings:

- Start with "Use when".
- Include trigger phrases.
- Add a "Do not use for" section when false positives are likely.

Missing examples or troubleshooting:

- Add 2-4 short examples that map user requests to actions.
- Add common failure modes such as auth expiry, missing tools, stale data, or rate limits.

Over-specificity:

- Replace personal paths and hardcoded environment details with placeholders.
- Keep URLs only when they are stable documentation or service roots.

## Artifacts

Reports are written under `${SKILL_CHECKER_OUT:-/tmp/skill-checker}/<skill-slug>/`:

- `waza.txt`
- `skill-validator.txt`
- `skill-check.txt`

Use those files when the one-line summary is not enough.
