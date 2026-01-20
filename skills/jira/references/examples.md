## Commands

Run these examples from the skill's scripts directory (`skills/jira/scripts`). If you're in the skill root, run `cd scripts` first.

### List Projects
```bash
uv run extract_jira.py --list-projects
```

### Extract Stories (Default: RELOPS project)
```bash
uv run extract_jira.py
```

### Extract by Project
```bash
uv run extract_jira.py --project PROJECT_KEY
```

### Extract Epics Only
```bash
uv run extract_jira.py --epics
```

### Extract Stories from a Specific Epic
```bash
uv run extract_jira.py --epic-key RELOPS-123
```

### Extract Your Issues
```bash
uv run extract_jira.py --my-issues
```

### Extract Current Sprint Stories
```bash
uv run extract_jira.py --current-sprint --summary
```

### Extract Your Stories in Current Sprint
```bash
uv run extract_jira.py --current-sprint --my-issues --summary
```

### Filter by Status
```bash
uv run extract_jira.py --status "In Progress"
uv run extract_jira.py --status "Done"
```

### Filter by Assignee
```bash
uv run extract_jira.py --assignee "Jonathan Moss"
```

### Filter by Date Range
```bash
uv run extract_jira.py --created-after 2025-01-01
uv run extract_jira.py --updated-after 2025-06-01
```

### Custom JQL Query
```bash
uv run extract_jira.py --jql "project = RELOPS AND status = 'In Progress'"
```

### Combine Filters
```bash
uv run extract_jira.py --project RELOPS --status "Done" --created-after 2025-01-01 -o completed_2025.json
```

## Modify Stories

### Change Status
```bash
uv run extract_jira.py --modify RELOPS-123 --set-status "Backlog"
uv run extract_jira.py --modify RELOPS-123 --set-status "In Progress"
```

### Remove from Sprint
```bash
uv run extract_jira.py --modify RELOPS-123 --remove-sprint
```

### Move to Sprint
```bash
uv run extract_jira.py --modify RELOPS-123 --set-sprint "RelOps 28"
```

### Change Epic
```bash
uv run extract_jira.py --modify RELOPS-123 --set-epic RELOPS-456
uv run extract_jira.py --modify RELOPS-123 --remove-epic
```

### Sprint Removal (Backlog)
```bash
uv run extract_jira.py --modify RELOPS-123 --remove-sprint
```

### Modify Multiple Issues
```bash
uv run extract_jira.py --modify RELOPS-123,RELOPS-124,RELOPS-125 --set-status "Backlog" --remove-sprint
```

### Update Description (with Markdown)
```bash
uv run extract_jira.py --modify RELOPS-123 --set-description "## Summary

Updated the feature.

## Changes
- Fixed bug
- Added tests"
```

### Add Comment (with Markdown)
```bash
uv run extract_jira.py --modify RELOPS-123 --add-comment "Completed the implementation. See [PR #123](https://github.com/org/repo/pull/123)."
```

### Dry Run (Preview Changes)
```bash
uv run extract_jira.py --modify RELOPS-123 --set-status "Done" --dry-run
```
