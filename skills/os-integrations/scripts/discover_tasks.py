#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""
Discover Taskcluster tasks by worker type.

This script fetches the task graph from the Taskcluster index API and filters
tasks by their worker type (e.g., b-win2022). It can output task labels in
various formats suitable for use with mach try.

Usage:
    uv run discover_tasks.py -w b-win2022
    uv run discover_tasks.py -w b-win2022 -o query
    uv run discover_tasks.py -w win11-64-24h2 --branch autoland -o json
"""

import argparse
import json
import sys
from urllib.parse import quote

import httpx


TASKCLUSTER_ROOT = "https://firefox-ci-tc.services.mozilla.com"
INDEX_API = f"{TASKCLUSTER_ROOT}/api/index/v1"
DEFAULT_BRANCH = "mozilla-central"


def get_task_graph_url(branch: str) -> str:
    """Build the URL for fetching the task graph artifact."""
    artifact_path = quote("public/task-graph.json", safe="")
    return (
        f"{INDEX_API}/task/gecko.v2.{branch}.latest.taskgraph.decision"
        f"/artifacts/{artifact_path}"
    )


def fetch_task_graph(branch: str = DEFAULT_BRANCH, timeout: float = 60.0) -> dict | None:
    """
    Fetch the task graph from Taskcluster index API.

    Args:
        branch: The gecko branch to fetch from (e.g., mozilla-central, autoland)
        timeout: Request timeout in seconds

    Returns:
        The task graph as a dictionary, or None if fetch failed
    """
    url = get_task_graph_url(branch)

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
            print(f"Branch '{branch}' may not exist or have no recent decision task", file=sys.stderr)
        return None
    except httpx.RequestError as e:
        print(f"Error: Request failed - {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse task graph JSON - {e}", file=sys.stderr)
        return None


def filter_by_worker_type(task_graph: dict, worker_type: str) -> list[str]:
    """
    Filter task graph by worker type and return sorted task labels.

    Args:
        task_graph: The full task graph dictionary
        worker_type: The worker type to filter by (e.g., b-win2022)

    Returns:
        List of task labels sorted alphabetically
    """
    labels = []

    for task_id, task_data in task_graph.items():
        # Task data contains a 'task' key with the actual task definition
        task = task_data.get("task", {})
        task_worker_type = task.get("workerType", "")

        if task_worker_type == worker_type:
            # Get label from the outer task_data, not the inner task
            label = task_data.get("label", "")
            if label:
                labels.append(label)

    return sorted(labels)


def format_output(labels: list[str], output_format: str) -> str:
    """
    Format task labels for output.

    Args:
        labels: List of task labels
        output_format: Output format ('labels', 'json', or 'query')

    Returns:
        Formatted output string
    """
    if output_format == "json":
        return json.dumps({"labels": labels, "count": len(labels)}, indent=2)

    if output_format == "query":
        if not labels:
            return ""
        # Create OR pattern for mach try fuzzy: -xq 'task1|task2|...'
        pattern = "|".join(labels)
        return f"-xq '{pattern}'"

    # Default: labels format (one per line)
    return "\n".join(labels)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Discover Taskcluster tasks by worker type",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -w b-win2022              List all tasks using b-win2022 worker
  %(prog)s -w b-win2022 -o query     Output as mach try query string
  %(prog)s -w win11-64-24h2 -o json  Output as JSON with count
  %(prog)s -w b-win2022 --branch autoland
        """,
    )

    parser.add_argument(
        "-w", "--worker-type",
        required=True,
        metavar="TYPE",
        help="Worker type to filter by (e.g., b-win2022, win11-64-24h2)",
    )
    parser.add_argument(
        "-o", "--output",
        choices=["labels", "json", "query"],
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
        "--timeout",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Request timeout in seconds (default: 60)",
    )

    args = parser.parse_args()

    # Fetch task graph
    print(f"Fetching task graph from {args.branch}...", file=sys.stderr)
    task_graph = fetch_task_graph(branch=args.branch, timeout=args.timeout)

    if task_graph is None:
        return 1

    # Filter by worker type
    labels = filter_by_worker_type(task_graph, args.worker_type)

    if not labels:
        print(f"No tasks found for worker type '{args.worker_type}'", file=sys.stderr)
        return 0

    print(f"Found {len(labels)} task(s) for worker type '{args.worker_type}'", file=sys.stderr)

    # Format and output results
    output = format_output(labels, args.output)
    if output:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
