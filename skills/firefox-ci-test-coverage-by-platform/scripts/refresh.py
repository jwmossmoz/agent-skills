#!/usr/bin/env python3
"""
Refresh the skill's data snapshots from a Firefox source checkout.

Requires a Firefox checkout (shallow sparse clone is fine) with at minimum:
  - taskcluster/ (for tier config, test-sets, test-platforms, variants)
  - Test manifest directories (testing/, browser/, toolkit/, dom/, etc.)
    for skip-if parsing

Usage:
    python3 refresh.py <path-to-firefox-checkout>

Example:
    python3 refresh.py /path/to/firefox

The script will:
  1. Parse tier assignments (handle_tier + kind YAMLs + variants)
  2. Parse skip-if annotations from .toml test manifests
  3. Cross-reference tiers with skips
  4. Write updated JSON snapshots to the assets/ directory
"""

import re
import sys
import yaml
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).parent.parent / "assets"


def parse_tier1_platforms_from_source(tc_dir):
    """Parse the tier-1 platform list directly from handle_tier() in other.py.
    Falls back to the data snapshot if source is unavailable."""
    other_py = tc_dir / "gecko_taskgraph" / "transforms" / "test" / "other.py"
    if not other_py.exists():
        print("    Warning: could not find other.py, using existing snapshot for tier-1 platforms")
        snapshot = DATA_DIR / "tier_matrix.json"
        if snapshot.exists():
            return json.loads(snapshot.read_text(encoding="utf-8")).get("tier_1_platforms", [])
        return []

    content = other_py.read_text(encoding="utf-8")
    # Find the platform list inside handle_tier() between the [ and ]:
    # Look for the pattern: if task["test-platform"] in [\n ... \n]:
    match = re.search(
        r'if task\["test-platform"\] in \[\s*\n(.*?)\n\s*\]:',
        content, re.DOTALL
    )
    if not match:
        print("    Warning: could not parse handle_tier() platform list from other.py")
        return []

    block = match.group(1)
    platforms = re.findall(r'"([^"]+)"', block)
    print(f"    Parsed {len(platforms)} tier-1 platforms from other.py")
    return platforms
OS_LIST = ["linux", "win", "mac", "android"]


def platform_os(platform):
    if platform.startswith("linux"): return "Linux"
    elif platform.startswith("windows"): return "Windows"
    elif platform.startswith("macosx"): return "macOS"
    elif platform.startswith("android"): return "Android"
    return "Other"


# --- Tier parsing ---

def parse_kind_tiers(tc_dir):
    suite_tiers = {}
    kind_dir = tc_dir / "kinds" / "test"
    for yml_file in kind_dir.glob("*.yml"):
        if yml_file.name == "kind.yml":
            continue
        try:
            data = yaml.safe_load(yml_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for name, defn in data.items():
            if name == "task-defaults" or not isinstance(defn, dict):
                continue
            if "tier" in defn:
                suite_tiers[name] = defn["tier"]
    return suite_tiers


def parse_variant_overrides(tc_dir):
    data = yaml.safe_load((tc_dir / "test_configs" / "variants.yml").read_text(encoding="utf-8"))
    overrides = {}
    for name, defn in data.items():
        if not isinstance(defn, dict):
            continue
        replace = defn.get("replace", {})
        if isinstance(replace, dict) and "tier" in replace:
            overrides[name] = {
                "tier": replace["tier"],
                "when": defn.get("when", {}).get("$eval", "always"),
                "suffix": defn.get("suffix", name),
            }
    return overrides


def resolve_tier(suite, platform, suite_tiers, tier_1_set):
    if suite in suite_tiers:
        tier_def = suite_tiers[suite]
        if isinstance(tier_def, int):
            return tier_def
        if isinstance(tier_def, dict) and "by-test-platform" in tier_def:
            keyed = tier_def["by-test-platform"]
            for pattern, value in keyed.items():
                if pattern == "default":
                    continue
                if re.match(pattern, platform):
                    if isinstance(value, int):
                        return value
                    break
            default_val = keyed.get("default", "default")
            if isinstance(default_val, int):
                return default_val
    return 1 if platform in tier_1_set else 2


def get_test_platforms(tc_dir):
    data = yaml.safe_load((tc_dir / "test_configs" / "test-platforms.yml").read_text(encoding="utf-8"))
    return sorted(data.keys()) if data else []


def get_all_suites(tc_dir, suite_tiers):
    data = yaml.safe_load((tc_dir / "test_configs" / "test-sets.yml").read_text(encoding="utf-8"))
    all_suites = set()
    if data:
        for test_set, suites in data.items():
            if isinstance(suites, list):
                all_suites.update(suites)
    all_suites.update(suite_tiers.keys())
    return sorted(all_suites)


# --- Skip parsing ---

def infer_suite(rel_path):
    fname = Path(rel_path).name.lower()
    if "xpcshell" in fname: return "xpcshell"
    elif "browser" in fname: return "mochitest-browser-chrome"
    elif "mochitest" in fname: return "mochitest-plain"
    elif "chrome" in fname: return "mochitest-chrome"
    elif "a11y" in fname: return "mochitest-a11y"
    elif "reftest" in fname: return "reftest"
    elif "crashtest" in fname: return "crashtest"
    else: return fname.replace(".toml", "")


def extract_os(cond):
    targets = set()
    for m in re.finditer(r"os\s*==\s*['\"](\w+)['\"]", cond):
        targets.add(m.group(1))
    for m in re.finditer(r"os\s*!=\s*['\"](\w+)['\"]", cond):
        targets.update(set(OS_LIST) - {m.group(1)})
    if cond.strip() == "true":
        targets.update(OS_LIST)
    if re.match(r"^(debug|!debug|asan|tsan|verify|ccov)$", cond.strip()):
        targets.update(OS_LIST)
    return targets


def parse_skips(firefox_dir):
    """Returns (skip_keys, suite_totals) for cross-referencing."""
    import os as _os

    suite_totals = defaultdict(int)
    skip_keys = defaultdict(lambda: defaultdict(set))

    for f in firefox_dir.rglob("*.toml"):
        sf = str(f)
        if "node_modules" in sf or ".git" in sf:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel = str(f.relative_to(firefox_dir)).replace(_os.sep, "/")
        suite = infer_suite(rel)

        # Count all tests
        for line in content.split("\n"):
            m = re.match(r'\["?([^"\]]+)"?\]', line.strip())
            if m and m.group(1) != "DEFAULT":
                suite_totals[suite] += 1

        if "skip-if" not in content:
            continue

        cur = None
        in_skip = False
        for line in content.split("\n"):
            s = line.strip()
            if s.startswith("[") and not s.startswith("[["):
                tm = re.match(r'\["?([^"\]]+)"?\]', s)
                if tm:
                    cur = tm.group(1)
                in_skip = False
            if s.startswith("skip-if"):
                in_skip = True
                il = re.match(r'skip-if\s*=\s*\[(.+)\]', s)
                if il:
                    for c in re.findall(r'"([^"]+)"', il.group(1)):
                        k = rel + "::" + str(cur or "DEFAULT")
                        skip_keys[k][suite].update(extract_os(c))
                    in_skip = False
                    continue
            if in_skip:
                if s == "]":
                    in_skip = False
                    continue
                for c in re.findall(r'"([^"]+)"', s):
                    k = rel + "::" + str(cur or "DEFAULT")
                    skip_keys[k][suite].update(extract_os(c))

    return skip_keys, suite_totals


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    firefox_dir = Path(sys.argv[1])
    tc_dir = firefox_dir / "taskcluster"

    if not tc_dir.exists():
        print(f"Error: {tc_dir} not found. Provide a path to a Firefox checkout.", file=sys.stderr)
        sys.exit(1)

    print("Refreshing data snapshots...")
    print(f"  Firefox checkout: {firefox_dir}")

    # --- Tier matrix ---
    print("\n  Parsing tier configuration...")
    tier_1_platforms = parse_tier1_platforms_from_source(tc_dir)
    tier_1_set = set(tier_1_platforms)
    suite_tiers = parse_kind_tiers(tc_dir)
    variant_overrides = parse_variant_overrides(tc_dir)
    platforms = get_test_platforms(tc_dir)
    suites = get_all_suites(tc_dir, suite_tiers)

    os_groups = defaultdict(list)
    for p in platforms:
        os_groups[platform_os(p)].append(p)

    matrix = {}
    for suite in suites:
        matrix[suite] = {}
        for platform in platforms:
            matrix[suite][platform] = resolve_tier(suite, platform, suite_tiers, tier_1_set)

    tier_matrix = {
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "platforms": platforms,
        "platforms_by_os": dict(os_groups),
        "tier_1_platforms": tier_1_platforms,
        "suites": suites,
        "matrix": matrix,
        "variant_overrides": variant_overrides,
        "suite_tiers_from_kinds": {k: str(v) for k, v in suite_tiers.items()},
    }

    print(f"    Suites: {len(suites)}, Platforms: {len(platforms)}")

    # --- Skip data ---
    print("  Parsing skip-if annotations...")
    skip_keys, suite_totals_raw = parse_skips(firefox_dir)

    suite_skipped = defaultdict(int)
    suite_all_skip = defaultdict(int)
    suite_t1_affected = defaultdict(int)
    suite_skip_os = defaultdict(lambda: defaultdict(int))

    always_t2 = set()
    for s in suites:
        if all(matrix.get(s, {}).get(p, 2) >= 2 for p in platforms):
            always_t2.add(s)

    for key, suite_map in skip_keys.items():
        for suite, os_set in suite_map.items():
            suite_skipped[suite] += 1
            if all(o in os_set for o in OS_LIST):
                suite_all_skip[suite] += 1
            if suite not in always_t2 and os_set & {"linux", "win", "mac", "android"}:
                suite_t1_affected[suite] += 1
            for o in os_set:
                suite_skip_os[suite][o] += 1

    total_skipped = sum(suite_skipped.values())
    total_all = sum(suite_all_skip.values())
    total_t1 = sum(suite_t1_affected.values())

    skip_crossref = {
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "summary": {
            "total_skipped_tests": total_skipped,
            "skipped_all_platforms": total_all,
            "tier1_affected_skips": total_t1,
        },
        "suites": {
            suite: {
                "total_skipped": suite_skipped.get(suite, 0),
                "skipped_all_platforms": suite_all_skip.get(suite, 0),
                "tier1_affected": suite_t1_affected.get(suite, 0),
                "suite_always_tier2": suite in always_t2,
                "skips_by_os": dict(suite_skip_os.get(suite, {})),
            }
            for suite in sorted(set(list(suite_skipped.keys()) + suites))
        },
        "always_tier2_suites": sorted(always_t2),
    }

    skip_totals = {s: {"total": c} for s, c in suite_totals_raw.items()}

    print(f"    Tests with skips: {total_skipped}")
    print(f"    Skipped everywhere: {total_all}")

    # --- Write outputs ---
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    (DATA_DIR / "tier_matrix.json").write_text(json.dumps(tier_matrix, indent=2), encoding="utf-8")
    (DATA_DIR / "tier_skip_crossref.json").write_text(json.dumps(skip_crossref, indent=2), encoding="utf-8")
    (DATA_DIR / "skip_totals.json").write_text(json.dumps(skip_totals, indent=2), encoding="utf-8")

    print(f"\n  Data written to: {DATA_DIR}")
    print(f"  Snapshot date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    print("  Done.")


if __name__ == "__main__":
    main()
