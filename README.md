# agent-skills

Claude Code skills for the Mozilla RelOps team. Each skill gives agents the context and tooling to work with Mozilla's telemetry, CI, and infrastructure systems.

## Installation

Install all skills:

```bash
npx skills add mozilla-platform-ops/agent-skills
```

Install a specific skill:

```bash
npx skills add mozilla-platform-ops/agent-skills/<skill-name>
```

## Available Skills

| Skill | Description |
|-------|-------------|
| [queue-diagnosis](skills/queue-diagnosis/) | Diagnose large Taskcluster worker-pool queues by combining live Taskcluster pool state with Redash/BigQuery demand analysis. Produces a supply-side, demand-side, mixed, or inconclusive verdict with supporting evidence. |
| [redash](skills/redash/) | Query Mozilla's Redash (sql.telemetry.mozilla.org) for Firefox telemetry and FXCI task data. Covers OS version distribution, DAU/MAU, architecture breakdown, worker-pool queue time, and task-level CI analysis. Requires only a Redash API key. |

## Adding New Skills

1. Create `skills/<skill-name>/` directory
2. Add `SKILL.md` with YAML frontmatter (`name` and `description`)
3. Add optional `references/`, `scripts/`, or `assets/` subdirectories
4. Update this README's Available Skills table
5. Test with `npx skills add`

## License

MPL-2.0 except where noted. Individual skills may use different licenses; check the LICENSE file in each skill directory.

## Links

- [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code)
- [Mozilla Platform Operations](https://github.com/mozilla-platform-ops)
