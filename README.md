# Agent Skills

A collection of reusable skills for AI agents working with Mozilla Firefox development and CI infrastructure.

## Overview

This repository provides modular skills that enable AI agents to interact with Mozilla's development tools and CI systems. Skills use official Mozilla tools and libraries where available, with minimal custom wrappers.

## Skills

### CI and task management

- **taskcluster** — Status, logs, artifacts, retriggers, and in-tree actions for Firefox CI tasks
- **treeherder** — CI job results, failure analysis, and similar-job comparison via treeherder-cli + REST API
- **lando** — Poll the Lando API for landing job status
- **task-discovery** — List tasks assigned to a worker pool (migrations, audits, targeted try pushes)
- **os-integrations** — Firefox `mach try` with pre-configured alpha worker pool overrides

### Worker images

- **worker-image-build** — Trigger GitHub Actions workflows to build FXCI Windows worker images
- **worker-image-investigation** — Diagnose image-caused CI failures (cliffs, comparisons, debug VMs)

### Logs

- **papertrail** — In-VM worker logs from SolarWinds Observability via paperctl
- **splunk** — Azure activity logs (`index=azure_audit`) via browser-harness against Splunk Web
- **worker-ready-tracing** — End-to-end Azure VM request, in-VM boot scripts, and generic-worker ready timing

### Issue tracking

- **bugzilla** — Search, view, create, update, and comment on Mozilla Bugzilla bugs
- **jira** — Search, create, modify, and transition issues in Mozilla JIRA with Markdown→ADF

### Telemetry and data

- **bigquery** — Ad-hoc SQL against Mozilla telemetry tables via the bq CLI
- **redash** — Saved queries and shareable results from sql.telemetry.mozilla.org
- **azure-cost-duckdb** — Download Azure Cost Management exports from Blob Storage and query local Parquet with DuckDB
- **win11-files** — Local SQLite of Windows 11 cumulative-update file information

### Productivity

- **daily-log** — Compile a daily work log from Claude Code and Codex session JSONL files
- **expensify-remote-expenses** — Create recurring Mozilla home-internet and on-call phone expense-report drafts from current Mana guidance and authenticated billing portals
- **one-on-one** — Build topic-organized, linked 1:1/status bullets from `~/moz_artifacts` and copy them as rich text
- **self-review** — Draft evidence-backed performance self-reviews and copy final Markdown as rich review-form text

### Meta

- **skill-checker** — Validate Agent Skills with waza, skill-validator, and skill-check
- **writing-skills** — House style for authoring and maintaining the skills in this repo

For overlap boundaries between similar skills (`taskcluster` vs `task-discovery`, `redash` vs `bigquery`, `splunk` vs `papertrail` vs `tc-logview`, `worker-image-build` vs `worker-image-investigation`), see each skill's description and `## Related Skills` section.

## Subagents

- **agents/coder** - Code implementation specialist
- **agents/explorer** - Fast codebase discovery
- **agents/helper** - Planning, research, and explanation support

## Usage

### For Users

Once skills are installed, ask your agent naturally:

- "Show me my current sprint stories"
- "Check the treeherder status for my push"
- "Run os-integration tests on Windows 11"
- "Create a JIRA story for fixing the login bug"
- "Search bugzilla for crashes in Firefox"
- "File a bug for the startup regression"

The agent will invoke the appropriate skill and handle the technical details such as directory navigation and command execution.

### For Installation / Manual Use

#### Claude Code (preferred)

Use `npx skills` to install — it manages the canonical location at `~/.agents/skills/` and creates the symlinks Claude Code reads from `~/.claude/skills/`:

```bash
npx skills add jwmossmoz/agent-skills -g --agent '*' -y
```

Pass `--skill <name>` to install individual skills.

#### Manual symlinks (advanced)

If you don't want to use `npx skills`, symlink each skill manually:

```bash
AGENT_SKILLS_ROOT="/path/to/agent-skills"
for d in "$AGENT_SKILLS_ROOT"/skills/*/; do
  name=$(basename "$d")
  ln -sf "$d" "$HOME/.claude/skills/$name"
done

for f in "$AGENT_SKILLS_ROOT"/agents/*.md; do
  ln -sf "$f" "$HOME/.claude/agents/$(basename "$f")"
done
```

#### Other Agents

For Codex, OpenCode, or any other agent that supports skills, point it at this repo's `skills/` directory or symlink individual skill directories into the agent's configured skills path.

Each skill contains:
- `SKILL.md` - Full documentation and examples for the agent's reference
- `references/` - Optional supporting docs and examples
- `scripts/` - The actual implementation scripts

`uv.lock` files are tracked intentionally for reproducible Python dependencies.

## Design Principles

- **Official tools first** - Use Mozilla's official packages (`lando-cli`, `treeherder-client`, `mach`)
- **Isolated execution** - All Python tools use `uv`/`uvx` for dependency isolation
- **Single responsibility** - Each skill does one thing well
- **Framework agnostic** - Works with any agent framework that supports terminal access

## Requirements

- [uv](https://docs.astral.sh/uv/) - For running Python scripts in isolated environments
- Skill-specific prerequisites are documented in each `SKILL.md`
