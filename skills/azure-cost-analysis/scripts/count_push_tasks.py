#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Count Taskcluster tasks per worker pool and test suite for a mozilla-central push.

Uses the TC index and queue APIs (public, no auth required) to enumerate tasks
in a push's task group and break them down by worker pool and test suite.

Usage:
    uv run count_push_tasks.py --date 2026.03.30
    uv run count_push_tasks.py --date 2026.01.15 --pool-filter win11-64-24h2
    uv run count_push_tasks.py --date 2026.03.30 --push-index 1
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

TC_BASE = "https://firefox-ci-tc.services.mozilla.com/api"


def fetch_json(url, timeout=30):
    """Fetch JSON from a URL."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_push_times(date_path):
    """List push timestamps for a date (e.g., '2026.01.15')."""
    data = fetch_json(
        f"{TC_BASE}/index/v1/namespaces/"
        f"gecko.v2.mozilla-central.pushdate.{date_path}"
    )
    return [
        ns["name"]
        for ns in data.get("namespaces", [])
        if ns["name"] != "latest"
    ]


def get_task_group_id(date_path, push_time):
    """Get the taskGroupId for a push by looking up an indexed task."""
    ns = (
        f"gecko.v2.mozilla-central.pushdate.{date_path}"
        f".{push_time}.firefox.linux64-opt"
    )
    try:
        index_data = fetch_json(
            f"{TC_BASE}/index/v1/task/{ns}", timeout=10
        )
    except Exception:
        return None

    task_id = index_data.get("taskId")
    if not task_id:
        return None

    task = fetch_json(
        f"{TC_BASE}/queue/v1/task/{task_id}", timeout=10
    )
    return task.get("taskGroupId")


def count_task_group(task_group_id, pool_filter=None):
    """Count tasks by worker pool and test suite in a task group."""
    pool_counts = defaultdict(int)
    suite_counts = defaultdict(lambda: defaultdict(int))
    total = 0
    continuation = None

    while True:
        url = (
            f"{TC_BASE}/queue/v1/task-group/{task_group_id}/list?limit=1000"
        )
        if continuation:
            url += (
                f"&continuationToken="
                f"{urllib.parse.quote(continuation)}"
            )

        data = fetch_json(url, timeout=60)

        for entry in data.get("tasks", []):
            task = entry.get("task", {})
            queue_id = task.get("taskQueueId", "unknown")
            pool_counts[queue_id] += 1
            total += 1

            if pool_filter and pool_filter in queue_id:
                tags = task.get("tags", {})
                suite = tags.get(
                    "test-suite", tags.get("kind", "other")
                )
                suite_counts[queue_id][suite] += 1

        continuation = data.get("continuationToken")
        if not continuation:
            break

    return dict(pool_counts), dict(suite_counts), total


def main():
    parser = argparse.ArgumentParser(
        description="Count tasks per worker pool in a mozilla-central push",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --date 2026.03.30
  %(prog)s --date 2026.01.15 --pool-filter win11-64-24h2
  %(prog)s --date 2026.03.30 --push-index 1
        """,
    )
    parser.add_argument(
        "--date", required=True,
        help="Push date in TC index format: YYYY.MM.DD",
    )
    parser.add_argument(
        "--push-index", type=int, default=0,
        help="Which push on that date (0=first, default: 0)",
    )
    parser.add_argument(
        "--pool-filter",
        help="Show suite breakdown only for pools matching this substring",
    )

    args = parser.parse_args()

    # Get pushes for the date
    print(f"Getting pushes for {args.date}...", file=sys.stderr)
    pushes = get_push_times(args.date)
    if not pushes:
        print(f"No pushes found for {args.date}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Found {len(pushes)} pushes: {', '.join(pushes)}",
        file=sys.stderr,
    )

    if args.push_index >= len(pushes):
        print(
            f"Push index {args.push_index} out of range "
            f"(0-{len(pushes) - 1})",
            file=sys.stderr,
        )
        sys.exit(1)

    push_time = pushes[args.push_index]
    print(f"Analyzing push {push_time}...", file=sys.stderr)

    # Get task group
    tg_id = get_task_group_id(args.date, push_time)
    if not tg_id:
        print("Could not find task group", file=sys.stderr)
        sys.exit(1)

    print(f"Task group: {tg_id}", file=sys.stderr)

    # Count tasks
    print("Counting tasks (this may take a moment)...", file=sys.stderr)
    pool_counts, suite_counts, total = count_task_group(
        tg_id, args.pool_filter
    )

    # Print results
    print(f"\nPush: {args.date} / {push_time}")
    print(f"Task group: {tg_id}")
    print(f"Total tasks: {total}")

    # Pool summary
    win_pools = {
        k: v for k, v in pool_counts.items()
        if "win" in k.lower()
    }
    other_count = total - sum(win_pools.values())

    if win_pools:
        print(f"\nWindows worker pools:")
        for pool, count in sorted(
            win_pools.items(), key=lambda x: -x[1]
        ):
            print(f"  {count:>4}  {pool}")
        print(f"  {other_count:>4}  (all other pools)")

    # Suite breakdown
    if suite_counts:
        for pool in sorted(
            suite_counts, key=lambda p: -sum(suite_counts[p].values())
        ):
            suites = suite_counts[pool]
            pool_total = sum(suites.values())
            print(f"\n{pool} ({pool_total} tasks):")
            for suite, count in sorted(
                suites.items(), key=lambda x: -x[1]
            ):
                print(f"  {count:>4}  {suite}")


if __name__ == "__main__":
    main()
