---
name: firefox-ci-test-coverage-by-platform
description: "Use when querying Firefox CI test health by platform: tier classification, skip rates, coverage gaps, pool comparisons, green-up planning, platform decommissioning, test suite analysis, or CI infrastructure planning."
allowed-tools: "Read Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)"
---

# Firefox CI Test Coverage by Platform

Use `query.py` first; it reads snapshots from `assets/`.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/query.py <command> [args]
```

## USE FOR:

Tier lookup, skip rates, coverage gaps, pool comparisons, green-up planning, platform retirement, and suite coverage analysis.

## DO NOT USE FOR:

Live Taskcluster job status, try pushes, or refreshing stale snapshots unless the user asks.

## Commands

Use `summary`, `suite <name>`, `platform <name>`, `os <linux|windows|macos|android>`, `risk`, `skipped-everywhere`, `compare <platform1> <platform2>`, or `search <term>`.

## Examples

- "What's tier 1 on Windows 11?" Run `platform windows11` or `os windows`.
- "Tell me about xpcshell." Run `suite xpcshell`.
- "Riskiest coverage gaps?" Run `risk`.
- "Can we retire this pool?" Run `compare <old> <new>`.

## Tier Model

Tier precedence: variant overrides, kind YAML tier settings, then the `handle_tier()` platform default. The same suite can have different tiers by platform.

## Data Freshness

Check each snapshot's `snapshot_date` before migration or green-up decisions. Refresh stale data with [references/refresh.md](references/refresh.md).

## Troubleshooting

- Missing snapshots: confirm `assets/tier_matrix.json`, `assets/tier_skip_crossref.json`, and `assets/skip_totals.json`.
- Stale data: refresh before release or pool-retirement decisions.
- No match: run `search <term>` for the canonical name.
- Refresh import errors: install PyYAML, then rerun `scripts/refresh.py`.
