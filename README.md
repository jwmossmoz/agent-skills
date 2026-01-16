# Agent Skills

A collection of reusable skills for Claude Code and other AI agents, focused on Mozilla Firefox development workflows.

## Structure

```
agent-skills/
├── agents/             # Claude Code agent definitions
│   ├── coder.md       # Opus - code implementation
│   ├── explorer.md    # Haiku - fast exploration
│   └── helper.md      # Sonnet - planning & research
└── skills/            # Reusable skills
    ├── jira/          # JIRA integration
    ├── lando/         # Lando landing job status
    ├── os-integrations/  # Firefox mach try with alpha workers
    └── treeherder/    # Treeherder CI job results
```

## Available Skills

### lando

Check Mozilla Lando landing job status using the official `lando-cli` tool.

**Use when:** After `mach try` to verify your commit landed

**Example:**
```bash
uvx --from lando-cli lando check-job 173397
```

**Triggers:** "lando status", "landing job", "check landing", "commit landed"

[Full Documentation →](skills/lando/SKILL.md)

### treeherder

Query Firefox Treeherder for CI job results using the official `treeherder-client` library.

**Use when:** After commit lands to check build/test results

**Example:**
```bash
uv run ~/.claude/skills/treeherder/scripts/query.py \
  --revision c081f3f7d219 \
  --filter mochitest-chrome
```

**Triggers:** "treeherder", "job results", "check tests", "ci status"

[Full Documentation →](skills/treeherder/SKILL.md)

### os-integrations

Run Firefox mach try commands with pre-configured worker pool overrides for testing against Windows and Linux alpha images.

**Use when:** Testing Firefox changes against new VM images before production deployment

**Example:**
```bash
uv run ~/.claude/skills/os-integrations/scripts/run_try.py win11-24h2 --push
```

**Available presets:** win11-24h2, win11-hw, win10-2009, win11-amd, win11-source, b-win2022, win11-arm64

**Triggers:** "os-integration", "mach try", "windows testing", "linux testing", "alpha image"

[Full Documentation →](skills/os-integrations/SKILL.md)

### jira

Create, extract, and modify Mozilla JIRA stories (mozilla-hub.atlassian.net).

**Use when:** Working with Mozilla JIRA for issue tracking

**Triggers:** "jira", "create story", "update issue"

[Full Documentation →](skills/jira/SKILL.md)

## Complete Workflow Example

```bash
# 1. Submit try push with worker overrides (os-integrations)
uv run ~/.claude/skills/os-integrations/scripts/run_try.py win11-24h2 \
  -q "-xq 'mochitest-chrome'" \
  --push

# Output: Landing job id: 173397

# 2. Check landing status (lando)
uvx --from lando-cli lando check-job 173397

# Output: Status LANDED, Revision: c081f3f7d219...

# 3. Query test results (treeherder)
uv run ~/.claude/skills/treeherder/scripts/query.py \
  --revision c081f3f7d219 \
  --filter mochitest-chrome

# Output: ✅ success / ❌ testfailed / etc.
```

## Quick Setup

```bash
# Symlink skills to Claude Code
ln -s ~/github_moz/agent-skills/skills/lando ~/.claude/skills/lando
ln -s ~/github_moz/agent-skills/skills/treeherder ~/.claude/skills/treeherder
ln -s ~/github_moz/agent-skills/skills/os-integrations ~/.claude/skills/os-integrations
ln -s ~/github_moz/agent-skills/skills/jira ~/.claude/skills/jira

# Verify skills are available
ls -la ~/.claude/skills/
```

## Design Philosophy

### Official Tools First

Skills prioritize official Mozilla tools:
- ✅ `lando-cli` - Official Lando API client
- ✅ `treeherder-client` - Official Treeherder API client
- ✅ `mach try` - Firefox's native try server interface

Custom wrappers are only used when no official tool exists.

### Isolated Execution

All Python tools use `uv` or `uvx` for isolated execution:
- No global package pollution
- Reproducible environments
- Fast execution

### Framework Agnostic

Skills work with any agent framework that supports terminal access:
- Claude Code (primary)
- OpenCode (ChatGPT)
- Aider
- Cursor
- Custom agents

## Claude Code Agents

Optimized agent definitions for different task types:

| Agent | Model | Best For | Cost |
|-------|-------|----------|------|
| **coder** | Opus | Feature implementation, refactoring, complex logic | High |
| **explorer** | Haiku | Codebase search, file discovery, quick lookups | Low |
| **helper** | Sonnet | Planning, explanations, task organization | Medium |

Agent definitions are in `agents/`.

## Skill Development

### Creating New Skills

See `skills/skill-creator/SKILL.md` for guidelines on creating effective skills.

**Key principles:**
1. **Single responsibility** - One skill, one purpose
2. **Clear triggers** - Document phrases that invoke the skill
3. **Official tools** - Use Mozilla/standard tools where available
4. **Good documentation** - Clear examples and prerequisites
5. **Framework agnostic** - Should work beyond Claude Code

### Skill Structure

```
skills/skill-name/
├── SKILL.md          # Required: Skill documentation with YAML frontmatter
├── scripts/          # Optional: Helper scripts
│   └── *.py         # Python scripts with PEP 723 metadata
└── references/       # Optional: Additional documentation
    └── *.md
```

## Prerequisites

### System Requirements

- **uv/uvx**: Install from https://docs.astral.sh/uv/
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- **Python 3.10+**: For skill scripts

### Skill-Specific Requirements

Each skill has its own prerequisites. Check individual `SKILL.md` files:

- **lando**: Requires `~/.mozbuild/lando.toml` with API token
- **treeherder**: No prerequisites (read-only API access)
- **os-integrations**: Requires Firefox repository at `~/firefox`
- **jira**: Requires JIRA API credentials

## Contributing

### Adding Skills

1. Create skill directory: `skills/skill-name/`
2. Add `SKILL.md` with YAML frontmatter
3. Use official tools where available
4. Add helper scripts if needed (with PEP 723 metadata)
5. Update this README
6. Test with multiple agent frameworks

### Improving Skills

1. Keep documentation up-to-date
2. Use official tools and standard interfaces
3. Provide clear examples
4. Document prerequisites
5. Test across Claude Code and other agents

## Resources

- **Claude Code**: https://claude.com/claude-code
- **uv Documentation**: https://docs.astral.sh/uv/
- **Mozilla CI Docs**: https://firefox-source-docs.mozilla.org/
- **Treeherder**: https://treeherder.mozilla.org/
- **Lando**: https://moz-conduit.readthedocs.io/

## Support

- **Claude Code Issues**: https://github.com/anthropics/claude-code/issues
- **Skill Issues**: File in this repository
- **Mozilla Tools**: #moc-ci-support on Slack

## License

See individual skill licenses. Most skills use Mozilla Public License 2.0 or MIT.
