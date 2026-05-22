# Self-Review Workflow Details

## Evidence Gathering

Start from `qmd`, not raw `rg`, for prior work in the user's local notes:

```bash
qmd query "performance review daily logs manager themes" -c <collection> -n 20
qmd search "prior self reflection performance review" -c <collection> -n 10
```

Gather by theme rather than by day. Common themes are reliable CI platforms,
infrastructure observability, security/operational efficiency, and any
manager-provided headings.

Verify unstable or quantified claims before using them:

- Issue counts, meta tickets, and patch status: the relevant issue tracker.
- Project epics/stories: the relevant project tracker.
- Analytics, saved query IDs, and volume claims: the relevant data source.
- Local investigation details: `qmd get` and evidence notes.

## File Set

Use a predictable directory and names:

- `<artifacts-dir>/performance_review/<cycle>-working-draft.md`
- `<artifacts-dir>/performance_review/<cycle>-submission-full.md`
- `<artifacts-dir>/performance_review/<cycle>-submission-final.md`
- Topic evidence notes when calculations or caveats matter.

The full file can preserve the manager headings and evidence inventory. The
final file should answer the form prompt directly.

## Final Writing

Lead with outcomes, not a chronological work log. Use exact dates for
milestones. Prefer first person, concrete verbs, and short evidence-backed
claims. Use the user's prior review language when available.

Use the data noun the source actually measures: clients, profiles, tasks, runs,
or other source-specific units. Do not call telemetry clients "users" unless
the source really measures people.

Remove placeholder language before final paste: "draft", "if the form asks",
"evidence to keep", or notes to self.

## Rich Text Formatting

Many review forms use rich-text editors. The helper script copies both HTML and
plain text to the clipboard so headings, bold labels, code spans, and spacing
survive paste:

```bash
uv run ~/.claude/skills/self-review/scripts/copy_rich_markdown.py \
  <path-to-review>/performance-review-submission-final.md
```

If the user asks to inspect the review form, use `browser-harness` to identify
the active editor and confirm supported formatting controls. Do not click
submit unless explicitly asked.
