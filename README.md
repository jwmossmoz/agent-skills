# Agent Skills

A collection of reusable skills for AI agents working with Mozilla Firefox development and CI infrastructure.

## Overview

This repository provides modular skills that enable AI agents to interact with Mozilla's development tools and CI systems. Skills use official Mozilla tools and libraries where available, with minimal custom wrappers.

## Skills

- **lando** - Check Lando landing job status using `lando-cli`
- **treeherder** - Query Treeherder CI job results using `treeherder-client`
- **os-integrations** - Run Firefox mach try with alpha worker pool overrides
- **jira** - Create and modify Mozilla JIRA stories

## Usage

### For Users

Once skills are installed, simply ask Claude naturally:

- "Show me my current sprint stories"
- "Check the treeherder status for my push"
- "Run os-integration tests on Windows 11"
- "Create a JIRA story for fixing the login bug"

Claude will invoke the appropriate skill and handle all the technical details (directory navigation, command execution, etc.) for you.

### For Installation / Manual Use

Symlink skills to your agent's skill directory:

```bash
ln -s ~/github_moz/agent-skills/skills/lando ~/.claude/skills/lando
ln -s ~/github_moz/agent-skills/skills/treeherder ~/.claude/skills/treeherder
ln -s ~/github_moz/agent-skills/skills/os-integrations ~/.claude/skills/os-integrations
ln -s ~/github_moz/agent-skills/skills/jira ~/.claude/skills/jira
```

Each skill contains:
- `SKILL.md` - Full documentation and examples for Claude's reference
- `references/examples.md` - Command-line examples for manual execution
- `scripts/` - The actual implementation scripts

## Design Principles

- **Official tools first** - Use Mozilla's official packages (`lando-cli`, `treeherder-client`, `mach`)
- **Isolated execution** - All Python tools use `uv`/`uvx` for dependency isolation
- **Single responsibility** - Each skill does one thing well
- **Framework agnostic** - Works with any agent framework that supports terminal access

## Requirements

- [uv](https://docs.astral.sh/uv/) - For running Python scripts in isolated environments
- Skill-specific prerequisites are documented in each `SKILL.md`
