---
name: one-on-one
description: >
  Use when turning indexed Mozilla work notes into linked, topic-based manager
  or 1:1 bullets and copying them as rich text. DO NOT USE FOR daily logs or
  performance reviews.
metadata:
  version: "1.4"
---

# One-on-One

Build topic-based status bullets from `~/moz_artifacts`; copy HTML, RTF, and
plain text to the macOS clipboard.

## Prerequisites

The `moz` qmd collection must index `~/moz_artifacts`. The clipboard helper
needs macOS and `/usr/bin/swift`.

## Usage

```bash
qmd query "work summary one on one <date range>" -c moz -n 20
qmd get "daily-log-YYYY-MM-DD.md"
swift ~/.claude/skills/one-on-one/scripts/copy-rich-bullets.swift /tmp/one-on-one.json
```

Write a JSON object with a `sections` array; each section has a `title` and
`bullets`, and each bullet has `segments` with `text` and optional `url`.

## Workflow

1. State the date range and query qmd before opening files directly.
2. Group by topic. Pick 4–6 topics with the most outcome, risk, cost, or decision value; put the rest in one "Other" bullet.
3. Aim for about 15 bullets. Each is one sentence of 25 words or less: result, then why it matters. Skip sub-bullets, process steps, and non-actionable numbers.
4. Add 1–2 links per bullet to the relevant bug, PR, or ticket. Link the noun; omit Treeherder or Taskcluster unless it is the main evidence.
5. Write `/tmp/one-on-one.json`, run the helper, and report source gaps.

## Gotchas

- Do not run `qmd update`, `qmd embed`, or `qmd collection add` unless asked; query, search, get, ls, and status are read-only.
- Use the helper to preserve rich formatting. Do not drive Google Docs unless asked; verify the target before pasting.
- If qmd may be stale, check recent files before reporting a missing day.

## Related Skills

Use **daily-log** for missing session logs and **self-review** for performance reviews.
