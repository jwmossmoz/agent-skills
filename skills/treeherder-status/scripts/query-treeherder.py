#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["treeherder-client"]
# ///
"""
Query Treeherder for job results by revision or push ID.

This is a thin wrapper around treeherder-client for command-line usage.
For more control, use the treeherder-client Python package directly.
"""

import argparse
import sys

from thclient import TreeherderClient


def format_job_status(job: dict) -> str:
    """Format job information for display."""
    name = job.get("job_type_name", "Unknown")
    result = job.get("result", "unknown")
    state = job.get("state", "unknown")

    emoji = {
        "success": "✅",
        "testfailed": "❌",
        "busted": "💥",
        "retry": "🔄",
        "usercancel": "🚫",
        "running": "🏃",
        "pending": "⏳",
    }.get(result if result != "unknown" else state, "❓")

    return f"{emoji} {name} - {result} ({state})"


def main():
    parser = argparse.ArgumentParser(
        description="Query Treeherder for job results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query by revision
  %(prog)s --revision abc123def456 --repo try

  # Query by push ID
  %(prog)s --push-id 12345 --repo try

  # Filter jobs by name
  %(prog)s --revision abc123 --filter mochitest
        """,
    )
    parser.add_argument(
        "--revision",
        help="Commit revision to query",
    )
    parser.add_argument(
        "--push-id",
        type=int,
        help="Push ID to query",
    )
    parser.add_argument(
        "--repo",
        default="try",
        help="Repository name (default: try)",
    )
    parser.add_argument(
        "--filter",
        help="Filter jobs by name substring",
    )

    args = parser.parse_args()

    if not args.revision and not args.push_id:
        parser.error("Either --revision or --push-id must be specified")

    client = TreeherderClient()

    # Get push if querying by revision
    if args.revision:
        print(f"Querying push for revision {args.revision}...")
        data = client._get_json(client.PUSH_ENDPOINT, project=args.repo, revision=args.revision)
        if not data.get("results"):
            print("❌ No push found for this revision")
            sys.exit(1)
        push = data["results"][0]
        push_id = push["id"]
        print(f"Found push ID: {push_id}")
        print(f"Author: {push.get('author', 'unknown')}")
        print(f"Treeherder: https://treeherder.mozilla.org/jobs?repo={args.repo}&revision={args.revision}\n")
    else:
        push_id = args.push_id

    # Get jobs
    print(f"Fetching jobs for push {push_id}...")
    data = client._get_json(client.JOBS_ENDPOINT, project=args.repo, push_id=push_id)
    jobs = data.get("results", [])

    if args.filter:
        jobs = [j for j in jobs if args.filter in j.get("job_type_name", "")]
        print(f"Filter: '{args.filter}'")

    if not jobs:
        print("⚠️  No jobs found")
        sys.exit(0)

    print(f"\nFound {len(jobs)} job(s):\n")

    # Summary by result
    by_result = {}
    for job in jobs:
        result = job.get("result", "unknown")
        by_result.setdefault(result, []).append(job)

    for result in sorted(by_result.keys()):
        print(f"{result.upper()}: {len(by_result[result])}")

    print("\nDetailed results:\n")
    for job in jobs:
        print(format_job_status(job))

    # Exit code based on failures
    failed = sum(1 for j in jobs if j.get("result") in ["testfailed", "busted"])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
