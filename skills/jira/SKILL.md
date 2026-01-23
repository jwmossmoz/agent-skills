---
name: jira
description: Extract, create, and modify JIRA stories from Mozilla JIRA (mozilla-hub.atlassian.net). Use when the user asks to create JIRA stories, update JIRA issues, search for stories, list epics, add comments, or work with sprints. Supports Markdown formatting in descriptions and comments.
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
cd scripts && uv run extract_jira.py [options]
```

| Operation | Command |
|-----------|---------|
| Query current sprint | `--current-sprint --summary` |
| Query your issues | `--my-issues` |
| Query specific issue | `--jql "key = RELOPS-123"` |
| Create issue | `--create --create-summary "Title"` |
| Modify issue | `--modify RELOPS-123 --set-status "In Progress"` |
| Link issues | `--modify RELOPS-123 --link-issue RELOPS-456` |
| Output to stdout | `--stdout --quiet` |

## Resources

- **Full examples**: [references/examples.md](references/examples.md)
- **All options**: `uv run extract_jira.py --help`
- **Output**: `~/moz_artifacts/jira_stories.json` (default)
