#!/usr/bin/env python3
"""
Firefox CI test health query tool.

Combines tier classification, skip matrix, and coverage data into
a single queryable interface for CI infrastructure teams.

Usage:
    python query.py suite <name>            Show tier + skip info for a suite
    python query.py platform <name>         Show all suites on a platform with tiers
    python query.py os <linux|windows|macos|android>  Show tier summary for an OS family
    python query.py risk                    Show tier-1 suites ranked by skip rate
    python query.py skipped-everywhere      Show tests with no coverage on any platform
    python query.py compare <plat1> <plat2> Compare tier assignments between platforms
    python query.py search <term>           Search suites/platforms by name
    python query.py summary                 Overall health summary
"""

import json
import sys
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load(name):
    path = DATA_DIR / name
    if not path.exists():
        print(f"Error: {path} not found. Run refresh.py to generate data.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_warning(tier_data, skip_data):
    """Print data freshness info."""
    tier_date = tier_data.get("snapshot_date", "unknown")
    skip_date = skip_data.get("snapshot_date", "unknown")
    print(f"  [Data snapshot: tiers={tier_date}, skips={skip_date}]")


def resolve_variant_applicability(variant_name, variant_info, suite_name, platform=None):
    """Best-effort check if a variant applies to a suite+platform combo.
    Returns: 'yes', 'no', or 'maybe' (when we can't fully evaluate the condition)."""
    when = variant_info.get("when", "")
    if not isinstance(when, str):
        return "maybe"
    if when == "always":
        return "yes"

    # Try to evaluate common patterns in the $eval expressions
    checks = []

    # Check suite/try-name references
    suite_patterns = re.findall(r'"([\w-]+)"\s*(?:==|in)\s*task\["try-name"\]', when)
    suite_patterns += re.findall(r'task\["try-name"\]\s*(?:==|in)\s*"([\w-]+)"', when)
    # Also handle: "foo" in task["try-name"]
    suite_in = re.findall(r'"([\w-]+)"\s+in\s+task\["try-name"\]', when)
    suite_patterns += suite_in

    if suite_patterns:
        suite_match = any(p == suite_name or p in suite_name for p in suite_patterns)
        if not suite_match:
            return "no"
        checks.append(True)

    # Check platform references
    if platform:
        plat_in = re.findall(r'"(\w+)"\s+in\s+task\["test-platform"\]', when)
        plat_eq = re.findall(r'task\["test-platform"\]\s*==\s*"([^"]+)"', when)
        plat_checks = plat_in + plat_eq
        if plat_checks:
            plat_match = any(p in platform for p in plat_checks)
            if not plat_match:
                return "no"
            checks.append(True)

    # If we matched some conditions but there are more we couldn't parse
    if checks:
        # Check for negation patterns we might have missed
        if "!" in when or "not" in when.lower():
            return "maybe"
        return "likely"

    return "maybe"


def cmd_suite(args):
    if not args:
        print("Usage: query.py suite <name>")
        return

    name = args[0].lower()
    tier_data = load("tier_matrix.json")
    skip_data = load("tier_skip_crossref.json")

    matches = [s for s in tier_data["suites"] if name in s.lower()]
    if not matches:
        print(f"No suites matching '{name}'")
        return

    snapshot_warning(tier_data, skip_data)

    for suite in matches:
        print(f"\n{'='*70}")
        print(f"Suite: {suite}")
        print(f"{'='*70}")

        matrix = tier_data["matrix"].get(suite, {})
        os_groups = tier_data["platforms_by_os"]

        for os_name in ["Linux", "Windows", "macOS", "Android"]:
            plats = os_groups.get(os_name, [])
            if not plats:
                continue
            tiers = {p: matrix.get(p, "?") for p in plats}
            t1 = [p for p, t in tiers.items() if t == 1]
            t2 = [p for p, t in tiers.items() if t == 2]
            t3 = [p for p, t in tiers.items() if t == 3]

            print(f"\n  {os_name}:")
            if t1:
                print(f"    Tier 1 ({len(t1)} platforms): {', '.join(sorted(t1)[:5])}")
                if len(t1) > 5:
                    print(f"      ... and {len(t1)-5} more")
            if t2:
                print(f"    Tier 2 ({len(t2)} platforms): {', '.join(sorted(t2)[:5])}")
                if len(t2) > 5:
                    print(f"      ... and {len(t2)-5} more")
            if t3:
                print(f"    Tier 3 ({len(t3)} platforms)")

        # Skip info
        skip_info = skip_data.get("suites", {}).get(suite)
        if skip_info and skip_info.get("total_skipped", 0) > 0:
            print(f"\n  Skip Summary:")
            print(f"    Tests with skips:       {skip_info['total_skipped']}")
            print(f"    Skipped everywhere:     {skip_info['skipped_all_platforms']}")
            print(f"    Affecting tier-1:       {skip_info['tier1_affected']}")
            by_os = skip_info.get("skips_by_os", {})
            if by_os:
                print(f"    By OS: Linux={by_os.get('linux',0)}, Windows={by_os.get('win',0)}, macOS={by_os.get('mac',0)}, Android={by_os.get('android',0)}")
        else:
            print(f"\n  Skip Summary: No skip-if annotations found")

        # Variant overrides with applicability check
        variants = tier_data.get("variant_overrides", {})
        if variants:
            print(f"\n  Variant Overrides:")
            for vname, vinfo in sorted(variants.items()):
                applicability = resolve_variant_applicability(vname, vinfo, suite)
                if applicability == "no":
                    continue
                tag = ""
                if applicability == "yes":
                    tag = " [APPLIES]"
                elif applicability == "likely":
                    tag = " [LIKELY APPLIES]"
                elif applicability == "maybe":
                    tag = " [MAY APPLY - condition too complex to resolve statically]"
                print(f"    {vname} -> forces tier {vinfo['tier']}{tag}")


def cmd_platform(args):
    if not args:
        print("Usage: query.py platform <name>")
        return

    name = args[0].lower()
    tier_data = load("tier_matrix.json")
    skip_data = load("tier_skip_crossref.json")

    matches = [p for p in tier_data["platforms"] if name in p.lower()]
    if not matches:
        print(f"No platforms matching '{name}'")
        return

    snapshot_warning(tier_data, skip_data)

    for platform in matches:
        print(f"\n{'='*70}")
        print(f"Platform: {platform}")
        is_t1 = platform in set(tier_data.get("tier_1_platforms", []))
        print(f"Default tier: {'1 (must-pass)' if is_t1 else '2 (secondary)'}")
        print(f"{'='*70}")

        t1_suites = []
        t2_suites = []
        t3_suites = []

        for suite in tier_data["suites"]:
            tier = tier_data["matrix"].get(suite, {}).get(platform, "?")
            if tier == 1:
                t1_suites.append(suite)
            elif tier == 2:
                t2_suites.append(suite)
            elif tier == 3:
                t3_suites.append(suite)

        print(f"\n  Tier 1 ({len(t1_suites)} suites -- must pass before code lands):")
        for s in sorted(t1_suites):
            print(f"    {s}")

        print(f"\n  Tier 2 ({len(t2_suites)} suites -- secondary):")
        for s in sorted(t2_suites):
            print(f"    {s}")

        if t3_suites:
            print(f"\n  Tier 3 ({len(t3_suites)} suites -- experimental):")
            for s in sorted(t3_suites):
                print(f"    {s}")


def cmd_os(args):
    """Show tier summary for an entire OS family."""
    if not args:
        print("Usage: query.py os <linux|windows|macos|android>")
        return

    os_input = args[0].lower()
    # Normalize input
    os_map = {
        "linux": "Linux", "lin": "Linux",
        "windows": "Windows", "win": "Windows",
        "macos": "macOS", "mac": "macOS", "osx": "macOS",
        "android": "Android", "andr": "Android",
    }
    os_name = os_map.get(os_input)
    if not os_name:
        print(f"Unknown OS '{os_input}'. Use: linux, windows, macos, android")
        return

    tier_data = load("tier_matrix.json")
    skip_data = load("tier_skip_crossref.json")

    snapshot_warning(tier_data, skip_data)

    os_groups = tier_data["platforms_by_os"]
    plats = os_groups.get(os_name, [])
    t1_plats_set = set(tier_data.get("tier_1_platforms", []))

    if not plats:
        print(f"No platforms found for {os_name}")
        return

    t1_plats = [p for p in plats if p in t1_plats_set]
    t2_plats = [p for p in plats if p not in t1_plats_set]

    print(f"\n{'='*70}")
    print(f"OS Family: {os_name}")
    print(f"{'='*70}")
    print(f"\n  Platforms: {len(plats)} ({len(t1_plats)} tier 1, {len(t2_plats)} tier 2)")

    print(f"\n  Tier 1 platforms:")
    for p in sorted(t1_plats):
        print(f"    {p}")
    print(f"\n  Tier 2 platforms:")
    for p in sorted(t2_plats):
        print(f"    {p}")

    # Suite summary for this OS: which suites are T1 on at least one platform here
    t1_suites = set()
    t2_only_suites = set()
    t3_suites = set()

    for suite in tier_data["suites"]:
        tiers_here = set()
        for p in plats:
            t = tier_data["matrix"].get(suite, {}).get(p, 2)
            tiers_here.add(t)
        if 1 in tiers_here:
            t1_suites.add(suite)
        elif 3 in tiers_here and 2 not in tiers_here:
            t3_suites.add(suite)
        else:
            t2_only_suites.add(suite)

    print(f"\n  Suites with Tier 1 on {os_name}: {len(t1_suites)}")
    print(f"  Suites always Tier 2 on {os_name}: {len(t2_only_suites)}")
    if t3_suites:
        print(f"  Suites at Tier 3 on {os_name}: {len(t3_suites)}")

    # Skip info for suites with T1 on this OS
    os_key = {"Linux": "linux", "Windows": "win", "macOS": "mac", "Android": "android"}[os_name]
    print(f"\n  {'Suite':<40} {'Tier':>6} {'Skips on ' + os_name:>16}")
    print(f"  {'-'*65}")

    rows = []
    for suite in sorted(t1_suites):
        skip_info = skip_data.get("suites", {}).get(suite, {})
        os_skips = skip_info.get("skips_by_os", {}).get(os_key, 0)
        rows.append((suite, "T1", os_skips))
    for suite in sorted(t2_only_suites):
        skip_info = skip_data.get("suites", {}).get(suite, {})
        os_skips = skip_info.get("skips_by_os", {}).get(os_key, 0)
        if os_skips > 0:
            rows.append((suite, "T2", os_skips))

    rows.sort(key=lambda r: -r[2])
    for suite, tier, skips in rows:
        if skips > 0:
            print(f"  {suite:<40} {tier:>6} {skips:>16}")


def cmd_risk(args):
    """Show tier-1 suites ranked by skip rate."""
    skip_data = load("tier_skip_crossref.json")
    tier_data = load("tier_matrix.json")
    skip_totals = load("skip_totals.json")

    snapshot_warning(tier_data, skip_data)

    print(f"\n{'='*70}")
    print(f"Tier-1 Suites Ranked by Skip Rate (highest risk first)")
    print(f"{'='*70}")
    print(f"{'Suite':<40} {'Skipped':>8} {'Total':>8} {'Rate':>7} {'All-Plat':>9}")
    print("-" * 75)

    rows = []
    for suite, info in skip_data.get("suites", {}).items():
        if info.get("suite_always_tier2"):
            continue
        total = skip_totals.get(suite, {}).get("total", 0)
        skipped = info.get("total_skipped", 0)
        rate = (skipped / total * 100) if total > 0 else 0
        all_plat = info.get("skipped_all_platforms", 0)
        if skipped > 0:
            rows.append((suite, skipped, total, rate, all_plat))

    rows.sort(key=lambda r: -r[3])
    for suite, skipped, total, rate, all_plat in rows:
        print(f"{suite:<40} {skipped:>8} {total:>8} {rate:>6.1f}% {all_plat:>9}")


def cmd_skipped_everywhere(args):
    """Show suites with tests skipped on all platforms."""
    skip_data = load("tier_skip_crossref.json")
    tier_data = load("tier_matrix.json")

    snapshot_warning(tier_data, skip_data)

    print(f"\n{'='*70}")
    print(f"Tests Skipped on ALL Platforms (complete coverage gaps)")
    print(f"{'='*70}")
    print(f"{'Suite':<40} {'All-Skip':>9} {'Total Skipped':>14}")
    print("-" * 65)

    total_all = 0
    for suite in sorted(skip_data.get("suites", {}).keys()):
        info = skip_data["suites"][suite]
        if info.get("skipped_all_platforms", 0) > 0:
            print(f"{suite:<40} {info['skipped_all_platforms']:>9} {info['total_skipped']:>14}")
            total_all += info["skipped_all_platforms"]

    print("-" * 65)
    print(f"{'TOTAL':<40} {total_all:>9}")


def cmd_compare(args):
    if len(args) < 2:
        print("Usage: query.py compare <platform1> <platform2>")
        return

    tier_data = load("tier_matrix.json")
    p1_name, p2_name = args[0].lower(), args[1].lower()

    p1_matches = [p for p in tier_data["platforms"] if p1_name in p.lower()]
    p2_matches = [p for p in tier_data["platforms"] if p2_name in p.lower()]

    if not p1_matches or not p2_matches:
        print(f"Could not find platforms. Matches: {p1_matches[:3]}, {p2_matches[:3]}")
        return

    p1, p2 = p1_matches[0], p2_matches[0]

    snapshot_warning(tier_data, load("tier_skip_crossref.json"))

    print(f"\n{'='*70}")
    print(f"Comparing: {p1} vs {p2}")
    print(f"{'='*70}")

    diffs = []
    same = 0
    for suite in tier_data["suites"]:
        t1 = tier_data["matrix"].get(suite, {}).get(p1, "?")
        t2 = tier_data["matrix"].get(suite, {}).get(p2, "?")
        if t1 != t2:
            diffs.append((suite, t1, t2))
        else:
            same += 1

    print(f"\n  Same tier on both: {same} suites")
    if diffs:
        print(f"  Different tier: {len(diffs)} suites\n")
        print(f"  {'Suite':<40} {p1[:20]:>20} {p2[:20]:>20}")
        print(f"  {'-'*80}")
        for suite, t1, t2 in sorted(diffs):
            print(f"  {suite:<40} {'Tier '+str(t1):>20} {'Tier '+str(t2):>20}")
    else:
        print(f"\n  All suites have identical tiers on both platforms.")


def cmd_search(args):
    if not args:
        print("Usage: query.py search <term>")
        return

    term = args[0].lower()
    tier_data = load("tier_matrix.json")

    suites = [s for s in tier_data["suites"] if term in s.lower()]
    plats = [p for p in tier_data["platforms"] if term in p.lower()]

    if suites:
        print(f"\nSuites matching '{term}': {len(suites)}")
        for s in sorted(suites):
            print(f"  {s}")
    if plats:
        print(f"\nPlatforms matching '{term}': {len(plats)}")
        for p in sorted(plats):
            t1 = "(Tier 1)" if p in set(tier_data.get("tier_1_platforms", [])) else "(Tier 2)"
            print(f"  {p} {t1}")
    if not suites and not plats:
        print(f"No suites or platforms matching '{term}'")


def cmd_summary(args):
    tier_data = load("tier_matrix.json")
    skip_data = load("tier_skip_crossref.json")

    suites = tier_data["suites"]
    platforms = tier_data["platforms"]
    t1_plats = set(tier_data.get("tier_1_platforms", []))

    print(f"\n{'='*70}")
    print(f"Firefox CI Test Health Summary")
    print(f"{'='*70}")

    snapshot_warning(tier_data, skip_data)

    print(f"\n  Suites:    {len(suites)}")
    print(f"  Platforms: {len(platforms)} ({len(t1_plats)} tier 1, {len(platforms)-len(t1_plats)} tier 2)")

    # Per-OS breakdown
    os_groups = tier_data.get("platforms_by_os", {})
    for os_name in ["Linux", "Windows", "macOS", "Android"]:
        plats = os_groups.get(os_name, [])
        t1 = sum(1 for p in plats if p in t1_plats)
        print(f"    {os_name}: {len(plats)} platforms ({t1} tier 1)")

    summary = skip_data.get("summary", {})
    print(f"\n  Tests with skip-if:          {summary.get('total_skipped_tests', '?')}")
    print(f"  Skipped on all platforms:     {summary.get('skipped_all_platforms', '?')}")
    print(f"  Affecting tier-1 platforms:   {summary.get('tier1_affected_skips', '?')}")

    # Variant overrides
    variants = tier_data.get("variant_overrides", {})
    if variants:
        print(f"\n  Variant tier overrides: {len(variants)}")
        for name, info in sorted(variants.items()):
            print(f"    {name} -> tier {info['tier']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    commands = {
        "suite": cmd_suite,
        "platform": cmd_platform,
        "os": cmd_os,
        "risk": cmd_risk,
        "skipped-everywhere": cmd_skipped_everywhere,
        "compare": cmd_compare,
        "search": cmd_search,
        "summary": cmd_summary,
    }

    if cmd in commands:
        commands[cmd](args)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
