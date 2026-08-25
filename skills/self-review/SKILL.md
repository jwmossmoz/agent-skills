---
name: self-review
description: >
  Use when drafting an evidence-based performance, promotion, H1, H2, or annual
  self-review from local notes and prior reviews. DO NOT USE FOR routine status.
metadata:
  version: "1.1"
---

# Self Review

Draft a review from verified evidence and preserve the user's established
voice.

## Prerequisites

The `moz` qmd collection must contain the relevant notes. Use the exact review
prompt and period.

## Usage

```bash
qmd query "performance review <period> outcomes" -c moz -n 20

uv run ~/.claude/skills/self-review/scripts/copy_rich_markdown.py \
  <review-directory>/performance-review-submission-final.md
```

Keep a detailed evidence draft and a shorter final paste version. Follow
[workflow.md](references/workflow.md) for prompt mapping and final checks.

## Gotchas

- Use prior reviews for voice, not as evidence for the current period.
- Verify numbers and current claims with their source.
- Do not run qmd update, embed, or collection commands unless asked.
- Plain `pbcopy` loses formatting; use the helper.
- Do not submit a review form unless the user explicitly asks.

## Related Skills

- Use **one-on-one** for routine manager updates.
- Use **daily-log** when source logs are missing.
