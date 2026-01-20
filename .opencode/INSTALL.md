# OpenCode Setup

Configure OpenCode to load skills from this repo's `skills/` directory.

If your OpenCode setup uses a skills directory, you can use symlinks:

```bash
AGENT_SKILLS_ROOT="/path/to/agent-skills"

mkdir -p ~/.opencode/skills

ln -s "$AGENT_SKILLS_ROOT/skills/lando" ~/.opencode/skills/lando
ln -s "$AGENT_SKILLS_ROOT/skills/treeherder" ~/.opencode/skills/treeherder
ln -s "$AGENT_SKILLS_ROOT/skills/os-integrations" ~/.opencode/skills/os-integrations
ln -s "$AGENT_SKILLS_ROOT/skills/jira" ~/.opencode/skills/jira
ln -s "$AGENT_SKILLS_ROOT/skills/taskcluster" ~/.opencode/skills/taskcluster
ln -s "$AGENT_SKILLS_ROOT/skills/writing-skills" ~/.opencode/skills/writing-skills
```

If OpenCode is configured via an environment variable or config file, point it at the absolute `skills/` directory instead.
