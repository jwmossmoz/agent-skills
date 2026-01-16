---
name: lando
description: >
  Check the status of Lando landing jobs using Mozilla's official lando-cli tool.
  Use after submitting try pushes with mach try to verify if your commit has landed.
  Triggers on "lando status", "landing job", "check landing", "commit landed".
---

# Lando

## Overview

Check the status of Mozilla Lando landing jobs using the official `lando-cli` package. After submitting a try push with `mach try`, you receive a landing job ID. Use this skill to check if the commit has successfully landed and get the revision hash.

**When to use:** After running `mach try` commands to verify the commit landed before querying Treeherder for job results.

## Prerequisites

### Lando CLI Configuration

To use `lando` commands, create a config file at `~/.mozbuild/lando.toml`:

```toml
[auth]
api_token = "<YOUR_API_TOKEN>"
user_email = "your.email@mozilla.com"
```

**Getting an API token:** Request one from the Mozilla Conduit team.

## Quick Start

```bash
# Check landing job status by ID
uvx --from lando-cli lando check-job <JOB_ID>
```

### Example

```bash
# After mach try, you get output like:
# Landing job id: 173397
# Treeherder: https://treeherder.mozilla.org/jobs?repo=try&landoCommitID=173397

# Check if the landing completed
uvx --from lando-cli lando check-job 173397
```

## Output Explained

### Status Values

- **SUBMITTED** - Landing job is queued, commit not landed yet
  - **Action:** Wait 1-2 minutes and check again
- **LANDED** - Commit successfully landed
  - **Action:** Use the revision hash to query Treeherder
- **FAILED** - Landing failed due to errors
  - **Action:** Check error messages and fix issues before resubmitting

### Example Output

**Still landing:**
```bash
$ uvx --from lando-cli lando check-job 173397
Status: SUBMITTED
Waiting for landing to complete...
```

**Successfully landed:**
```bash
$ uvx --from lando-cli lando check-job 173397
Status: LANDED
Revision: c081f3f7d21922047379fe76320cfbc3abf7f2b3
Branch: try
Repository: https://hg.mozilla.org/try/
```

**Failed:**
```bash
$ uvx --from lando-cli lando check-job 173397
Status: FAILED
Error: Merge conflict detected
```

## Complete Workflow

### After Try Push

```bash
# 1. Submit try push (from Firefox repository)
cd ~/firefox
./mach try fuzzy --query 'windows11 24h2 debug mochitest-chrome'

# Output shows:
# Landing job id: 173397
# Treeherder: https://treeherder.mozilla.org/jobs?repo=try&landoCommitID=173397

# 2. Check landing status (wait 1-2 minutes)
uvx --from lando-cli lando check-job 173397

# 3. Once landed, use the revision to query Treeherder
# See treeherder-query skill for checking job results
```

## Other lando-cli Commands

```bash
# Push new commits directly (requires permissions)
uvx --from lando-cli lando push-commits <ARGS>

# Push merge actions
uvx --from lando-cli lando push-merge <ARGS>

# Push new tags
uvx --from lando-cli lando push-tag <ARGS>

# See all commands
uvx --from lando-cli lando --help
```

## Typical Timeline

- **0-30 seconds**: Job queued (SUBMITTED)
- **30-90 seconds**: Processing and landing
- **90-120 seconds**: Commit lands (LANDED)
- **2-5 minutes**: Appears on Treeherder

## Troubleshooting

### "No API token configured"

Create `~/.mozbuild/lando.toml` with your API token:

```toml
[auth]
api_token = "<TOKEN>"
user_email = "you@mozilla.com"
```

### "lando: command not found"

Use the full `uvx` command:

```bash
uvx --from lando-cli lando check-job 173397
```

### Landing stuck in SUBMITTED

- Wait a few minutes - landing can take time
- Check if there are many queued landings
- Verify the try push was successful with `mach try`

### FAILED status

Common causes:
- Merge conflicts
- Invalid commit message format
- Insufficient permissions
- Repository access issues

Check the error message for specific details.

## Integration with Other Skills

### With os-integrations

```bash
# 1. Submit try push with worker overrides (os-integrations skill)
cd ~/firefox
./mach try fuzzy \
  --query 'windows11 24h2 debug' \
  --preset os-integration \
  --worker-override win11-64-24h2=gecko-t/win11-64-24h2-alpha

# Output: Landing job id: 173397

# 2. Check landing (lando-status skill)
uvx --from lando-cli lando check-job 173397

# Output: Revision: c081f3f7d219...

# 3. Query job results (treeherder-query skill)
uv run ~/.claude/skills/treeherder-query/scripts/query.py \
  --revision c081f3f7d219 \
  --filter mochitest-chrome
```

## Benefits of lando-cli

- ✅ **Official Mozilla tool** - Maintained by the Conduit team
- ✅ **No installation needed** - Use with `uvx` for isolated execution
- ✅ **Authenticated access** - Secure API token authentication
- ✅ **Real-time status** - Query landing job progress
- ✅ **Error reporting** - Detailed failure messages

## Resources

- **lando-cli**: [PyPI](https://pypi.org/project/lando-cli/) | [GitHub](https://github.com/mozilla-conduit/lando-api)
- **Lando API**: https://api.lando.services.mozilla.com/
- **Conduit Documentation**: https://moz-conduit.readthedocs.io/
