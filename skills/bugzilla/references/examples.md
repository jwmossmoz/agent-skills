# Bugzilla Examples & Workflows

## User Request Mappings

When the user asks to:
- "search bugzilla for crashes" → `uv run bz.py search --quicksearch "crash"`
- "find my assigned bugs" → `uv run bz.py search --assignee user@mozilla.com --status ASSIGNED`
- "show bug 1234567" → `uv run bz.py get 1234567 -v`
- "file a bug for Firefox" → `uv run bz.py create --product Firefox --component General --summary "..." --version unspecified`
- "mark bug as fixed" → `uv run bz.py update 1234567 --status RESOLVED --resolution FIXED`
- "add a comment to bug" → `uv run bz.py comment 1234567 "Comment text"`
- "attach a file to bug" → `uv run bz.py attachment 1234567 /path/to/file`
- "request needinfo" → `uv run bz.py needinfo 1234567 --request user@mozilla.com`
- "clear needinfo" → `uv run bz.py needinfo 1234567 --clear`
- "find P1 bugs" → `uv run bz.py search --product Firefox --priority P1 --status NEW,ASSIGNED`
- "export bugs to json" → `uv run bz.py search --quicksearch "crash" --format json --output results.json`

## Common Workflows

### Duplicate a bug
```bash
uv run bz.py update 1234567 --status RESOLVED --resolution DUPLICATE \
  --add-comment "Duplicate of bug 7654321"
```

### Triage a bug
```bash
uv run bz.py update 1234567 --priority P2 --severity major
```

### Close as fixed with comment
```bash
uv run bz.py update 1234567 --status RESOLVED --resolution FIXED \
  --add-comment "Fixed in https://hg.mozilla.org/..."
```

### Reassign a bug
```bash
uv run bz.py update 1234567 --assignee newowner@mozilla.com \
  --add-comment "Reassigning to the appropriate owner"
```

### Bulk search to JSON
```bash
uv run bz.py search --product Core --status NEW --format json --output bugs.json
```

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Access denied" | Bug is in restricted security group | Your account lacks permission |
| "Invalid field value" | Bad product/component/version | Run `uv run bz.py products <Product> -v` |
| "API key not set" | Missing auth for write ops | `export BUGZILLA_API_KEY="..."` |
| Rate limited | Too many rapid requests | Add delays between bulk operations |
