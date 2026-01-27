#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["treeherder-client", "requests"]
# ///
"""
Query and manage Treeherder job classifications.

Sheriffs classify job failures to help distinguish:
- Intermittent failures (known flaky tests)
- Infrastructure issues
- Real code regressions
- Fixed by subsequent commits

This script allows querying classifications for jobs.
"""

import argparse
import json
import sys
from typing import Optional

import requests
from thclient import TreeherderClient


# Treeherder classification IDs
CLASSIFICATION_NAMES = {
    1: "not classified",
    2: "fixed by commit",
    3: "expected fail",
    4: "intermittent",
    5: "infra",
    6: "intermittent needs filing",
    7: "autoclassified intermittent",
}


def get_job_by_task_id(
    client: TreeherderClient,
    task_id: str,
    repo: str = "autoland",
) -> Optional[dict]:
    """Find a Treeherder job by Taskcluster task ID."""
    # Search across common repos if not found
    repos_to_try = [repo] if repo else ["autoland", "mozilla-central", "try"]

    for r in repos_to_try:
        try:
            data = client._get_json(
                client.JOBS_ENDPOINT,
                project=r,
                task_id=task_id,
            )
            jobs = data.get("results", [])
            if jobs:
                return {"job": jobs[0], "repo": r}
        except Exception:
            continue

    return None


def get_job_by_id(
    client: TreeherderClient,
    job_id: int,
    repo: str,
) -> Optional[dict]:
    """Get a Treeherder job by job ID."""
    try:
        data = client._get_json(
            client.JOBS_ENDPOINT,
            project=repo,
            id=job_id,
        )
        jobs = data.get("results", [])
        if jobs:
            return {"job": jobs[0], "repo": repo}
    except Exception:
        pass

    return None


def get_job_classification(job: dict) -> dict:
    """Extract classification information from a job."""
    class_id = job.get("failure_classification_id", 1)

    return {
        "job_id": job.get("id"),
        "task_id": job.get("task_id"),
        "job_type_name": job.get("job_type_name"),
        "result": job.get("result"),
        "state": job.get("state"),
        "failure_classification_id": class_id,
        "failure_classification_name": CLASSIFICATION_NAMES.get(class_id, f"unknown ({class_id})"),
        "who": job.get("who"),  # Who ran the job
    }


def get_job_notes(job_id: int, repo: str) -> list:
    """
    Get notes/comments on a job (includes classification notes from sheriffs).

    Uses direct API call since treeherder-client doesn't expose this.
    """
    url = f"https://treeherder.mozilla.org/api/project/{repo}/note/?job_id={job_id}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Could not fetch notes: {e}", file=sys.stderr)
        return []


def cmd_get(args) -> int:
    """Get classification for a job."""
    client = TreeherderClient()

    # Find the job
    if args.task_id:
        result = get_job_by_task_id(client, args.task_id, args.repo)
        if not result:
            print(f"Job not found for task ID: {args.task_id}", file=sys.stderr)
            return 1
    elif args.job_id:
        if not args.repo:
            print("--repo is required when using --job-id", file=sys.stderr)
            return 1
        result = get_job_by_id(client, args.job_id, args.repo)
        if not result:
            print(f"Job not found: {args.job_id} in {args.repo}", file=sys.stderr)
            return 1
    else:
        print("Either --task-id or --job-id is required", file=sys.stderr)
        return 1

    job = result["job"]
    repo = result["repo"]

    classification = get_job_classification(job)
    classification["repo"] = repo
    classification["treeherder_url"] = (
        f"https://treeherder.mozilla.org/jobs?repo={repo}"
        f"&selectedJobId={job.get('id')}"
    )

    # Get notes if requested
    if args.include_notes:
        notes = get_job_notes(job.get("id"), repo)
        classification["notes"] = [
            {
                "id": n.get("id"),
                "text": n.get("text"),
                "failure_classification_id": n.get("failure_classification_id"),
                "failure_classification_name": CLASSIFICATION_NAMES.get(
                    n.get("failure_classification_id", 1), "unknown"
                ),
                "created": n.get("created"),
            }
            for n in notes
        ]

    if args.json:
        print(json.dumps(classification, indent=2))
    else:
        print(f"Job: {classification['job_type_name']}")
        print(f"Result: {classification['result']} ({classification['state']})")
        print(f"Classification: {classification['failure_classification_name']} (id={classification['failure_classification_id']})")
        print(f"Treeherder: {classification['treeherder_url']}")

        if args.include_notes and classification.get("notes"):
            print("\nNotes:")
            for note in classification["notes"]:
                print(f"  - [{note['failure_classification_name']}] {note['text']}")

    return 0


def cmd_summary(args) -> int:
    """Get classification summary for jobs in a push."""
    client = TreeherderClient()

    # Get push
    if args.revision:
        data = client._get_json(
            client.PUSH_ENDPOINT,
            project=args.repo,
            revision=args.revision,
        )
        if not data.get("results"):
            print(f"No push found for revision: {args.revision}", file=sys.stderr)
            return 1
        push_id = data["results"][0]["id"]
    else:
        push_id = args.push_id

    # Get jobs
    data = client._get_json(
        client.JOBS_ENDPOINT,
        project=args.repo,
        push_id=push_id,
    )
    jobs = data.get("results", [])

    # Filter to failures only
    failures = [j for j in jobs if j.get("result") in ["testfailed", "busted"]]

    if not failures:
        print("No failures found in this push")
        return 0

    # Group by classification
    by_classification = {}
    for job in failures:
        class_id = job.get("failure_classification_id", 1)
        class_name = CLASSIFICATION_NAMES.get(class_id, f"unknown ({class_id})")
        by_classification.setdefault(class_name, []).append(job)

    if args.json:
        result = {
            "push_id": push_id,
            "repo": args.repo,
            "total_failures": len(failures),
            "by_classification": {
                name: [get_job_classification(j) for j in jobs]
                for name, jobs in by_classification.items()
            },
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"Push {push_id} ({args.repo}): {len(failures)} failure(s)\n")
        print("By classification:")
        for class_name in sorted(by_classification.keys()):
            jobs = by_classification[class_name]
            print(f"\n  {class_name}: {len(jobs)}")
            for job in jobs[:5]:  # Show first 5
                print(f"    - {job.get('job_type_name')}")
            if len(jobs) > 5:
                print(f"    ... and {len(jobs) - 5} more")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Query Treeherder job classifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Classification IDs:
  1 = not classified
  2 = fixed by commit
  3 = expected fail
  4 = intermittent (known flaky test)
  5 = infra (infrastructure issue)
  6 = intermittent needs filing
  7 = autoclassified intermittent

Examples:
  # Get classification by Taskcluster task ID
  %(prog)s get --task-id fuCPrKG2T62-4YH1tWYa7Q

  # Get classification by Treeherder job ID
  %(prog)s get --job-id 12345 --repo autoland

  # Include sheriff notes
  %(prog)s get --task-id fuCPrKG2T62-4YH1tWYa7Q --include-notes

  # Classification summary for a push
  %(prog)s summary --revision abc123 --repo autoland
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # get command
    get_parser = subparsers.add_parser("get", help="Get classification for a job")
    get_parser.add_argument("--task-id", help="Taskcluster task ID")
    get_parser.add_argument("--job-id", type=int, help="Treeherder job ID")
    get_parser.add_argument("--repo", help="Repository (autoland, mozilla-central, try)")
    get_parser.add_argument("--include-notes", action="store_true", help="Include sheriff notes")
    get_parser.add_argument("--json", action="store_true", help="JSON output")

    # summary command
    summary_parser = subparsers.add_parser("summary", help="Classification summary for a push")
    summary_parser.add_argument("--revision", help="Commit revision")
    summary_parser.add_argument("--push-id", type=int, help="Push ID")
    summary_parser.add_argument("--repo", default="autoland", help="Repository (default: autoland)")
    summary_parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "get":
        return cmd_get(args)
    elif args.command == "summary":
        if not args.revision and not args.push_id:
            print("Either --revision or --push-id is required", file=sys.stderr)
            return 1
        return cmd_summary(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
