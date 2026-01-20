---
name: jira
description: Extract, create, and modify JIRA stories from Mozilla JIRA (mozilla-hub.atlassian.net). Use when the user asks to create JIRA stories, update JIRA issues, search for stories, list epics, add comments, or work with sprints. Supports Markdown formatting in descriptions and comments.
---

# JIRA

## Prerequisites

### 1. JIRA API Token

Create a JIRA API token from your Atlassian account:
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label and copy the token

### 2. Authentication

Set environment variables (recommended):

```bash
export JIRA_API_TOKEN="your-api-token"
export JIRA_EMAIL="your@email.com"
```

Add these to your shell profile (`~/.zshrc` or `~/.bashrc`) for persistence.

### 3. Configuration (Optional)

For custom JIRA instance URLs or default project settings, create a config file:

```bash
cd ~/github_moz/agent-skills/skills/jira/scripts
cp config.toml.example config.toml
```

Edit `config.toml`:
- `jira.base_url`: Your JIRA instance URL (default: mozilla-hub.atlassian.net)
- `jira.default_project`: Default project key (default: RELOPS)

## Usage

Run the JIRA script from the `scripts` directory. Use `uv sync && uv run` to ensure dependencies are installed:

```bash
cd ~/github_moz/agent-skills/skills/jira/scripts && uv sync && uv run extract_jira.py [options]
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

The script checks for credentials in this order:

### Option 1: Environment Variables (Recommended)

```bash
export JIRA_API_TOKEN="your-api-token"
export JIRA_EMAIL="your@email.com"
```

### Option 2: 1Password CLI (Optional Fallback)

If environment variables are not set, the script falls back to 1Password CLI. Requires:
1. 1Password CLI installed (`brew install 1password-cli`)
2. Signed in (`op signin`)
3. Configuration in `config.toml`:
   - `onepassword.item_name`: Item containing credentials
   - `onepassword.vault`: Vault name
   - `onepassword.credential_field`: Field for API token (default: `credential`)
   - `onepassword.username_field`: Field for email (default: `username`)

## Examples

First, change to the scripts directory and sync dependencies:
```bash
cd ~/github_moz/agent-skills/skills/jira/scripts && uv sync
```

Then run commands with `uv run extract_jira.py`. When the user asks to:
- "extract my JIRA stories" → Run with `--my-issues`
- "show my sprint stories" or "my current sprint stories" → Run with `--current-sprint --my-issues --summary`
- "current sprint" or "all sprint stories" → Run with `--current-sprint --summary`
- "get all RELOPS epics" → Run with `--epics`
- "show stories in epic RELOPS-123" → Run with `--epic-key RELOPS-123`
- "stories in specific sprint" → Run with `--sprint "Sprint Name"`
- "export done stories from last month" → Run with `--status Done --created-after YYYY-MM-01`
- "list JIRA projects" → Run with `--list-projects`

## Creating Stories

The script can create new JIRA issues. Use `--create` with required and optional parameters.

### Create Options
- `--create-summary "Title"` - Summary/title for the issue (REQUIRED)
- `--description "Details"` - Description (supports Markdown formatting)
- `--issue-type-create TYPE` - Issue type (default: Story)
- `--priority-create PRIORITY` - Priority (e.g., "High", "Medium", "Low")
- `--assignee-create ASSIGNEE` - Assignee (use "me" for yourself, or email/account ID)
- `--reporter-create REPORTER` - Reporter (use "me" for yourself, email, display name, or account ID)
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
- "create a story with John as reporter" → Run with `--create --create-summary "Title" --reporter-create "John Doe"` or `--reporter-create jdoe@mozilla.com`
- "create a high priority story in current sprint" → Run with `--create --create-summary "Title" --priority-create High --sprint-create "Sprint Name"`
- "create a story with fix version 2026 Q1" → Run with `--create --create-summary "Title" --fix-versions-create "2026 Q1"`
- "create a bug in project FOO" → Run with `--create --create-summary "Bug title" --issue-type-create Bug --project-create FOO`

## Modifying Stories

The script can also modify JIRA issues. Use `--modify` with one or more issue keys (comma-separated).

### Modify Options
- `--set-status STATUS` - Change status (e.g., "Backlog", "In Progress", "Done")
- `--set-summary "Text"` - Update the issue summary/title
- `--set-description "Text"` - Update the description (supports Markdown)
- `--set-reporter REPORTER` - Change the reporter (email, display name, "me", or account ID)
- `--add-comment "Text"` - Add a comment to the issue (supports Markdown)
- `--remove-sprint` - Remove issue(s) from their current sprint
- `--set-sprint "Sprint Name"` - Move issue(s) to a specific sprint
- `--set-epic EPIC-KEY` - Set the epic link
- `--remove-epic` - Remove issue(s) from their current epic
- `--set-fix-versions "2026 Q1"` - Set fix versions (comma-separated)
- `--link-issue ISSUE-KEY` - Link to another issue (e.g., RELOPS-456)
- `--link-type TYPE` - Type of link: Relates (default), Blocks, Clones, Duplicate
- `--unlink-issue ISSUE-KEY` - Remove link to another issue (e.g., RELOPS-456)
- `--dry-run` - Preview changes without applying them

### Modify Examples

When the user asks to:
- "move RELOPS-123 to backlog" → Run with `--modify RELOPS-123 --set-status Backlog`
- "remove these stories from the sprint" → Run with `--modify RELOPS-123,RELOPS-124 --remove-sprint`
- "move RELOPS-123 to the KTLO epic" → Run with `--modify RELOPS-123 --set-epic RELOPS-56`
- "set fix version to 2026 Q1" → Run with `--modify RELOPS-123 --set-fix-versions "2026 Q1"`
- "remove from sprint and set to backlog" → Run with `--modify RELOPS-123 --set-status Backlog --remove-sprint`
- "update the description" → Run with `--modify RELOPS-123 --set-description "New description"`
- "change the title" → Run with `--modify RELOPS-123 --set-summary "New title"`
- "add a comment" → Run with `--modify RELOPS-123 --add-comment "Comment text"`
- "change the reporter to John" → Run with `--modify RELOPS-123 --set-reporter "John Doe"` or `--set-reporter jdoe@mozilla.com`
- "link RELOPS-123 to RELOPS-456" → Run with `--modify RELOPS-123 --link-issue RELOPS-456`
- "link as blocking" → Run with `--modify RELOPS-123 --link-issue RELOPS-456 --link-type Blocks`

## Markdown Formatting

Descriptions and comments support Markdown formatting, which is automatically converted to JIRA's rich text format:

- `## Heading` - Headings (levels 1-6)
- `- item` or `* item` - Bullet lists
- `1. item` - Numbered lists
- ` ```language ` - Code blocks with syntax highlighting
- `` `code` `` - Inline code
- `[text](url)` - Links
- `**bold**` - Bold text
- `*italic*` - Italic text

Example with Markdown:
```bash
--description "## Summary

Implemented feature X.

## Changes
- Added new endpoint
- Updated tests

## Usage
\`\`\`bash
curl https://api.example.com/v1/endpoint
\`\`\`"
```
