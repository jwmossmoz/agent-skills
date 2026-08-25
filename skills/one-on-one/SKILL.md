---
name: one-on-one
description: >
  Use when turning indexed Mozilla work notes into topic-based manager or 1:1
  bullets with links and copying them as rich text. DO NOT USE FOR raw logs.
metadata:
  version: "1.1"
---

# One-on-One

Build concise status bullets from `~/moz_artifacts` and copy HTML, RTF, and
plain-text versions to the macOS clipboard.

## Prerequisites

The `moz` qmd collection must index `~/moz_artifacts`. The clipboard helper
needs macOS and `/usr/bin/swift`.

## Usage

```bash
qmd query "work summary one on one <date range>" -c moz -n 20
qmd get "daily-log-YYYY-MM-DD.md"
swift ~/.claude/skills/one-on-one/scripts/copy-rich-bullets.swift \
  /tmp/one-on-one.json
```

Create a JSON object with a `sections` array. Each section has a `title` and
`bullets`; each bullet has `segments` with `text` and an optional `url`.

## Workflow

1. State the concrete date range.
2. Query qmd before you inspect files directly.
3. Group work by topic, not date. Lead with outcomes, risk, cost, or decisions.
4. Link Bugzilla, JIRA, GitHub, Treeherder, and important Taskcluster items.
5. Write `/tmp/one-on-one.json`, run the helper, and report source gaps.

## Gotchas

- Do not run `qmd update`, `qmd embed`, or `qmd collection add` unless the user
  asks. `qmd query`, `search`, `get`, `ls`, and `status` are read-only.
- Use the helper; plain `pbcopy` loses rich list formatting.
- Do not drive Google Docs unless the user asks. Verify the target before an
  automated paste.
- If qmd can be stale, check recent files before you report a missing day.

## Related Skills

- Use **daily-log** to create missing source logs.
- Use data skills only when the summary needs fresh evidence, not prior notes.
