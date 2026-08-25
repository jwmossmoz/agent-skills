---
name: jira
description: >
  Use when a Mozilla JIRA task needs RELOPS defaults, sprint-aware issue
  management, safe bulk edits, or Markdown-to-ADF conversion through the local
  helper.
metadata:
  version: "1.1"
---

# JIRA

Use this script instead of the Atlassian MCP for Mozilla JIRA work. It supports
RELOPS defaults, sprint queries, comment edits, links, and bulk dry runs.

## Prerequisites

Set `JIRA_EMAIL` and `JIRA_API_TOKEN`. The email must own the token. For custom
defaults, copy [config.toml.example](scripts/config.toml.example) to
`scripts/config.toml`.

## Usage

```bash
JIRA=~/.claude/skills/jira/scripts/extract_jira.py

# Read issues.
uv run "$JIRA" --current-sprint --summary
uv run "$JIRA" --jql 'key = RELOPS-123' --stdout --quiet

# Create or change a story.
uv run "$JIRA" --create --create-summary "Title" \
  --description "## Context\n\nDescription" --epic-create RELOPS-2019
uv run "$JIRA" --modify RELOPS-123 --set-status "In Progress"
uv run "$JIRA" --modify RELOPS-123 --append-description "New notes"
```

Run `uv run "$JIRA" --help` for comments, links, bulk changes, and other
fields. See [examples.md](references/examples.md) for complete workflows.

## Gotchas

- Write descriptions and comments in Markdown. Do not use Jira wiki markup.
  The script converts Markdown to Atlassian Document Format.
- Review text that other people will read before you submit it.
- The default project is RELOPS. Use JQL or explicit project options for
  another project.
- The default output file is `~/moz_artifacts/jira_stories.json`.
