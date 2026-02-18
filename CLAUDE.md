# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository provides modular skills that enable AI agents to interact with Mozilla's development tools and CI systems. Each skill is self-contained and uses official Mozilla tools where available.

## Role and Context

**Your role**: Supporting Firefox CI infrastructure, not Firefox development itself. You work on CI tooling, worker pool configurations, and automation that supports Firefox developers.

**Firefox Repository References**: When working with Firefox-related skills (especially os-integrations, treeherder, lando), be aware of the Firefox repository's agent guidance:

- **Local Firefox CLAUDE.md**: `/Users/jwmoss/firefox/CLAUDE.md` (read this file for full Firefox development guidance)
- **Firefox CLAUDE.md (GitHub)**: https://github.com/mozilla-firefox/firefox/blob/main/CLAUDE.md (references AGENTS.md)
- **Firefox AGENTS.md (GitHub)**: https://github.com/mozilla-firefox/firefox/blob/main/AGENTS.md

Key Firefox workflow notes from AGENTS.md:
- **Always use `searchfox-cli` for searching the Firefox codebase** (never grep/rg on ~/firefox)
- `./mach` is the main interface (`./mach build`, `./mach test`, `./mach try`, etc.)
- Always run `./mach format` and `./mach lint` before committing
- Use `./mach try auto` to run tests in CI
- Never perform commits yourself - always let the user commit
- Local Firefox repo (`~/firefox`) is only needed for `mach try` pushes, not for code searches

These Firefox conventions apply when debugging CI issues or testing worker configurations that involve Firefox builds/tests.

## Repository Structure

```
agent-skills/
├── skills/           # Individual skill implementations
│   ├── bugzilla/    # Mozilla Bugzilla interaction
│   ├── jira/        # Mozilla JIRA integration
│   ├── lando/       # Lando landing job status
│   ├── treeherder/  # Treeherder CI query tool
│   ├── taskcluster/ # Taskcluster CI interaction
│   └── os-integrations/  # Firefox mach try with worker overrides
└── agents/          # Custom subagent definitions for Task tool
```

Each skill directory contains:
- `SKILL.md` - Complete skill documentation with metadata header
- `references/` - Reference documentation and examples
- `scripts/` - Implementation scripts

## Custom Subagents

The `agents/` directory contains custom subagent definitions that are symlinked to `~/.claude/agents/` for global availability. These agents are automatically available in any project directory.

**Setup**: `~/.claude/agents` → `/path/to/agent-skills/agents`

Use these custom subagents with the Task tool instead of the default subagent types when appropriate:

| Agent | Model | Use For |
|-------|-------|---------|
| **helper** | Sonnet | Reading markdown, planning, research, analysis, explanations, non-coding tasks |
| **coder** | Opus | Writing code, refactoring, implementing features, fixing bugs, any coding task |
| **explorer** | Haiku | Fast codebase exploration, finding files, searching for patterns, quick analysis |

### When to Use Each Agent

**Use `helper` for:**
- Reading and summarizing documentation (markdown files, READMEs)
- Planning multi-step tasks
- Research and analysis
- Explaining concepts
- Reviewing and providing feedback
- Any task that doesn't involve writing code

**Use `coder` for:**
- Writing new code or scripts
- Refactoring existing code
- Implementing features
- Fixing bugs
- Any task that requires code changes

**Use `explorer` for:**
- Quickly finding files by pattern
- Searching for specific functions or classes
- Understanding project structure
- Rapid code walkthroughs
- Any quick codebase navigation task

### Example Usage

These agents are automatically available via the Task tool:

```
# For reading and summarizing a markdown file
Use the helper agent to read and summarize the README.md

# For implementing a new feature
Use the coder agent to add error handling to the tc.py script

# For finding where something is implemented
Use the explorer agent to find all files that handle authentication
```

You can also request them explicitly: "Have the coder implement..." or "Ask the explorer to find..."

## Core Design Principles

1. **Official tools first** - Use Mozilla's official packages (lando-cli, treeherder-client, mach) rather than direct API calls
2. **Isolated execution** - All Python tools use `uv`/`uvx` for zero-install, dependency-isolated execution
3. **Single responsibility** - Each skill focuses on one specific task
4. **Framework agnostic** - Skills work with any agent that supports terminal access

## Development Commands

### Running Skills

Skills are executed using `uv run` with the full path to the script:

```bash
# Bugzilla skill - search, create, update bugs
uv run ~/.claude/skills/bugzilla/scripts/bz.py search --quicksearch "crash"

# JIRA skill
uv run ~/.claude/skills/jira/scripts/extract_jira.py [options]

# Treeherder skill - two CLI tools
treeherder-cli a13b9fc22101 --json                          # Primary: failure analysis
uvx --from lumberjackth lj pushes autoland -n 10             # Secondary: push listing, failures-by-bug

# Lando skill - uses uvx for zero-install execution
uvx --from lando-cli lando check-job <job_id>

# Taskcluster skill — native CLI for most ops, tc.py for actions/artifacts
export TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com
taskcluster task status <TASK_ID>                                      # status
taskcluster task log <TASK_ID>                                         # logs
taskcluster task def <TASK_ID>                                         # definition
taskcluster group list --all <TASK_GROUP_ID>                          # list group
uv run ~/.claude/skills/taskcluster/scripts/tc.py artifacts <TASK_ID> # full artifact JSON
uv run ~/.claude/skills/taskcluster/scripts/tc.py retrigger <TASK_ID> # in-tree retrigger

# OS Integrations - requires Firefox repo at ~/firefox for mach try
uv run ~/.claude/skills/os-integrations/scripts/run_try.py win11-24h2 --dry-run
```

### Testing Skills

Each skill should be tested manually by running the scripts with appropriate parameters. There are no automated tests currently.

### Creating New Skills

Use the built-in `/skill-creator` skill in Claude Code to create new skills. This guides you through the process interactively and ensures proper structure and metadata.

When creating scripts, always use `uv` for Python execution (never run Python directly).

## Important Patterns

### Skill Metadata Format

Every `SKILL.md` must start with YAML frontmatter:
```yaml
---
name: skill-name
description: >
  Single-line description used by agents to determine when to invoke this skill.
  Include trigger keywords if applicable.
---
```

### Python Dependency Management

- Use `uv` for all Python execution to ensure isolated environments
- For one-off CLI tools: `uvx --from package-name command`
- For custom scripts with dependencies:
  1. Create `pyproject.toml` with dependencies
  2. Execute with `uv run script.py` (uv automatically syncs dependencies)
- Never commit `.venv/` or `uv.lock` files

### Configuration Management

- User-specific config files (e.g., `config.toml`) should have `.example` versions committed
- Add actual config files to `.gitignore`
- Prefer environment variables for credentials (simple, works in CI/CD)
- 1Password CLI is an optional fallback for local development

## Skill-Specific Details

### Bugzilla Skill
- Uses `requests` library to interact with BMO REST API
- Auth: Set `BUGZILLA_API_KEY` env var (generate at https://bugzilla.mozilla.org/userprefs.cgi?tab=apikey)
- Read-only operations work without authentication
- Supports search, get, create, update, comment, and attachment operations
- Run with: `uv run ~/.claude/skills/bugzilla/scripts/bz.py <command>`

### JIRA Skill
- Uses official `jira` Python package (v3.10.0+)
- Auth: Set `JIRA_API_TOKEN` and `JIRA_EMAIL` env vars (1Password CLI optional fallback)
- Config file: `skills/jira/scripts/config.toml` (optional, for custom JIRA URL/project)
- Outputs to `~/moz_artifacts/jira_stories.json` by default
- Supports creating, modifying, and querying issues with Markdown formatting

### Treeherder Skill
- Uses two CLI tools: **treeherder-cli** (primary) and **lumberjackth** (secondary)
- **treeherder-cli**: Rust CLI for failure analysis, revision comparison, test history, log fetching, artifact downloads. Install with `cargo install --git https://github.com/padenot/treeherder-cli`
- **lumberjackth**: Python CLI for push listing, failures-by-bug, error suggestions, perf alerts, result/tier/state filtering. Zero-install via `uvx --from lumberjackth lj`
- Read-only access, no authentication required for either tool

### Lando Skill
- Uses official `lando-cli` package via uvx
- Requires `~/.mozbuild/lando.toml` with API token
- Check landing job status by job ID

### OS Integrations Skill
- Runs Firefox `mach try` with worker pool overrides for alpha testing
- Requires local Firefox repo at `~/firefox` (for mach try pushes only)
- Presets defined in `references/presets.yml`
- Must be on a feature branch (not main/master)
- Available presets: win11-24h2, win11-hw, win10-2009, win11-amd, win11-arm64, b-win2022, win11-source

### Taskcluster Skill
- **Always set** `TASKCLUSTER_ROOT_URL=https://firefox-ci-tc.services.mozilla.com`
- **Native CLI first**: use `taskcluster task status/log/def/rerun/cancel` and `taskcluster group list/status/cancel` for basic operations
- **tc.py for the rest**: `artifacts` (full JSON with URLs), `group-status` (structured state counts), and all in-tree actions
- In-tree actions (`retrigger`, `confirm-failures`, `backfill`, `retrigger-multiple`, `action-list`, `action`) require auth with `hooks:trigger-hook:project-gecko/in-tree-action-*` scope
- **Never use** `taskcluster task retrigger` for Firefox CI — it clears dependencies; use `uv run tc.py retrigger` instead
- Intermittent triage order: `treeherder-cli --history` / `--similar-history` → `lj errors` → `tc.py confirm-failures` → `tc.py backfill`

## Working with Firefox Repository

The local Firefox repository (`~/firefox`) is only needed for running `mach try` pushes to test changes on CI. **Do not search the local Firefox repo** - always use `searchfox-cli` for code searches instead, as the Firefox codebase is too large for local grep/rg.
