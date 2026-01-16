# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository provides modular skills that enable AI agents to interact with Mozilla's development tools and CI systems. Each skill is self-contained and uses official Mozilla tools where available.

## Repository Structure

```
agent-skills/
├── skills/           # Individual skill implementations
│   ├── jira/        # Mozilla JIRA integration
│   ├── lando/       # Lando landing job status
│   ├── treeherder/  # Treeherder CI query tool
│   ├── os-integrations/  # Firefox mach try with worker overrides
│   └── skill-creator/    # Skill creation guide
└── agents/          # Agent persona definitions (unused by skills)
```

Each skill directory contains:
- `SKILL.md` - Complete skill documentation with metadata header
- `references/` - Reference documentation and examples
- `scripts/` - Implementation scripts

## Core Design Principles

1. **Official tools first** - Use Mozilla's official packages (lando-cli, treeherder-client, mach) rather than direct API calls
2. **Isolated execution** - All Python tools use `uv`/`uvx` for zero-install, dependency-isolated execution
3. **Single responsibility** - Each skill focuses on one specific task
4. **Framework agnostic** - Skills work with any agent that supports terminal access

## Development Commands

### Running Skills

Skills are designed to be executed from their script directories using `uv`:

```bash
# JIRA skill - requires uv sync first for dependencies
cd skills/jira/scripts && uv sync && uv run extract_jira.py [options]

# Treeherder skill - direct execution with uv run
uv run skills/treeherder/scripts/query.py --revision <hash> --repo try

# Lando skill - uses uvx for zero-install execution
uvx --from lando-cli lando check-job <job_id>

# OS Integrations - requires Firefox repo at ~/firefox
cd skills/os-integrations/scripts && uv run run_try.py win11-24h2 --dry-run
```

### Testing Skills

Each skill should be tested manually by running the scripts with appropriate parameters. There are no automated tests currently.

### Creating New Skills

1. Create a new directory under `skills/<skill-name>/`
2. Add `SKILL.md` with the frontmatter metadata:
   ```yaml
   ---
   name: skill-name
   description: What the skill does and when to use it
   ---
   ```
3. Create `scripts/` directory for implementation
4. Add `references/` directory for examples and documentation
5. Use `uv` for Python dependency management (create `pyproject.toml` if needed)

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
  2. Execute with `uv sync && uv run script.py`
- Never commit `.venv/` or `uv.lock` files

### Configuration Management

- User-specific config files (e.g., `config.toml`) should have `.example` versions committed
- Add actual config files to `.gitignore`
- Use environment variables for credentials when possible
- Prefer 1Password CLI integration for secure credential retrieval

## Skill-Specific Details

### JIRA Skill
- Uses official `jira` Python package (v3.10.0+)
- Requires 1Password CLI or environment variables for authentication
- Config file: `skills/jira/scripts/config.toml` (create from `config.toml.example`)
- Outputs to `~/moz_artifacts/jira_stories.json` by default
- Supports creating, modifying, and querying issues with Markdown formatting

### Treeherder Skill
- Uses official `treeherder-client` library
- Read-only access, no authentication required
- Query by revision hash or push ID
- Filter results by test name patterns

### Lando Skill
- Uses official `lando-cli` package via uvx
- Requires `~/.mozbuild/lando.toml` with API token
- Check landing job status by job ID

### OS Integrations Skill
- Runs Firefox `mach try` with worker pool overrides for alpha testing
- Requires Firefox repo at `~/firefox`
- Presets defined in `references/presets.yml`
- Must be on a feature branch (not main/master)
- Available presets: win11-24h2, win11-hw, win10-2009, win11-amd, win11-arm64, b-win2022, win11-source

## Working with Firefox Repository

Several skills assume the Firefox repository is located at `~/firefox`. This is a Mozilla development environment convention.
