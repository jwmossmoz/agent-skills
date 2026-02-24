#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""
Discover Taskcluster tasks by worker type.

Fetches the task graph from the Taskcluster index API and filters tasks by
worker type using substring (default), exact, or regex matching. Supports
grouping by kind and multiple output formats.

Usage:
    uv run discover.py -w win11-64-24h2 -o summary
    uv run discover.py -w win11-64-24h2 --exact -o json
    uv run discover.py -w win11-64-24h2-hw -k browsertime -o labels
    uv run discover.py --list-worker-types
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from urllib.parse import quote

import httpx


TASKCLUSTER_ROOT = "https://firefox-ci-tc.services.mozilla.com"
INDEX_API = f"{TASKCLUSTER_ROOT}/api/index/v1"
DEFAULT_BRANCH = "mozilla-central"


def get_task_graph_url(branch: str) -> str:
    artifact_path = quote("public/task-graph.json", safe="")
    return (
        f"{INDEX_API}/task/gecko.v2.{branch}.latest.taskgraph.decision"
        f"/artifacts/{artifact_path}"
    )


def fetch_task_graph(branch: str = DEFAULT_BRANCH, timeout: float = 120.0) -> dict | None:
    """
    Fetch the task graph from Taskcluster index API.

    Args:
        branch: The gecko branch to fetch from (e.g., mozilla-central, autoland)
        timeout: Request timeout in seconds

    Returns:
        The task graph as a dictionary, or None if fetch failed
    """
    url = get_task_graph_url(branch)
    print(f"Fetching task graph from {branch}...", file=sys.stderr)

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        print(f"Error: Request timed out after {timeout}s", file=sys.stderr)
        return None
    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP {e.response.status_code} - {e.response.reason_phrase}", file=sys.stderr)
        if e.response.status_code == 404:
            print(
                f"Branch '{branch}' may not exist or have no recent decision task",
                file=sys.stderr,
            )
        return None
    except httpx.RequestError as e:
        print(f"Error: Request failed - {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse task graph JSON - {e}", file=sys.stderr)
        return None


def extract_tasks(task_graph: dict) -> list[tuple[str, str, str]]:
    """
    Extract (label, worker_type, kind) tuples from a task graph.

    Args:
        task_graph: The full task graph dictionary

    Returns:
        List of (label, worker_type, kind) tuples
    """
    tasks = []
    for _task_id, task_data in task_graph.items():
        label = task_data.get("label", "")
        if not label:
            continue
        task = task_data.get("task", {})
        worker_type = task.get("workerType", "")
        kind = task.get("tags", {}).get("kind", "unknown")
        tasks.append((label, worker_type, kind))
    return tasks


def build_matcher(pattern: str, exact: bool, regex: bool):
    """Return a callable that tests whether a worker_type matches the pattern."""
    if regex:
        compiled = re.compile(pattern)
        return lambda wt: bool(compiled.search(wt))
    if exact:
        return lambda wt: wt == pattern
    return lambda wt: pattern in wt


def filter_tasks(
    tasks: list[tuple[str, str, str]],
    pattern: str,
    exact: bool,
    regex: bool,
    kinds: list[str] | None,
) -> list[tuple[str, str, str]]:
    """
    Filter tasks by worker type pattern and optional kind(s).

    Args:
        tasks: List of (label, worker_type, kind) tuples
        pattern: Worker type pattern string
        exact: Use exact matching
        regex: Treat pattern as regex
        kinds: Optional list of kinds to restrict to

    Returns:
        Filtered and sorted list of (label, worker_type, kind) tuples
    """
    matcher = build_matcher(pattern, exact, regex)
    kind_set = set(kinds) if kinds else None

    result = [
        (label, wt, kind)
        for label, wt, kind in tasks
        if matcher(wt) and (kind_set is None or kind in kind_set)
    ]
    return sorted(result, key=lambda t: t[0])


def format_labels(tasks: list[tuple[str, str, str]]) -> str:
    return "\n".join(label for label, _, _ in tasks)


def format_json(tasks: list[tuple[str, str, str]], pattern: str) -> str:
    by_kind: dict[str, list[str]] = defaultdict(list)
    labels = []
    for label, _, kind in tasks:
        by_kind[kind].append(label)
        labels.append(label)
    return json.dumps(
        {
            "worker_type": pattern,
            "count": len(labels),
            "by_kind": dict(sorted(by_kind.items())),
            "labels": labels,
        },
        indent=2,
    )


def format_summary(tasks: list[tuple[str, str, str]]) -> str:
    # Group by (kind, worker_type) -> count
    by_kind: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, wt, kind in tasks:
        by_kind[kind][wt] += 1

    lines = []
    total = 0
    for kind in sorted(by_kind):
        wt_counts = by_kind[kind]
        kind_total = sum(wt_counts.values())
        total += kind_total
        lines.append(f"{kind} ({kind_total})")
        for wt in sorted(wt_counts):
            lines.append(f"  {wt}: {wt_counts[wt]}")

    lines.append("")
    lines.append(f"Total: {total} tasks across {len(by_kind)} kind(s)")
    return "\n".join(lines)


def format_query(tasks: list[tuple[str, str, str]]) -> str:
    return " ".join(f"-q '{label}'" for label, _, _ in tasks)


def format_output(tasks: list[tuple[str, str, str]], output_format: str, pattern: str) -> str:
    if output_format == "json":
        return format_json(tasks, pattern)
    if output_format == "summary":
        return format_summary(tasks)
    if output_format == "query":
        return format_query(tasks)
    return format_labels(tasks)


def list_worker_types(tasks: list[tuple[str, str, str]]) -> str:
    worker_types = sorted({wt for _, wt, _ in tasks if wt})
    return "\n".join(worker_types)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover Taskcluster tasks by worker type",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-worker-types
  %(prog)s -w win11-64-24h2 -o summary
  %(prog)s -w win11-64-24h2 --exact -o json
  %(prog)s -w win11-64-24h2-hw -k browsertime -o labels
  %(prog)s -w win11-64-24h2 -o query | head -5
  %(prog)s -w 'win11-64-24h2(-gpu|-source)' --regex -o summary
        """,
    )

    parser.add_argument(
        "-w", "--worker-type",
        metavar="PATTERN",
        help="Worker type pattern (substring match by default)",
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Require exact match instead of substring",
    )
    parser.add_argument(
        "--regex",
        action="store_true",
        help="Treat pattern as a regular expression",
    )
    parser.add_argument(
        "-o", "--output",
        choices=["labels", "json", "summary", "query"],
        default="labels",
        help="Output format (default: labels)",
    )
    parser.add_argument(
        "--branch",
        default=DEFAULT_BRANCH,
        metavar="BRANCH",
        help=f"Branch to fetch task graph from (default: {DEFAULT_BRANCH})",
    )
    parser.add_argument(
        "-k", "--kind",
        action="append",
        metavar="KIND",
        dest="kinds",
        help="Filter to specific kind (repeatable, e.g. -k test -k browsertime)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        metavar="SECONDS",
        help="HTTP timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--list-worker-types",
        action="store_true",
        help="List all unique worker types in the graph (no -w needed)",
    )

    args = parser.parse_args()

    if not args.list_worker_types and not args.worker_type:
        parser.error("one of -w/--worker-type or --list-worker-types is required")

    if args.exact and args.regex:
        parser.error("--exact and --regex are mutually exclusive")

    task_graph = fetch_task_graph(branch=args.branch, timeout=args.timeout)
    if task_graph is None:
        return 1

    tasks = extract_tasks(task_graph)
    print(f"Loaded {len(tasks)} tasks from task graph", file=sys.stderr)

    if args.list_worker_types:
        print(list_worker_types(tasks))
        return 0

    filtered = filter_tasks(tasks, args.worker_type, args.exact, args.regex, args.kinds)

    if not filtered:
        match_desc = "exact" if args.exact else ("regex" if args.regex else "substring")
        print(
            f"No tasks found for worker type '{args.worker_type}' ({match_desc} match)",
            file=sys.stderr,
        )
        return 0

    print(f"Found {len(filtered)} task(s) matching '{args.worker_type}'", file=sys.stderr)

    output = format_output(filtered, args.output, args.worker_type)
    if output:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
