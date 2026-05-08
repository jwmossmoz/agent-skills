---
name: daily-log
description: >
  Generate a daily work log by scanning Claude Code (~/.claude/projects/)
  and Codex (~/.codex/sessions/) session JSONL files and compiling them
  into ~/moz_artifacts/daily-log-YYYY-MM-DD.md. Use when summarizing a
  day's sessions or reviewing what the user worked on.
---

# Daily Log

Generate a daily work log by scanning session JSONL files from known locations.

## Session file locations

| Agent | Location | Format |
|-------|----------|--------|
| Claude Code | `~/.claude/projects/*/` | JSONL files in per-project dirs |
| Codex | `~/.codex/sessions/YYYY/MM/DD/` | JSONL files with local-time filenames |

## Workflow

1. Determine the target date (default: today)
2. Find all session JSONL files modified on the target date
3. Read each session to extract user prompts and outcomes
4. Compile the log and write the output file
5. Refresh the qmd `moz` collection so the new log is searchable

## Step 1: Find session files for the target date

```bash
# Claude Code sessions modified today
fd -e jsonl --changed-within 1d . ~/.claude/projects/

# Codex sessions with today's date in the filename (YYYY-MM-DD pattern)
fd -e jsonl "2026-04-14" ~/.codex/sessions/
```

For a specific date, adjust the `--changed-within` or filename pattern accordingly.

Filter out subagent sessions (paths containing `/subagents/`) — only
summarize top-level sessions.

## Step 2: Extract session content

Read each JSONL file directly. Each line is a JSON object representing a
message in the conversation.

### JSONL message structure

See `references/jsonl-formats.md` for detailed field descriptions.

Claude Code lines have `type: "user"` or `type: "assistant"`; Codex lines
have `type: "response_item"` with `payload.role` of `user` / `assistant` /
`developer`.

### What to extract

For each session:
- **First user message**: serves as the session title/topic
- **User prompts**: scan user-role messages for key requests and decisions
- **Artifacts**: look for bug IDs, JIRA tickets, commit hashes, file paths,
  revision numbers, try push links
- **Outcomes**: check the final assistant messages for results and summaries

For large sessions, read only the first 200 and last 100 lines to get
the topic and outcome without consuming excessive context.

## Step 3: Compile the log

Group sessions by agent. Use the output format in `references/output-format.md`.

Derive session times from:
- **Claude Code**: file modification time, or timestamps within the JSONL
- **Codex**: filename contains local time directly

Save to: `~/moz_artifacts/daily-log-YYYY-MM-DD.md`

## Step 4: Refresh the qmd index

After the log file is written, re-index the `moz` qmd collection so the new
log is queryable immediately:

```bash
qmd update && qmd embed
```

Both are incremental — they only scan/embed new or changed chunks, so this
is cheap even when run at the end of every log generation.

## Notes

- Focus on user prompts and high-level outcomes, not every tool call
- Sessions under 3 user turns can be summarized in one line
- If a session was interrupted before meaningful work, note it briefly
- Combine related sessions (same bug/task across multiple sessions) in the summary

## Gotchas

- Subagent JSONL files (paths containing `/subagents/`) are noise. Skip them — only top-level sessions are worth summarizing.
- Codex filenames already encode local time; Claude Code session files don't, so use file mtime for ordering Claude sessions.
- For very large sessions (thousands of lines), read the first 200 + last 100. The first messages give the topic; the last give the outcome. Reading the whole file blows context for no benefit.
- Always run `qmd update && qmd embed` after writing the log so the new file is searchable; both are incremental and cheap.
