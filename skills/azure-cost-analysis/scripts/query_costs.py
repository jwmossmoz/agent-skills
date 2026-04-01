#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Query Azure Cost Management API for FXCI costs grouped by worker-pool-id.

Requires: az CLI authenticated with access to the target subscription.

Usage:
    uv run query_costs.py --start 2026-01-01 --end 2026-03-31 --granularity monthly
    uv run query_costs.py --start 2026-03-01 --end 2026-03-31 --granularity daily
    uv run query_costs.py --start 2026-01-01 --end 2026-03-31 --compare-months
    uv run query_costs.py --start 2026-03-01 --end 2026-03-31 --output costs.json
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

FXCI_SUBSCRIPTION = "108d46d5-fe9b-4850-9a7d-8c914aa6c1f0"


def query_costs(subscription, start, end, granularity="Monthly"):
    """Query the Cost Management REST API."""
    body = json.dumps({
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": start, "to": end},
        "dataset": {
            "granularity": granularity,
            "aggregation": {
                "totalCost": {"name": "Cost", "function": "Sum"},
            },
            "grouping": [
                {"type": "TagKey", "name": "worker-pool-id"},
            ],
        },
    })
    url = (
        f"https://management.azure.com/subscriptions/{subscription}"
        "/providers/Microsoft.CostManagement/query"
        "?api-version=2023-11-01"
    )
    result = subprocess.run(
        ["az", "rest", "--method", "post", "--url", url, "--body", body],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def parse_rows_monthly(data):
    """Parse monthly granularity rows into {pool: {month: cost}}."""
    pools = {}
    for row in data["properties"]["rows"]:
        cost, month_str, _tag_key, tag_val, _currency = row
        pool = tag_val if tag_val else "(untagged)"
        month = month_str[:7]
        pools.setdefault(pool, {})[month] = (
            pools.get(pool, {}).get(month, 0) + cost
        )
    return pools


def parse_rows_daily(data):
    """Parse daily granularity rows into {pool: {date: cost}}."""
    pools = {}
    for row in data["properties"]["rows"]:
        cost, date_int, _tag_key, tag_val, _currency = row
        pool = tag_val if tag_val else "(untagged)"
        d = str(date_int)
        date_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        pools.setdefault(pool, {})[date_str] = (
            pools.get(pool, {}).get(date_str, 0) + cost
        )
    return pools


def print_monthly(pools, top_n):
    """Print monthly cost table sorted by total spend."""
    totals = {p: sum(m.values()) for p, m in pools.items()}
    sorted_pools = sorted(totals.items(), key=lambda x: -x[1])
    months = sorted({m for dates in pools.values() for m in dates})

    # Monthly totals
    print("Monthly Totals:")
    for month in months:
        total = sum(pools[p].get(month, 0) for p in pools)
        print(f"  {month}: ${total:>12,.2f}")

    # Table header
    month_hdrs = " ".join(f"{m:>12}" for m in months)
    print(f"\n{'Pool':<50} {month_hdrs} {'Total':>12}")
    print(f"{'-' * 50} {' '.join('-' * 12 for _ in months)} {'-' * 12}")

    for pool, total in sorted_pools[:top_n]:
        if total < 1:
            continue
        vals = " ".join(
            f"${pools[pool].get(m, 0):>10,.0f}" for m in months
        )
        print(f"{pool:<50} {vals} ${total:>10,.0f}")


def print_monthly_comparison(pools, top_n):
    """Print month-over-month comparison with deltas."""
    months = sorted({m for dates in pools.values() for m in dates})
    if len(months) < 2:
        print("Need at least 2 months for comparison.", file=sys.stderr)
        return

    first, last = months[0], months[-1]
    first_total = sum(pools[p].get(first, 0) for p in pools)
    last_total = sum(pools[p].get(last, 0) for p in pools)

    print(f"Period: {first} to {last}")
    print(f"  {first}: ${first_total:>12,.2f}")
    print(f"  {last}:  ${last_total:>12,.2f}")
    if first_total > 0:
        pct = (last_total - first_total) / first_total * 100
        print(f"  Change: ${last_total - first_total:>+12,.2f} ({pct:+.1f}%)")

    # Compute deltas
    deltas = []
    for pool, dates in pools.items():
        c_first = dates.get(first, 0)
        c_last = dates.get(last, 0)
        deltas.append((pool, c_first, c_last, c_last - c_first))

    deltas.sort(key=lambda x: -x[3])

    print(f"\nTop {top_n} pools by increase ({first} -> {last}):")
    print(f"{'Pool':<50} {first:>12} {last:>12} {'Delta':>12}")
    print(f"{'-' * 50} {'-' * 12} {'-' * 12} {'-' * 12}")
    for pool, c_f, c_l, delta in deltas[:top_n]:
        if delta < 1:
            continue
        print(f"{pool:<50} ${c_f:>10,.0f} ${c_l:>10,.0f} ${delta:>+10,.0f}")

    # New pools
    new_pools = [
        (p, cf, cl, d)
        for p, cf, cl, d in deltas
        if cf < 1 and cl > 10
    ]
    if new_pools:
        print(f"\nNew pools (appeared after {first}):")
        for pool, _, c_last, _ in new_pools:
            print(f"  {pool:<50} ${c_last:>10,.0f}")


def print_daily(pools, top_n):
    """Print daily cost table for the top pools."""
    totals = {p: sum(d.values()) for p, d in pools.items()}
    top_pools = [
        p for p, _ in sorted(totals.items(), key=lambda x: -x[1])[:top_n]
    ]
    all_dates = sorted({d for dates in pools.values() for d in dates})

    for pool in top_pools:
        if totals[pool] < 1:
            continue
        print(f"\n{pool} (total: ${totals[pool]:,.0f})")
        print(f"{'Date':<12} {'Cost':>10}")
        print(f"{'-' * 12} {'-' * 10}")

        prev = 0
        for date in all_dates:
            cost = pools[pool].get(date, 0)
            if cost < 0.01:
                continue
            dow = datetime.strptime(date, "%Y-%m-%d").strftime("%a")
            marker = " << spike" if prev > 0 and cost > prev * 1.8 else ""
            print(f"{date} {dow} ${cost:>8,.0f}{marker}")
            prev = cost

    # Weekly averages for top 2 pools combined
    if len(top_pools) >= 2:
        print(f"\nWeekly averages ({top_pools[0]} + {top_pools[1]}):")
        weeks = {}
        for date in all_dates:
            dt = datetime.strptime(date, "%Y-%m-%d")
            wk = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
            cost = sum(pools[p].get(date, 0) for p in top_pools[:2])
            weeks.setdefault(wk, {"total": 0, "days": 0})
            weeks[wk]["total"] += cost
            weeks[wk]["days"] += 1

        print(f"{'Week of':<12} {'Total':>10} {'Daily Avg':>10}")
        for wk in sorted(weeks):
            w = weeks[wk]
            print(
                f"{wk:<12} ${w['total']:>8,.0f}"
                f" ${w['total'] / w['days']:>8,.0f}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Query FXCI Azure costs by worker-pool-id",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--start", required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end", required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--granularity", "-g",
        choices=["monthly", "daily"],
        default="monthly",
        help="Granularity (default: monthly)",
    )
    parser.add_argument(
        "--compare-months", action="store_true",
        help="Show month-over-month deltas",
    )
    parser.add_argument(
        "--top", type=int, default=25,
        help="Number of top pools to display (default: 25)",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Save raw API response as JSON",
    )
    parser.add_argument(
        "--subscription",
        default=FXCI_SUBSCRIPTION,
        help="Azure subscription ID",
    )

    args = parser.parse_args()
    gran = "Monthly" if args.granularity == "monthly" else "Daily"

    # For daily queries spanning multiple months, query each month separately
    if gran == "Daily":
        start_dt = datetime.strptime(args.start, "%Y-%m-%d")
        end_dt = datetime.strptime(args.end, "%Y-%m-%d")
        all_pools = {}

        current = start_dt.replace(day=1)
        while current <= end_dt:
            month_end = (current.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            if month_end > end_dt:
                month_end = end_dt
            print(
                f"Querying {current.strftime('%Y-%m')}...",
                file=sys.stderr,
            )
            data = query_costs(
                args.subscription,
                current.strftime("%Y-%m-%d"),
                month_end.strftime("%Y-%m-%d"),
                gran,
            )
            if args.output:
                # Save last response
                pass
            for pool, dates in parse_rows_daily(data).items():
                all_pools.setdefault(pool, {}).update(dates)
            current = month_end + timedelta(days=1)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w") as f:
                json.dump(all_pools, f, indent=2)
            print(f"Saved to {args.output}", file=sys.stderr)

        print_daily(all_pools, args.top)
    else:
        print("Querying...", file=sys.stderr)
        data = query_costs(args.subscription, args.start, args.end, gran)
        pools = parse_rows_monthly(data)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w") as f:
                json.dump(pools, f, indent=2)
            print(f"Saved to {args.output}", file=sys.stderr)

        if args.compare_months:
            print_monthly_comparison(pools, args.top)
        else:
            print_monthly(pools, args.top)


if __name__ == "__main__":
    main()
