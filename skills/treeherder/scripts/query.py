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
import json
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


def get_recent_pushes(client: TreeherderClient, repo: str, limit: int = 50) -> list:
    """Get recent pushes for a repository."""
    data = client._get_json(client.PUSH_ENDPOINT, project=repo, count=limit)
    return data.get("results", [])


def get_jobs_for_push(client: TreeherderClient, repo: str, push_id: int) -> list:
    """Get all jobs for a specific push."""
    data = client._get_json(client.JOBS_ENDPOINT, project=repo, push_id=push_id)
    return data.get("results", [])


def find_similar_failures(
    client: TreeherderClient,
    job_filter: str,
    repos: list[str],
    limit: int = 100,
    json_output: bool = False,
) -> list[dict]:
    """
    Search for similar job failures across multiple repositories.

    This is the core sheriff signal for distinguishing image vs code regressions:
    - If the same test fails on autoland/mozilla-central, it's likely a code regression
    - If the test only fails on alpha/staging pools, it's likely an image regression
    """
    results = []

    for repo in repos:
        if not json_output:
            print(f"\nSearching {repo} (last {limit} pushes)...", file=sys.stderr)

        pushes = get_recent_pushes(client, repo, limit)

        for push in pushes:
            push_id = push["id"]
            revision = push.get("revision", "")[:12]

            jobs = get_jobs_for_push(client, repo, push_id)

            # Filter jobs by name
            matching_jobs = [
                j for j in jobs
                if job_filter.lower() in j.get("job_type_name", "").lower()
            ]

            # Find failures
            failed_jobs = [
                j for j in matching_jobs
                if j.get("result") in ["testfailed", "busted"]
            ]

            for job in failed_jobs:
                job_id = job.get("id")
                result = {
                    "repo": repo,
                    "push_id": push_id,
                    "revision": revision,
                    "job_id": job_id,
                    "job_type_name": job.get("job_type_name"),
                    "result": job.get("result"),
                    "failure_classification_id": job.get("failure_classification_id"),
                    "treeherder_url": f"https://treeherder.mozilla.org/jobs?repo={repo}&revision={push['revision']}&selectedJobId={job_id}",
                    "taskcluster_task_id": job.get("task_id"),
                }
                results.append(result)

                if not json_output:
                    classification = job.get("failure_classification_id", 1)
                    class_label = {
                        1: "not classified",
                        2: "fixed by commit",
                        3: "expected fail",
                        4: "intermittent",
                        5: "infra",
                        6: "intermittent needs filing",
                        7: "autoclassified intermittent",
                    }.get(classification, f"unknown ({classification})")

                    print(f"  {revision} | {job.get('job_type_name')} | {job.get('result')} | {class_label}")

    return results


def query_by_revision(args, client: TreeherderClient) -> int:
    """Query jobs for a specific revision."""
    print(f"Querying push for revision {args.revision}...")
    data = client._get_json(client.PUSH_ENDPOINT, project=args.repo, revision=args.revision)
    if not data.get("results"):
        print("No push found for this revision")
        sys.exit(1)
    push = data["results"][0]
    push_id = push["id"]
    print(f"Found push ID: {push_id}")
    print(f"Author: {push.get('author', 'unknown')}")
    print(f"Treeherder: https://treeherder.mozilla.org/jobs?repo={args.repo}&revision={args.revision}\n")

    return push_id


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

  # Find similar failures across branches (sheriff workflow)
  %(prog)s --find-similar "mochitest-browser-chrome" --repos autoland,mozilla-central --limit 100

  # JSON output for scripting
  %(prog)s --find-similar "test_keycodes" --json
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
    parser.add_argument(
        "--find-similar",
        metavar="JOB_NAME",
        help="Search for similar job failures across branches (e.g., 'mochitest-browser-chrome')",
    )
    parser.add_argument(
        "--repos",
        default="autoland,mozilla-central",
        help="Comma-separated list of repos to search (default: autoland,mozilla-central)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of recent pushes to search per repo (default: 100)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    client = TreeherderClient()

    # Handle --find-similar mode
    if args.find_similar:
        repos = [r.strip() for r in args.repos.split(",")]

        if not args.json:
            print(f"Searching for '{args.find_similar}' failures across: {', '.join(repos)}")
            print(f"Checking last {args.limit} pushes per repo...\n")

        results = find_similar_failures(
            client,
            args.find_similar,
            repos,
            args.limit,
            json_output=args.json,
        )

        if args.json:
            print(json.dumps({"failures": results, "count": len(results)}, indent=2))
        else:
            print(f"\nFound {len(results)} failure(s) matching '{args.find_similar}'")

            # Summary by classification
            by_class = {}
            for r in results:
                class_id = r.get("failure_classification_id", 1)
                by_class.setdefault(class_id, []).append(r)

            if by_class:
                print("\nBy classification:")
                class_names = {
                    1: "Not classified",
                    2: "Fixed by commit",
                    3: "Expected fail",
                    4: "Intermittent",
                    5: "Infra",
                    6: "Intermittent needs filing",
                    7: "Autoclassified intermittent",
                }
                for class_id in sorted(by_class.keys()):
                    name = class_names.get(class_id, f"Unknown ({class_id})")
                    print(f"  {name}: {len(by_class[class_id])}")

        return 0

    # Original query mode
    if not args.revision and not args.push_id:
        parser.error("Either --revision, --push-id, or --find-similar must be specified")

    # Get push if querying by revision
    if args.revision:
        push_id = query_by_revision(args, client)
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
        print("No jobs found")
        sys.exit(0)

    if args.json:
        print(json.dumps({"jobs": jobs, "count": len(jobs)}, indent=2))
        return 0

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
    sys.exit(main() or 0)
