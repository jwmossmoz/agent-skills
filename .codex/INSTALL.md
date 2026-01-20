# Codex Setup

Point Codex at this repo's `skills/` directory so it can discover the skills.

If your Codex setup supports a skills directory, you can use symlinks:

```bash
AGENT_SKILLS_ROOT="/path/to/agent-skills"

mkdir -p ~/.codex/skills

ln -s "$AGENT_SKILLS_ROOT/skills/lando" ~/.codex/skills/lando
ln -s "$AGENT_SKILLS_ROOT/skills/treeherder" ~/.codex/skills/treeherder
ln -s "$AGENT_SKILLS_ROOT/skills/os-integrations" ~/.codex/skills/os-integrations
ln -s "$AGENT_SKILLS_ROOT/skills/jira" ~/.codex/skills/jira
ln -s "$AGENT_SKILLS_ROOT/skills/taskcluster" ~/.codex/skills/taskcluster
ln -s "$AGENT_SKILLS_ROOT/skills/writing-skills" ~/.codex/skills/writing-skills
```

If your Codex setup uses a different config path, add the absolute `skills/` directory there instead.
