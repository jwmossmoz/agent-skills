---
name: firefox-ci-test-coverage-by-platform
description: Query Firefox CI test health — tier classification, skip rates, coverage gaps, and platform comparisons. Use when analyzing which tests matter on which platforms, planning OS pool migrations, or investigating test coverage gaps.
when_to_use: tier lookup, skip rates, coverage gaps, pool comparisons, green-up planning, platform decommission, test suite analysis, CI infrastructure planning
argument-hint: [command] [query]
allowed-tools: Read Bash(python ${CLAUDE_SKILL_DIR}/scripts/*)
---

# Firefox CI Test Coverage by Platform

Understand what tests matter on which platforms across Firefox CI.

This skill gives CI infrastructure teams quick answers to questions like:
- **"What's tier 1 on Windows 11?"** — Which test suites must pass before code lands on a given platform
- **"What happens if we decommission this pool?"** — Compare tier coverage between two platforms
- **"Where are our biggest coverage gaps?"** — Find tier-1 suites with the highest skip rates
- **"Tell me about mochitest-browser-chrome"** — Full picture: tiers per OS, skip rates, variant overrides
- **"Show me everything about Android"** — All platforms, tier breakdown, skip hotspots for an OS family

It also surfaces the **three-layer tier override system** (variant overrides > kind YAML > handle_tier defaults) that can silently change which tier a suite runs at — critical context when planning pool migrations or greening up new OS images.

## Quick start

Just ask a question naturally after invoking the skill:

```
/firefox-ci-test-coverage-by-platform what's tier 1 on windows 11?
/firefox-ci-test-coverage-by-platform tell me about xpcshell
/firefox-ci-test-coverage-by-platform show me android
/firefox-ci-test-coverage-by-platform what are the riskiest coverage gaps?
/firefox-ci-test-coverage-by-platform compare windows10 vs windows11
```

Or use the query tool directly:

| Command | What it does |
|---|---|
| `summary` | Overall health numbers, platform counts, variant overrides |
| `suite <name>` | Tier per OS, skip rates, applicable variant overrides |
| `platform <name>` | All suites on that platform grouped by tier |
| `os <windows/linux/macos/android>` | Full OS family breakdown with skip hotspots |
| `risk` | Tier-1 suites ranked by skip rate (highest risk first) |
| `skipped-everywhere` | Tests with zero coverage on any platform |
| `compare <plat1> <plat2>` | Side-by-side tier differences between platforms |
| `search <term>` | Find suites or platforms by name |

## Data freshness warning

The data in this skill is a **point-in-time snapshot**. Check the `snapshot_date` field in the JSON files under `data/` for when it was last refreshed. Skip counts, tier assignments, and platform lists can change as Firefox CI config evolves. If the data is more than a few weeks old, consider running a refresh (see Refresh section below).

## How tiers work (important context)

Tier assignment follows three layers of precedence. Understanding this is critical because overrides can silently change what you expect:

1. **Variant overrides** (highest priority) — `variants.yml` uses `replace: tier:` to force a tier when a variant is active. For example, `a11y-checks` forces tier 2, `async-event-dispatching` forces tier 3. These apply regardless of platform or suite.

2. **Kind task definitions** — Files in `kinds/test/*.yml` can set an explicit tier per suite, sometimes keyed by platform. For example, `firefox-ui-functional` is always tier 2, all `talos-*-profiling` suites are always tier 2, `xpcshell-failures` is tier 3.

3. **`handle_tier()` default** (lowest priority) — A hardcoded list of ~51 platforms get tier 1, everything else gets tier 2. Most suites (mochitest, xpcshell, reftest, web-platform-tests, etc.) have no explicit tier and fall through entirely to this layer.

This means the **same suite can be tier 1 on one platform and tier 2 on another**, and a variant can bump it further. Always check the full picture.

## Commands

Run the query tool to answer questions:

```
python ${CLAUDE_SKILL_DIR}/scripts/query.py <command> [args]
```

### Look up a suite
```
python ${CLAUDE_SKILL_DIR}/scripts/query.py suite mochitest-browser-chrome
```
Shows tier assignment per OS/platform, skip rates, skipped-everywhere count, and any variant overrides that affect it.

### Look up a platform
```
python ${CLAUDE_SKILL_DIR}/scripts/query.py platform windows11-64-24h2/opt
```
Lists all tier-1 and tier-2 suites on that platform.

### Risk view — tier-1 suites ranked by skip rate
```
python ${CLAUDE_SKILL_DIR}/scripts/query.py risk
```
Shows which tier-1 suites have the most skipped tests — these are the highest-risk coverage gaps.

### Tests skipped on ALL platforms
```
python ${CLAUDE_SKILL_DIR}/scripts/query.py skipped-everywhere
```
Complete coverage gaps — tests with no coverage anywhere.

### Show an OS family
```
python ${CLAUDE_SKILL_DIR}/scripts/query.py os windows
```
Shows all platforms for that OS, which are tier 1 vs 2, suites with tier-1 on that OS, and skip counts. Accepts: linux, windows, macos, android.

### Compare two platforms
```
python ${CLAUDE_SKILL_DIR}/scripts/query.py compare windows11-64-24h2/opt linux2404-64/opt
```
Shows which suites differ in tier between the two platforms.

### Search by name
```
python ${CLAUDE_SKILL_DIR}/scripts/query.py search mochitest
```
Fuzzy search across suite and platform names.

### Overall summary
```
python ${CLAUDE_SKILL_DIR}/scripts/query.py summary
```

## Data sources

This skill uses pre-parsed snapshots of Firefox CI configuration:
- **tier_matrix.json** — Suite x platform tier assignments (from `handle_tier()`, kind YAMLs, and variant overrides)
- **tier_skip_crossref.json** — Skip counts cross-referenced with tier classification
- **skip_totals.json** — Total test counts per suite for percentage calculations

## Refreshing the data

To update the snapshots, you need a local Firefox checkout and PyYAML.

**Prerequisites:**
- Python 3.8+
- `pip install pyyaml` (only needed for refresh, not for querying)

A shallow sparse clone is sufficient — no full history required.

### Step 1: Clone Firefox (if you don't have it)

```bash
git clone --depth 1 --sparse https://github.com/mozilla-firefox/firefox.git
cd firefox
git sparse-checkout add taskcluster testing toolkit dom browser layout gfx image js devtools editor netwerk security widget extensions ipc mobile accessible docshell modules remote tools xpcom
```

This pulls only the current tree (no history) and only the directories needed for parsing.

**Required directories:**
- `taskcluster/` — tier config, test-sets, test-platforms, variants, kind definitions
- All others — contain `.toml` test manifests with `skip-if` annotations

### Step 2: Run the refresh

```bash
python ${CLAUDE_SKILL_DIR}/scripts/refresh.py /path/to/firefox
```

This will regenerate all three JSON files in the `data/` directory with a new snapshot date. The refresh script parses the tier-1 platform list directly from `handle_tier()` in `other.py`, so it picks up any changes to which platforms are tier 1.

### Step 3: Update an existing checkout

If you already have the Firefox clone, just pull the latest:

```bash
cd /path/to/firefox
git fetch --depth 1 origin
git reset --hard origin/HEAD
```

Then re-run the refresh script.

## Key numbers (baseline snapshot)

- 143 suites, 64 platforms (51 tier 1, 13 tier 2)
- 3,262 tests with skip-if annotations
- 476 skipped on all platforms (complete coverage gaps)
- 2,499 skips affecting tier-1 platforms
- 5 variant overrides that can bump tiers
