---
name: jira
description: Extract, create, and modify JIRA stories from Mozilla JIRA (mozilla-hub.atlassian.net). Use when the user asks to create JIRA stories, update JIRA issues, search for stories, list epics, add comments, or work with sprints. Supports Markdown formatting in descriptions and comments.
---

# JIRA

Interact with Mozilla JIRA via the `extract_jira.py` script.

## Quick Reference

```bash
cd scripts && uv run extract_jira.py --help      # Full option documentation
uv run extract_jira.py --help | grep -A3 "flag"  # Search for specific flag
```

For detailed examples, see [references/examples.md](references/examples.md).

## Prerequisites

Set environment variables:

```bash
export JIRA_API_TOKEN="your-api-token"  # From https://id.atlassian.com/manage-profile/security/api-tokens
export JIRA_EMAIL="your@email.com"
export JIRA_OUTPUT_DIR="~/moz_artifacts"   # Optional: output directory
export JIRA_DEFAULT_PROJECT="RELOPS"       # Optional: default project
```

Precedence: CLI args > env vars > config.toml > defaults

## Common Operations

### Query Issues

```bash
uv run extract_jira.py --current-sprint --summary    # Current sprint
uv run extract_jira.py --my-issues                   # Your issues
uv run extract_jira.py --epics                       # List epics
uv run extract_jira.py --jql "key = RELOPS-123"      # Specific issue
```

### Create Issues

```bash
uv run extract_jira.py --create --create-summary "Title" \
  --epic-create RELOPS-2019 \
  --sprint-create "RelOps 28" \
  --assignee-create me
```

### Modify Issues

```bash
uv run extract_jira.py --modify RELOPS-123 --set-status "In Progress"
uv run extract_jira.py --modify RELOPS-123 --set-sprint "RelOps 28"
uv run extract_jira.py --modify RELOPS-123 --link-issue RELOPS-456 --link-type "Issue split"
```

### Link Types

Use `--link-type` with `--link-issue`. Common types:
- `Relates` (default) - General relationship
- `Blocks` - Dependency
- `Issue split` - Work split from another issue
- `Duplicate` - Duplicate issues
- `Cloners` - Clone relationship

Run `uv run extract_jira.py --help` and search for `--link-type` for the complete list.

## Output

Stories are saved to `~/moz_artifacts/jira_stories.json` by default.

```bash
uv run extract_jira.py --stdout           # Output JSON to stdout (for piping)
uv run extract_jira.py --quiet            # Suppress status messages
uv run extract_jira.py --output-dir /tmp  # Custom output directory
```
