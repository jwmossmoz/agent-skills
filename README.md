# Agent Skills

A collection of reusable skills for Claude Code and other AI agents.

## Structure

```
agent-skills/
├── agents/
│   ├── coder.md      # Opus-powered code implementation
│   ├── explorer.md   # Haiku-powered fast exploration
│   └── helper.md     # Sonnet-powered general assistance
└── skills/
    ├── jira/               # JIRA integration skill
    ├── skill-creator/      # Skill development helper
    ├── os-integrations/    # Firefox mach try os-integration testing
    └── treeherder-status/  # Treeherder job status checker
```

## Available Skills

### JIRA
Extract, create, and modify JIRA stories.
See [skills/jira/SKILL.md](skills/jira/SKILL.md) for details.

### Skill Creator
Helper for creating new agent skills.
See [skills/skill-creator/SKILL.md](skills/skill-creator/SKILL.md) for details.

### OS Integrations
This skill runs Firefox mach try commands for os-integration testing on Windows and Linux virtual machines. Tests execute on VMs hosted in Azure/GCP, which are organized as worker pools in Mozilla's Taskcluster CI system. The skill targets "alpha" worker pools, which are used for testing new VM images before they are promoted to production. This allows for validation of OS integration features in a controlled testing environment.

**Available presets:** win11-24h2, win11-hw, win10-2009, win11-amd, win11-source, b-win2022, win11-arm64

**Linux worker overrides:** See the skill for Ubuntu 24.04 alpha image testing with marionette-integration.

See [skills/os-integrations/SKILL.md](skills/os-integrations/SKILL.md) for details.

### Treeherder Status
Check the status of Firefox try pushes on Treeherder by landing job ID. Queries Lando API for landing status and Treeherder API for job results. Use after submitting try pushes with mach try to monitor if jobs passed or failed.

See [skills/treeherder-status/SKILL.md](skills/treeherder-status/SKILL.md) for details.

## Agents

Custom agents optimized for different tasks to balance cost and performance.

| Agent | Model | Use Case |
|-------|-------|----------|
| **coder** | Opus | Writing, refactoring, implementing features. Use for code implementation. |
| **explorer** | Haiku | Fast codebase search, finding files, understanding structure. Use for discovery. |
| **helper** | Sonnet | Planning, research, explanations, task organization. Use for non-coding tasks. |

Agent definitions are in `agents/`.

## Usage

To use these skills with Claude Code, symlink them to `~/.claude/skills/`:

```bash
ln -s ~/github_moz/agent-skills/skills/* ~/.claude/skills/
```

Or configure Claude Code to look in this repository's `skills/` directory.

## Setup

Each skill may have its own setup requirements. Check individual SKILL.md files for:
- Prerequisites
- Configuration
- Usage examples
