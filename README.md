# Agent Skills

A collection of reusable skills for AI agents working with Mozilla Firefox development and CI infrastructure.

## Overview

This repository provides modular skills that enable AI agents to interact with Mozilla's development tools and CI systems. Skills use official Mozilla tools and libraries where available, with minimal custom wrappers.

## Skills

- **lando** - Check Lando landing job status using `lando-cli`
- **treeherder** - Query Treeherder CI job results using `treeherder-client`
- **os-integrations** - Run Firefox mach try with alpha worker pool overrides
- **jira** - Create and modify Mozilla JIRA stories
- **taskcluster** - Query Taskcluster task status, logs, artifacts, and task groups
- **writing-skills** - Write and maintain Agent Skills with best practices

## Subagents

- **agents/coder** - Code implementation specialist
- **agents/explorer** - Fast codebase discovery
- **agents/helper** - Planning, research, and explanation support

## Usage

### For Users

Once skills are installed, simply ask Claude naturally:

- "Show me my current sprint stories"
- "Check the treeherder status for my push"
- "Run os-integration tests on Windows 11"
- "Create a JIRA story for fixing the login bug"

Claude will invoke the appropriate skill and handle all the technical details (directory navigation, command execution, etc.) for you.

### For Installation / Manual Use

#### Claude Code

Symlink skills to your Claude Code skills directory and agents to your agents directory:

```bash
AGENT_SKILLS_ROOT="/path/to/agent-skills"

ln -s "$AGENT_SKILLS_ROOT/skills/lando" ~/.claude/skills/lando
ln -s "$AGENT_SKILLS_ROOT/skills/treeherder" ~/.claude/skills/treeherder
ln -s "$AGENT_SKILLS_ROOT/skills/os-integrations" ~/.claude/skills/os-integrations
ln -s "$AGENT_SKILLS_ROOT/skills/jira" ~/.claude/skills/jira
ln -s "$AGENT_SKILLS_ROOT/skills/taskcluster" ~/.claude/skills/taskcluster
ln -s "$AGENT_SKILLS_ROOT/skills/writing-skills" ~/.claude/skills/writing-skills

ln -s "$AGENT_SKILLS_ROOT/agents/coder.md" ~/.claude/agents/coder.md
ln -s "$AGENT_SKILLS_ROOT/agents/explorer.md" ~/.claude/agents/explorer.md
ln -s "$AGENT_SKILLS_ROOT/agents/helper.md" ~/.claude/agents/helper.md
```

See `.claude-plugin/INSTALL.md` for the full Claude Code checklist.

#### Codex

Add this repo's `skills/` directory to your Codex skills search path. See `.codex/INSTALL.md` for a checklist.

#### OpenCode

Add this repo's `skills/` directory to your OpenCode skills search path. See `.opencode/INSTALL.md` for a checklist.

Each skill contains:
- `SKILL.md` - Full documentation and examples for Claude's reference
- `references/examples.md` - Command-line examples for manual execution
- `scripts/` - The actual implementation scripts

`uv.lock` files are tracked intentionally for reproducible Python dependencies. Run `uv sync` in each skill's `scripts/` directory after updates.

## Design Principles

- **Official tools first** - Use Mozilla's official packages (`lando-cli`, `treeherder-client`, `mach`)
- **Isolated execution** - All Python tools use `uv`/`uvx` for dependency isolation
- **Single responsibility** - Each skill does one thing well
- **Framework agnostic** - Works with any agent framework that supports terminal access

## Requirements

- [uv](https://docs.astral.sh/uv/) - For running Python scripts in isolated environments
- Skill-specific prerequisites are documented in each `SKILL.md`
