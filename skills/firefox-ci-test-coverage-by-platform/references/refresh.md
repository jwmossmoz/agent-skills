# Refreshing Test Coverage Data

Use this only when the bundled snapshots in `assets/` are stale.

## Prerequisites

- Python 3.8 or newer
- PyYAML in the refresh environment
- A Firefox checkout with `taskcluster/` and test manifest directories

Install PyYAML if needed:

```bash
python3 -m pip install "pyyaml>=6.0"
```

## Sparse Firefox Checkout

A shallow sparse clone is enough:

```bash
git clone --depth 1 --sparse https://github.com/mozilla-firefox/firefox.git
cd firefox
git sparse-checkout add taskcluster testing toolkit dom browser layout gfx image js devtools editor netwerk security widget extensions ipc mobile accessible docshell modules remote tools xpcom
```

Required inputs:

- `taskcluster/` for tier config, test sets, test platforms, variants, and kind definitions
- Test manifest directories for `.toml` files with `skip-if` annotations

## Refresh

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/refresh.py /path/to/firefox
```

The script regenerates:

- `assets/tier_matrix.json`
- `assets/tier_skip_crossref.json`
- `assets/skip_totals.json`

## Existing Checkout

```bash
cd /path/to/firefox
git fetch --depth 1 origin
git reset --hard origin/HEAD
python3 ${CLAUDE_SKILL_DIR}/scripts/refresh.py /path/to/firefox
```
