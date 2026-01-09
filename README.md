# Agent Skills

A collection of reusable skills for Claude Code and other AI agents.

## Structure

```
agent-skills/
└── .claude/
    └── skills/
        ├── jira/           # JIRA integration skill
        └── skill-creator/  # Skill development helper
```

## Available Skills

### JIRA
Extract, create, and modify JIRA stories.
See [.claude/skills/jira/SKILL.md](.claude/skills/jira/SKILL.md) for details.

### Skill Creator  
Helper for creating new agent skills.
See [.claude/skills/skill-creator/SKILL.md](.claude/skills/skill-creator/SKILL.md) for details.

## Usage

Skills in `.claude/skills/` are automatically discovered by Claude Code.

## Setup

Each skill may have its own setup requirements. Check individual SKILL.md files for:
- Prerequisites
- Configuration
- Usage examples
