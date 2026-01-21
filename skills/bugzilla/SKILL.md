---
name: bugzilla
description: Interact with Mozilla Bugzilla (bugzilla.mozilla.org) via REST API. Use when the user asks to search bugs, view bug details, create bugs, update bugs, add comments, or attach files. Triggers on "bugzilla", "bmo", "file a bug", "bug report", "mozilla bug".
---

# Bugzilla

## Prerequisites

### 1. API Key

Generate a Bugzilla API key:
1. Go to https://bugzilla.mozilla.org/userprefs.cgi?tab=apikey
2. Enter a description and click "Generate"
3. Copy the generated key

### 2. Authentication

Set the environment variable:

```bash
export BUGZILLA_API_KEY="your-api-key"
```

Add to your shell profile (`~/.zshrc` or `~/.bashrc`) for persistence.

Note: Read-only operations (search, get) work without authentication but may not show restricted bugs.

## Usage

Run from the `scripts` directory:

```bash
cd scripts && uv sync && uv run bz.py <command> [options]
```

## Commands

### Search Bugs

```bash
# Quick search (simple text)
uv run bz.py search --quicksearch "crash startup"

# Filter by product/component
uv run bz.py search --product Firefox --component "Developer Tools"

# Filter by assignee and status
uv run bz.py search --assignee user@mozilla.com --status ASSIGNED

# Multiple filters
uv run bz.py search --product Firefox --priority P1 --status NEW --limit 50
```

Search options:
- `--quicksearch TEXT` - Simple text search
- `--product NAME` - Product name (e.g., Firefox, Core, Toolkit)
- `--component NAME` - Component name
- `--status STATUS` - NEW, ASSIGNED, RESOLVED, VERIFIED, CLOSED
- `--resolution RES` - FIXED, INVALID, WONTFIX, DUPLICATE
- `--assignee EMAIL` - Assigned to
- `--reporter EMAIL` - Reported by
- `--priority P1-P5` - Priority level
- `--severity LEVEL` - blocker, critical, major, normal, minor, trivial, enhancement
- `--keywords KEYWORDS` - Keyword search
- `--whiteboard TEXT` - Status whiteboard contains
- `--summary TEXT` - Summary contains
- `--created-after DATE` - Created after (YYYY-MM-DD)
- `--changed-after DATE` - Changed after (YYYY-MM-DD)
- `--limit N` - Max results (default: 20)

### Get Bug Details

```bash
# Basic details
uv run bz.py get 1234567

# Include comments
uv run bz.py get 1234567 --include-comments

# Include history
uv run bz.py get 1234567 --include-history

# Verbose output
uv run bz.py get 1234567 -v --include-comments --include-history

# Multiple bugs
uv run bz.py get 1234567 1234568 1234569
```

### Create Bug

```bash
uv run bz.py create \
  --product Firefox \
  --component General \
  --summary "Bug title here" \
  --version "unspecified" \
  --description "Detailed description"

# With more options
uv run bz.py create \
  --product Firefox \
  --component "Developer Tools" \
  --summary "DevTools crash on startup" \
  --version "Trunk" \
  --description "Steps to reproduce..." \
  --severity major \
  --priority P2 \
  --keywords regression
```

Required: `--product`, `--component`, `--summary`, `--version`

Optional: `--description`, `--severity`, `--priority`, `--assignee`, `--cc`, `--keywords`, `--blocks`, `--depends-on`, `--see-also`

### Update Bug

```bash
# Change status
uv run bz.py update 1234567 --status RESOLVED --resolution FIXED

# Add comment with update
uv run bz.py update 1234567 --status RESOLVED --resolution FIXED --add-comment "Fixed in changeset abc123"

# Change assignee
uv run bz.py update 1234567 --assignee user@mozilla.com

# Modify dependencies
uv run bz.py update 1234567 --add-blocks 1234568 --add-depends-on 1234566

# Update priority/severity
uv run bz.py update 1234567 --priority P1 --severity critical
```

### Add Comment

```bash
# Public comment
uv run bz.py comment 1234567 "This is my comment"

# Private comment
uv run bz.py comment 1234567 "Private note" --private
```

### Add Attachment

```bash
# Basic attachment
uv run bz.py attachment 1234567 /path/to/file.log

# With summary and comment
uv run bz.py attachment 1234567 /path/to/crash.log \
  --summary "Crash log from STR" \
  --comment "Attached crash log from step 3"

# Mark as patch
uv run bz.py attachment 1234567 /path/to/fix.patch --is-patch
```

### List Products

```bash
# List all accessible products
uv run bz.py products

# Get product details with components
uv run bz.py products Firefox -v
```

### Verify Authentication

```bash
uv run bz.py whoami
```

## Examples

When the user asks to:
- "search bugzilla for crashes" → `uv run bz.py search --quicksearch "crash"`
- "find my assigned bugs" → `uv run bz.py search --assignee user@mozilla.com --status ASSIGNED`
- "show bug 1234567" → `uv run bz.py get 1234567 -v`
- "file a bug for Firefox" → `uv run bz.py create --product Firefox --component General --summary "..." --version unspecified`
- "mark bug as fixed" → `uv run bz.py update 1234567 --status RESOLVED --resolution FIXED`
- "add a comment to bug" → `uv run bz.py comment 1234567 "Comment text"`
- "attach a file to bug" → `uv run bz.py attachment 1234567 /path/to/file`

## API Reference

See `references/api-reference.md` for detailed REST API documentation including endpoints, parameters, and error codes.
