---
name: jira
description: >
  Search, create, modify, comment, link, or transition issues in Mozilla
  JIRA (mozilla-hub.atlassian.net) via the extract_jira.py script. Markdown
  → ADF conversion is built in. Prefer this skill over the Atlassian MCP
  for JIRA work — it handles RELOPS defaults, sprint queries, comment
  edit/append, and bulk modify with dry-run.
metadata:
  version: "1.0"
---

# JIRA

Interact with Mozilla JIRA via `scripts/extract_jira.py`.

## Prerequisites

```bash
export JIRA_API_TOKEN="your-api-token"  # From https://id.atlassian.com/manage-profile/security/api-tokens
export JIRA_EMAIL="your@email.com"
```

Optional: `JIRA_OUTPUT_DIR`, `JIRA_DEFAULT_PROJECT`. Precedence: CLI args > env vars > config.toml > defaults.

## Usage

```bash
uv run ~/.claude/skills/jira/scripts/extract_jira.py [options]
```

| Operation | Command |
|-----------|---------|
| Query current sprint | `--current-sprint --summary` |
| Query your issues | `--my-issues` |
| Query specific issue | `--jql "key = RELOPS-123"` |
| Create issue | `--create --create-summary "Title"` |
| Modify issue | `--modify RELOPS-123 --set-status "In Progress"` |
| Append description | `--modify RELOPS-123 --append-description "New notes"` |
| Edit comment | `--modify RELOPS-123 --edit-comment 1242534 --comment-body "Updated content"` |
| Link issues | `--modify RELOPS-123 --link-issue RELOPS-456` |
| Output to stdout | `--stdout --quiet` |

## Markdown Formatting

Use **standard Markdown** for descriptions and comments. The tool automatically converts Markdown to Atlassian Document Format (ADF).

**DO NOT** use old Jira wiki markup syntax like `[text|url]` - it will not render correctly.

| Element | Correct (Markdown) | Wrong (Wiki Markup) |
|---------|-------------------|---------------------|
| Links | `[text](https://url)` | `[text\|https://url]` |
| Bold | `**text**` | `*text*` |
| Lists | `- item` or `1. item` | `* item` or `# item` |
| Code | `` `code` `` or ``` ```code``` ``` | `{code}code{code}` |
| Headings | `## Heading` | `h2. Heading` |

## Creating Stories

When creating JIRA stories, follow this workflow:

1. **Draft the story** - Create the summary and description based on requirements
2. **Humanize the description** - Use `/humanizer` to remove AI writing patterns from the description text
3. **Submit the story** - Use the humanized description with `--create`

### Example Workflow

```bash
# 1. Draft description (you do this in memory)
# 2. Run humanizer on the description
# 3. Create story with humanized description
uv run ~/.claude/skills/jira/scripts/extract_jira.py --create \
  --create-summary "Implement new feature" \
  --description "The feature adds capability to process tasks. It handles edge cases and provides error handling." \
  --epic-create RELOPS-2019
```

Use `/humanizer` to remove AI writing patterns from story descriptions before submitting.

## Gotchas

- Use Markdown, not Jira wiki markup (`*bold*`, `[text|url]`, `h2.`). The script converts Markdown to ADF; wiki markup renders as raw text.
- Run `/humanizer` on the description before `--create` — JIRA stories surface to other humans, and AI tells.
- `JIRA_API_TOKEN` is account-scoped. `JIRA_EMAIL` must match the token owner; mismatched email gives an opaque 401.
- Default project is RELOPS via this skill. Pass `--jql "project = X AND ..."` to query other projects.

## Resources

- **Full examples**: [references/examples.md](references/examples.md)
- **All options**: `uv run ~/.claude/skills/jira/scripts/extract_jira.py --help`
- **Output**: `~/moz_artifacts/jira_stories.json` (default)
