---
name: Jira
description: Extract, create, and modify JIRA stories from Mozilla JIRA (mozilla-hub.atlassian.net).
---

# JIRA

## Prerequisites

### 1. 1Password CLI
This skill uses 1Password CLI to securely retrieve JIRA API tokens. You must:

1. **Install 1Password CLI**: https://developer.1password.com/docs/cli/get-started/
2. **Sign in**: Run `op signin` to authenticate
3. **Create a JIRA API token** in your JIRA account settings
4. **Store in 1Password**: Save your JIRA API token and email in a 1Password item

### 2. Configuration

Copy the example configuration file and customize it:

```bash
cd .claude/skills/jira/scripts
cp config.toml.example config.toml
```

Edit `config.toml` to match your setup:
- `onepassword.item_name`: Your 1Password item name (default: "JiraMozillaToken")
- `onepassword.vault`: Your 1Password vault (default: "Private")
- `jira.base_url`: Your JIRA instance URL
- `jira.default_project`: Your default project key

**Note**: `config.toml` is gitignored to keep your settings private.

## Usage

Run the JIRA script from the `scripts` directory where `pyproject.toml` is located. Always use `uv sync && uv run` to ensure dependencies are installed:

```bash
cd .claude/skills/jira/scripts && uv sync && uv run extract_jira.py [options]
```

Or if already in the scripts directory:
```bash
uv sync && uv run extract_jira.py [options]
```

Reference examples.md for examples.

## Output

Stories are saved to `~/moz_artifacts/jira_stories.json` by default.
- Use `-o FILENAME` to specify a different filename
- Use `-d DIRECTORY` or `--output-dir DIRECTORY` to specify a different directory

Each story includes:
- key, url, summary, description
- status, issue_type, priority
- project_key, project_name
- assignee, assignee_email
- reporter, reporter_email
- epic_key, epic_name (if linked to an epic)
- sprints (list of sprint names)
- created, updated, resolved dates
- labels, components, fix_versions

## Authentication

The script uses 1Password CLI to retrieve the JIRA API token. Configuration is set in `config.toml`:
- `onepassword.item_name`: The 1Password item containing your JIRA credentials
- `onepassword.vault`: The vault where the item is stored
- `onepassword.credential_field`: Field name for API token (default: `credential`)
- `onepassword.username_field`: Field name for email (default: `username`)

See the Prerequisites section above for setup instructions.

## Examples

First, change to the scripts directory and sync dependencies:
```bash
cd .claude/skills/jira/scripts && uv sync
```

Then run commands with `uv run extract_jira.py`. When the user asks to:
- "extract my JIRA stories" → Run with `--my-issues`
- "show my sprint stories" or "current sprint" → Run with `--current-sprint --my-issues --summary`
- "get all RELOPS epics" → Run with `--epics`
- "show stories in epic RELOPS-123" → Run with `--epic-key RELOPS-123`
- "stories in specific sprint" → Run with `--sprint "Sprint Name"`
- "export done stories from last month" → Run with `--status Done --created-after YYYY-MM-01`
- "list JIRA projects" → Run with `--list-projects`

## Creating Stories

The script can create new JIRA issues. Use `--create` with required and optional parameters.

### Create Options
- `--create-summary "Title"` - Summary/title for the issue (REQUIRED)
- `--description "Details"` - Description for the issue
- `--issue-type-create TYPE` - Issue type (default: Story)
- `--priority-create PRIORITY` - Priority (e.g., "High", "Medium", "Low")
- `--assignee-create ASSIGNEE` - Assignee (use "me" for yourself, or email/account ID)
- `--epic-create EPIC-KEY` - Link to an epic (e.g., RELOPS-2028)
- `--sprint-create "Sprint Name"` - Add to a specific sprint
- `--labels-create "label1,label2"` - Comma-separated labels
- `--fix-versions-create "2026 Q1"` - Comma-separated fix versions
- `--project-create PROJECT` - Project key (default: RELOPS)
- `--dry-run` - Preview what would be created without actually creating it

### Create Examples

When the user asks to:
- "create a JIRA story with title X" → Run with `--create --create-summary "X"`
- "create a story for epic RELOPS-2028" → Run with `--create --create-summary "Title" --epic-create RELOPS-2028`
- "create a story and assign to me" → Run with `--create --create-summary "Title" --assignee-create me`
- "create a high priority story in current sprint" → Run with `--create --create-summary "Title" --priority-create High --sprint-create "Sprint Name"`
- "create a story with fix version 2026 Q1" → Run with `--create --create-summary "Title" --fix-versions-create "2026 Q1"`
- "create a bug in project FOO" → Run with `--create --create-summary "Bug title" --issue-type-create Bug --project-create FOO`

## Modifying Stories

The script can also modify JIRA issues. Use `--modify` with one or more issue keys (comma-separated).

### Modify Options
- `--set-status STATUS` - Change status (e.g., "Backlog", "In Progress", "Done")
- `--remove-sprint` - Remove issue(s) from their current sprint
- `--set-sprint "Sprint Name"` - Move issue(s) to a specific sprint
- `--set-epic EPIC-KEY` - Set the epic link
- `--remove-epic` - Remove issue(s) from their current epic
- `--set-fix-versions "2026 Q1"` - Set fix versions (comma-separated)
- `--dry-run` - Preview changes without applying them

### Modify Examples

When the user asks to:
- "move RELOPS-123 to backlog" → Run with `--modify RELOPS-123 --set-status Backlog`
- "remove these stories from the sprint" → Run with `--modify RELOPS-123,RELOPS-124 --remove-sprint`
- "move RELOPS-123 to the KTLO epic" → Run with `--modify RELOPS-123 --set-epic RELOPS-56`
- "set fix version to 2026 Q1" → Run with `--modify RELOPS-123 --set-fix-versions "2026 Q1"`
- "remove from sprint and set to backlog" → Run with `--modify RELOPS-123 --set-status Backlog --remove-sprint`
