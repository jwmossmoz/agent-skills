# Claude Code Setup

Use symlinks so Claude Code can discover skills and subagents.

```bash
AGENT_SKILLS_ROOT="/path/to/agent-skills"

mkdir -p ~/.claude/skills ~/.claude/agents

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

Restart Claude Code and confirm the skills show up in the available skills list.
