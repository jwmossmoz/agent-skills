# Output Format

Save to `~/moz_artifacts/daily-log-YYYY-MM-DD.md`.

```markdown
# Daily Work Log - YYYY-MM-DD

## Summary

2-3 sentence overview of the day's main themes and accomplishments.

---

## Codex Sessions (N sessions)

### HH:MM - Short title

1-3 sentence summary of what was done and the outcome. Include bug IDs,
revision numbers, and branch names where relevant.

### HH:MM - Short title

...

---

## Claude Code Sessions (N sessions)

### ~HH:MM - Short title

1-3 sentence summary. Use ~ prefix on times extracted from timestamps
rather than filenames.

---

## Artifacts Produced

| Type | ID | Description |
|------|-----|-------------|
| Bugzilla | Bug NNNNNNN | Short description |
| Phabricator | DNNNNNN | Short description |
| JIRA | RELOPS-NNNN | Short description |
| Analysis | filename.md | Short description |
```

## Guidelines

- Session times: Use local time. Codex filenames contain local time directly. Claude Code timestamps are UTC - convert to local.
- Artifacts table: Include bugs filed, Phabricator revisions submitted, JIRA stories created, try pushes, analysis files saved, and skill updates.
- Interrupted sessions: Note briefly with "(interrupted)" suffix.
- Combine related sessions that worked on the same bug in the summary section, but keep them separate in the session list.
