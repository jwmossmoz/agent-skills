---
name: daily-log
description: >
  Generate a daily work log by scanning Claude Code and Codex session JSONL files.
  Compile session summaries into a markdown file at ~/moz_artifacts/daily-log-YYYY-MM-DD.md.
  Use when the user says: "daily log", "end of day log", "what did I do today",
  "daily summary", "work log", "summarize my sessions", or asks to review their day's work.
---

# Daily Log

Generate a daily work log from Claude Code and Codex session histories.

## Workflow

1. Determine the target date (default: today)
2. Launch two helper subagents in parallel - one for Claude Code sessions, one for Codex sessions
3. Merge results chronologically and write the output file

## Step 1: Find session files

**Claude Code sessions:**
```bash
find ~/.claude/projects -name "*.jsonl" -type f | while read f; do
  mod=$(stat -f "%Sm" -t "%Y-%m-%d" "$f" 2>/dev/null)
  if [ "$mod" = "TARGET_DATE" ]; then echo "$f"; fi
done | sort
```
Skip files under `subagents/` directories - only read main session files.

**Codex sessions:**
```
~/.codex/sessions/YYYY/MM/DD/*.jsonl
```

## Step 2: Launch parallel subagents

Launch two `helper` subagents simultaneously via the Task tool:

**Subagent prompt template** (adapt for Claude Code vs Codex):
> Read each session JSONL file for TARGET_DATE. For each session extract:
> 1. Start time (from filename or first timestamp)
> 2. Project/working directory
> 3. User's initial prompt
> 4. Key actions (bugs filed, patches submitted, files edited, commands run)
> 5. Outcome (completed, interrupted, result)
>
> Return a structured summary per session, ordered chronologically.

See `references/jsonl-formats.md` for the JSONL structure of each tool.

## Step 3: Compile the log

Merge both subagent results into a single markdown file. Use the output format in `references/output-format.md`.

Save to: `~/moz_artifacts/daily-log-YYYY-MM-DD.md`

## Notes

- Focus on user prompts and high-level outcomes, not every tool call
- Sessions under 3 lines of user interaction can be summarized in one line
- If a session was interrupted before meaningful work, note it briefly
- Combine related sessions (same bug/task across multiple sessions) in the summary
