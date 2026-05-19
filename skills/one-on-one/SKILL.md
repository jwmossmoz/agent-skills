---
name: one-on-one
description: >
  Prepare one-on-one/status bullets from ~/moz_artifacts using qmd and copy
  a topic-organized HTML/RTF list with embedded links to the macOS clipboard.
  Use when summarizing recent Mozilla work for a manager, 1:1, or status
  update. DO NOT USE FOR generating raw daily logs; use daily-log.
metadata:
  version: "1.0"
---

# One-on-One

Prepare manager-facing bullets from recent Mozilla work notes and put them
on the clipboard in a Google Docs-friendly rich format.

## Prerequisites

- `qmd` indexes `~/moz_artifacts` as collection `moz`.
- macOS with `/usr/bin/swift`; the clipboard helper uses AppKit.
- Optional: `gh` for resolving GitHub PR URLs when notes only mention
  `repo#123` or `PR #123`.
- Optional: `peekaboo` for inspecting Google Docs paste results, but do not
  drive the document unless the user explicitly asks.

## Usage

Most runs are interactive: gather the relevant artifacts, write the bullets,
then call the clipboard helper with a JSON payload.

```bash
qmd query "one on one work summary May 13 May 19 2026" -c moz -n 20
qmd get "daily-log-2026-05-19.md"
swift ~/.claude/skills/one-on-one/scripts/copy-rich-bullets.swift /tmp/one-on-one.json
```

Minimal payload:

```json
{
  "sections": [
    {
      "title": "Windows / Firefox CI reliability",
      "bullets": [
        {
          "segments": [
            {"text": "Validated "},
            {"text": "Bug 1970481", "url": "https://bugzilla.mozilla.org/show_bug.cgi?id=1970481"},
            {"text": " on 25H2 alpha with all target rows green."}
          ]
        }
      ]
    }
  ]
}
```

The helper sets three pasteboard types at once: HTML, RTF, and plain text.
Google Docs usually consumes the HTML/RTF path; the plain-text fallback keeps
the clipboard readable in terminals and plain editors.

## Workflow

1. Determine the date range. If the user gives relative dates, state the
   concrete range you are using.
2. Query `qmd` before grepping `~/moz_artifacts`:

   ```bash
   qmd query "work summary one on one <date range>" -c moz -n 20
   qmd ls
   ```

3. Pull full source documents for the range with `qmd get`. Check the
   filesystem for new markdown files if the user just regenerated logs:

   ```bash
   rg --files ~/moz_artifacts | rg '2026-05-(13|14|15|16|17|18|19)'
   ```

4. Extract work items, outcomes, IDs, and URLs. Prefer concrete outcomes:
   PR opened/merged, bug filed, validation passed, cost impact quantified,
   root cause found, or handoff written.
5. Resolve hyperlinks for all externally meaningful references:
   - Bugzilla: `https://bugzilla.mozilla.org/show_bug.cgi?id=<bug>`
   - Jira: `https://mozilla-hub.atlassian.net/browse/<KEY>`
   - GitHub PR: use the actual `https://github.com/<owner>/<repo>/pull/<n>`
   - Treeherder: use the revision URL from the note, or construct
     `https://treeherder.mozilla.org/jobs?repo=try&revision=<rev>`
   - Taskcluster tasks: use the task URL if the source note includes a task id
     and that task is important to the bullet.
6. Organize bullets by topic, not date. Good default topics:
   - Trybox / local validation
   - Windows / Firefox CI reliability
   - OS integration / test coverage
   - Cost attribution / Azure reliability
   - Worker images / provisioning
7. Keep bullets manager-facing. Avoid implementation trivia unless it explains
   impact, risk, or a decision.
8. Write `/tmp/one-on-one.json` and run the clipboard helper.
9. Tell the user the clipboard is ready, and mention any date gaps or missing
   source logs.

## Examples

Each bullet should be one sentence when possible. Use links on the words a
human would expect to click, not naked URLs:

```json
{
  "segments": [
    {"text": "Opened "},
    {"text": "fxci-config PR #1002", "url": "https://github.com/mozilla-releng/fxci-config/pull/1002"},
    {"text": " with eviction and cost evidence for Spot pools."}
  ]
}
```

Use `text`-only segments for unlinked parts. Do not put literal bullet
characters in the text; the helper creates native HTML list items.

## Gotchas

- Do not run `qmd update`, `qmd embed`, or `qmd collection add` unless the
  user explicitly asks. Reading commands like `qmd query`, `qmd search`,
  `qmd get`, and `qmd ls` are safe.
- Google Docs may paste literal bullet characters if the clipboard only has
  plain text. Use the helper so the clipboard includes HTML and RTF list data.
- If Google Docs is already in bullet-list mode, ask the user to turn it off
  before pasting the rich list, or it can nest the pasted bullets.
- Do not blindly drive Google Docs with clicks. If automation is requested,
  use `peekaboo` to inspect the active window first and verify the cursor is
  in the intended date section.
- qmd can be stale if a daily log was just generated. Check `qmd status` and
  `fd -e md ~/moz_artifacts --changed-within <range>` before concluding a
  day had no artifacts.

## Related Skills

- Use `daily-log` when the user needs to generate or refresh a daily log from
  Claude Code/Codex session JSONL files before building the one-on-one notes.
- Use `redash` or `bigquery` when the summary needs fresh telemetry or CI data,
  rather than only prior notes in `~/moz_artifacts`.
