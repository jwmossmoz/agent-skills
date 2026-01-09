# Agent Skills

A collection of reusable skills for Claude Code and other AI agents.

## Structure

```
agent-skills/
└── .claude/
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
Run Firefox mach try commands with pre-configured flags for os-integration testing on Windows alpha worker pools.

**Available presets:** win11-24h2, win11-hw, win10-2009, win11-amd, win11-source, b-win2022, win11-arm64

See [.claude/skills/os-integrations/SKILL.md](.claude/skills/os-integrations/SKILL.md) for details.

## Usage

Skills in `.claude/skills/` are automatically discovered by Claude Code.

## Setup

Each skill may have its own setup requirements. Check individual SKILL.md files for:
- Prerequisites
- Configuration
- Usage examples
