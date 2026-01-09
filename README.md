# Agent Skills

A collection of reusable skills for Claude Code and other AI agents.

## Structure

```
agent-skills/
└── .claude/
    ├── agents/
    │   ├── coder.md      # Opus-powered code implementation
    │   ├── explorer.md   # Haiku-powered fast exploration  
    │   └── helper.md     # Sonnet-powered general assistance
    └── skills/
        ├── jira/               # JIRA integration skill
        ├── skill-creator/      # Skill development helper
        └── os-integrations/    # Firefox mach try os-integration testing
```

## Available Skills

### JIRA
Extract, create, and modify JIRA stories.
See [.claude/skills/jira/SKILL.md](.claude/skills/jira/SKILL.md) for details.

### Skill Creator  
Helper for creating new agent skills.
See [.claude/skills/skill-creator/SKILL.md](.claude/skills/skill-creator/SKILL.md) for details.

### OS Integrations
This skill runs Firefox mach try commands for os-integration testing on Windows virtual machines. Tests execute on Windows VMs hosted in Azure, which are organized as worker pools in Mozilla's Taskcluster CI system. The skill targets "alpha" worker pools, which are used for testing new VM images before they are promoted to production. This allows for validation of OS integration features in a controlled testing environment.

**Available presets:** win11-24h2, win11-hw, win10-2009, win11-amd, win11-source, b-win2022, win11-arm64

See [.claude/skills/os-integrations/SKILL.md](.claude/skills/os-integrations/SKILL.md) for details.

## Agents

Custom agents optimized for different tasks to balance cost and performance.

| Agent | Model | Use Case |
|-------|-------|----------|
| **coder** | Opus | Writing, refactoring, implementing features. Use for code implementation. |
| **explorer** | Haiku | Fast codebase search, finding files, understanding structure. Use for discovery. |
| **helper** | Sonnet | Planning, research, explanations, task organization. Use for non-coding tasks. |

Agent definitions are in `.claude/agents/`.

## Usage

Skills in `.claude/skills/` are automatically discovered by Claude Code.

## Setup

Each skill may have its own setup requirements. Check individual SKILL.md files for:
- Prerequisites
- Configuration
- Usage examples
