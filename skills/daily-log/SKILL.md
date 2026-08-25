---
name: daily-log
description: >
  Use when compiling one day's Claude Code and Codex sessions into a concise
  work log with outcomes and artifacts under ~/moz_artifacts, or reviewing
  what work was completed on a specific date.
metadata:
  version: "1.1"
---

# Daily Log

Collect bounded session evidence, then write a human-readable work log.

## Prerequisites

Use Python 3.10 or later. Session files must be available under
`~/.claude/projects/` and `~/.codex/sessions/`.

## Usage

```bash
COLLECT=~/.claude/skills/daily-log/scripts/collect_sessions.py

python3 "$COLLECT" --date YYYY-MM-DD \
  --output /tmp/daily-log-source-YYYY-MM-DD.md
```

Read the source file, combine related sessions, and write
`~/moz_artifacts/daily-log-YYYY-MM-DD.md` with the structure in
[output-format.md](references/output-format.md). Include outcomes, bug or issue
IDs, revisions, try pushes, and files produced. Omit routine tool calls.

## Gotchas

- The collector skips Claude subagent files and bounds message size.
- Claude session selection uses the file modification date. Codex uses its
  date directory. Check a known session directly if it is absent.
- The source file is evidence, not the final log. Verify long or interrupted
  sessions before stating an outcome.
- Do not run `qmd update` or `qmd embed` automatically. After writing the log,
  tell the user to run both commands if they want it indexed.

## Related Skills

- Use **one-on-one** to turn indexed logs into manager-facing status bullets.
- Read [jsonl-formats.md](references/jsonl-formats.md) only when a session
  format changes or the collector misses content.
