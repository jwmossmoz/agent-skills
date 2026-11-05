# Agent Skills

A small collection of skills for Mozilla work logs, status updates, and performance reviews.

## Skills

### Work records and reporting

- **daily-log** — Compile Claude Code, Codex, and pi sessions into a concise daily work log.
- **one-on-one** — Turn indexed work notes into topic-based, linked manager updates.
- **self-review** — Draft evidence-based performance and promotion reviews.

## Use

Once installed, ask your agent naturally:

- "Compile yesterday's work log."
- "Prepare 1:1 bullets for the last two weeks."
- "Draft my annual self-review from my notes."

## Install

Use `npx skills` to install the three skills globally for supported agents:

```bash
npx skills add jwmossmoz/agent-skills -g --agent '*' \
  --skill daily-log --skill one-on-one --skill self-review -y
```

For manual installation, symlink selected directories from this repository's `skills/` directory into the agent's configured skills directory. Each skill has a `SKILL.md` and may include references, scripts, or evals.

## Requirements

See each skill's prerequisites. Requirements differ by workflow and agent.
