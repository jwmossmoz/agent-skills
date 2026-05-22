---
name: self-review
description: >
  Use when creating performance self-reviews from local notes, prior reviews,
  review prompts, and verified evidence. Helps draft H1/H2, annual, and
  promotion self evaluations, example answers, and rich review-form paste output.
  Do not use for routine status or 1:1 summaries; use one-on-one.
metadata:
  version: "1.0"
---

# Self Review

Create evidence-backed performance self-reviews and rich review-form paste output.

## USE FOR:

- Drafting H1/H2, annual, or promotion self reviews from notes.
- Turning review prompts into concise example answers.
- Rewriting a draft in the user's existing voice.
- Preparing Markdown as rich clipboard content.

## DO NOT USE FOR:

- Routine 1:1 or status summaries; use `one-on-one`.
- Generating raw daily logs; use `daily-log`.
- Submitting review forms unless explicitly asked.

## Workflow

1. Confirm the prompt, audience, and exact period.
2. Query `qmd` before grepping notes; use prior reviews only for voice.
3. Group work into the prompt's themes; keep claims tied to evidence.
4. Verify quantified or current claims with the right source or skill.
5. Keep `submission-full.md` for evidence and `submission-final.md` for paste.
6. For 1-2 example prompts, use: `Outcome/progress`, `Behaviors demonstrated`, and `What I learned and will carry forward`.

See [workflow details](references/workflow.md) for the checklist.

## Rich Paste

```bash
uv run ~/.claude/skills/self-review/scripts/copy_rich_markdown.py \
  <path-to-review>/performance-review-submission-final.md
```

The helper writes `*-review-rich.html` and `*-review-rich.txt`, then copies HTML plus plain text.

## Troubleshooting

- Do not run `qmd update`, `qmd embed`, or `qmd collection add` unless asked.
- Plain `pbcopy` loses rich formatting; use the helper.
- Do not submit through browser automation unless explicitly asked.
- Do not overstate data; use the noun the source actually measures.

## Examples

- "Draft my H1 self review from notes and my prior review."
- "Copy this final review Markdown as rich text."
